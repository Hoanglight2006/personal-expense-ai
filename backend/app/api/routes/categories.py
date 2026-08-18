from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.category_defaults import add_missing_default_categories
from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import CategoryType
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategorySort,
    CategoryStatusFilter,
    CategoryUpdate,
    category_name_key,
)


router = APIRouter(prefix="/categories", tags=["categories"])
CATEGORY_NOT_FOUND = "Không tìm thấy danh mục."
CATEGORY_NAME_CONFLICT = "Tên danh mục đã tồn tại."


def default_period() -> tuple[date, date]:
    today = date.today()
    return today.replace(day=1), today.replace(day=monthrange(today.year, today.month)[1])


def validated_period(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    default_start, default_end = default_period()
    period_start = start_date or default_start
    period_end = end_date or default_end
    if period_start > period_end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Ngày bắt đầu không được sau ngày kết thúc.",
        )
    return period_start, period_end


def owned_category_or_404(
    db: Session,
    category_id: int,
    user_id: int,
    *,
    include_deleted: bool = False,
    lock: bool = False,
) -> Category:
    query = db.query(Category).filter(
        Category.id == category_id, Category.user_id == user_id
    )
    if not include_deleted:
        query = query.filter(Category.deleted_at.is_(None))
    if lock:
        query = query.with_for_update()
    category = query.first()
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=CATEGORY_NOT_FOUND)
    return category


def ensure_unique_name(
    db: Session,
    user_id: int,
    name_normalized: str,
    exclude_id: int | None = None,
) -> None:
    query = db.query(Category.id).filter(
        Category.user_id == user_id,
        Category.name_normalized == name_normalized,
    )
    if exclude_id is not None:
        query = query.filter(Category.id != exclude_id)
    if query.first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=CATEGORY_NAME_CONFLICT)


def commit_category(db: Session, category: Category) -> Category:
    try:
        db.commit()
    except DataError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Dữ liệu danh mục vượt quá giới hạn lưu trữ.",
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=CATEGORY_NAME_CONFLICT)
    db.refresh(category)
    return category


def category_response(db: Session, category: Category) -> CategoryResponse:
    has_transactions = db.query(Transaction.id).filter(
        Transaction.user_id == category.user_id,
        Transaction.category_id == category.id,
        Transaction.is_deleted.is_(False),
    ).first() is not None
    return CategoryResponse.model_validate(category).model_copy(
        update={"has_transactions": has_transactions}
    )


def category_rows_with_stats(
    db: Session,
    user_id: int,
    period_start: date,
    period_end: date,
    search: str | None = None,
    category_status: CategoryStatusFilter = "active",
    sort: CategorySort = "amount_desc",
    category_id: int | None = None,
) -> list[CategoryResponse]:
    stats = (
        db.query(
            Transaction.category_id.label("category_id"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total_amount"),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.type == CategoryType.EXPENSE, Transaction.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("expense_amount"),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.type == CategoryType.INCOME, Transaction.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("income_amount"),
            func.count(Transaction.id).label("transaction_count"),
        )
        .filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
        )
        .group_by(Transaction.category_id)
        .subquery()
    )
    amount_expression = func.coalesce(stats.c.total_amount, 0)
    query = (
        db.query(
            Category,
            amount_expression,
            func.coalesce(stats.c.expense_amount, 0),
            func.coalesce(stats.c.income_amount, 0),
            func.coalesce(stats.c.transaction_count, 0),
        )
        .outerjoin(stats, stats.c.category_id == Category.id)
        .filter(Category.user_id == user_id)
    )
    if category_id is not None:
        query = query.filter(Category.id == category_id)
    if search:
        normalized_search = search.strip().casefold()
        if normalized_search:
            query = query.filter(Category.name_normalized.contains(normalized_search, autoescape=True))
    
    # Always filter out soft-deleted categories
    query = query.filter(Category.deleted_at.is_(None))

    if category_status == "active":
        query = query.filter(Category.is_active.is_(True))
    elif category_status == "hidden":
        query = query.filter(Category.is_active.is_(False))

    if sort == "amount_asc":
        query = query.order_by(amount_expression.asc(), Category.name.asc())
    elif sort == "name_asc":
        query = query.order_by(Category.name.asc())
    else:
        query = query.order_by(amount_expression.desc(), Category.name.asc())

    total_expense = Decimal(
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
            Transaction.type == CategoryType.EXPENSE,
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
        )
        .scalar()
        or 0
    )
    used_category_ids = {
        row[0]
        for row in db.query(Transaction.category_id)
        .filter(
            Transaction.user_id == user_id,
            Transaction.is_deleted.is_(False),
        )
        .distinct()
        .all()
    }
    responses: list[CategoryResponse] = []
    for category, total_amount, expense_amount, income_amount, transaction_count in query.all():
        amount = Decimal(total_amount or 0).quantize(Decimal("0.01"))
        category_expense = Decimal(expense_amount or 0).quantize(Decimal("0.01"))
        category_income = Decimal(income_amount or 0).quantize(Decimal("0.01"))
        percentage = Decimal("0.00")
        if total_expense > 0:
            percentage = (
                category_expense / total_expense * Decimal("100")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        response = CategoryResponse.model_validate(category).model_copy(
            update={
                "total_amount": amount,
                "income_amount": category_income,
                "expense_amount": category_expense,
                "transaction_count": int(transaction_count or 0),
                "expense_percentage": percentage,
                "has_transactions": category.id in used_category_ids,
            }
        )
        responses.append(response)
    return responses


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    normalized_name = category_name_key(category_in.name)
    ensure_unique_name(db, current_user.id, normalized_name)
    category = Category(
        user_id=current_user.id,
        name=category_in.name,
        name_normalized=normalized_name,
        type=category_in.type,
        icon=category_in.icon,
        color=category_in.color,
    )
    db.add(category)
    commit_category(db, category)
    return category_response(db, category)


@router.post("/defaults", response_model=list[CategoryResponse], status_code=status.HTTP_201_CREATED)
def create_default_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CategoryResponse]:
    created = add_missing_default_categories(db, current_user.id)
    try:
        db.commit()
    except DataError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Dữ liệu danh mục vượt quá giới hạn lưu trữ.",
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=CATEGORY_NAME_CONFLICT)
    for category in created:
        db.refresh(category)
    return [category_response(db, category) for category in created]


@router.get("", response_model=CategoryListResponse)
def list_categories(
    search: Annotated[str | None, Query(max_length=50)] = None,
    status_filter: Annotated[CategoryStatusFilter, Query(alias="status")] = "active",
    sort: CategorySort = "amount_desc",
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryListResponse:
    period_start, period_end = validated_period(start_date, end_date)
    items = category_rows_with_stats(
        db,
        current_user.id,
        period_start,
        period_end,
        search=search,
        category_status=status_filter,
        sort=sort,
    )
    return CategoryListResponse(start_date=period_start, end_date=period_end, items=items)


@router.get("/statistics", response_model=CategoryListResponse)
def category_statistics(
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryListResponse:
    period_start, period_end = validated_period(start_date, end_date)
    items = category_rows_with_stats(
        db,
        current_user.id,
        period_start,
        period_end,
        category_status="all",
        sort="amount_desc",
    )
    return CategoryListResponse(start_date=period_start, end_date=period_end, items=items)


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    owned_category_or_404(db, category_id, current_user.id)
    period_start, period_end = validated_period(start_date, end_date)
    return category_rows_with_stats(
        db,
        current_user.id,
        period_start,
        period_end,
        category_status="all",
        category_id=category_id,
    )[0]


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    category = owned_category_or_404(db, category_id, current_user.id, lock=True)
    changes = category_in.model_dump(exclude_unset=True)
    if "type" in changes and changes["type"] != category.type:
        has_transactions = (
            db.query(Transaction.id)
            .filter(
                Transaction.category_id == category.id,
                Transaction.user_id == current_user.id,
            )
            .first()
            is not None
        )
        has_budgets = (
            db.query(Budget.id)
            .filter(
                Budget.category_id == category.id,
                Budget.user_id == current_user.id,
            )
            .first()
            is not None
        )
        if has_transactions or has_budgets:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Không thể đổi loại danh mục đã được sử dụng cho giao dịch "
                    "hoặc ngân sách."
                ),
            )
    next_name = changes.get("name", category.name)
    normalized_name = category_name_key(next_name)
    ensure_unique_name(db, current_user.id, normalized_name, exclude_id=category.id)
    for field, value in changes.items():
        setattr(category, field, value)
    category.name_normalized = normalized_name
    commit_category(db, category)
    return category_response(db, category)


@router.post("/{category_id}/hide", response_model=CategoryResponse)
def hide_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    category = owned_category_or_404(db, category_id, current_user.id)
    category.is_active = False
    commit_category(db, category)
    return category_response(db, category)


@router.post("/{category_id}/restore", response_model=CategoryResponse)
def restore_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    category = owned_category_or_404(db, category_id, current_user.id)
    normalized_name = category_name_key(category.name)
    ensure_unique_name(
        db,
        current_user.id,
        normalized_name,
        exclude_id=category.id,
    )
    category.name_normalized = normalized_name
    category.is_active = True
    commit_category(db, category)
    return category_response(db, category)

@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    category = owned_category_or_404(db, category_id, current_user.id)
    if category.deleted_at is not None:
        return
    
    # Check if category is used by any transactions
    has_transactions = db.query(Transaction).filter(
        Transaction.category_id == category_id,
        Transaction.user_id == current_user.id
    ).first() is not None

    if has_transactions:
        # Instead of returning 409, we perform soft delete according to the user's requirement: 
        # "thực tế chức năng này cũng là ẩn nhưng ko khôi phục được"
        # Since transactions belong to it, we soft delete it so transactions don't lose the category
        pass

    import time
    timestamp = str(int(time.time()))
    category.name_normalized = f"{category.name_normalized[:120]}_del_{timestamp}"
    category.deleted_at = func.now()
    category.is_active = False
    commit_category(db, category)
