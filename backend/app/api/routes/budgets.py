"""Budget management and spending alerts API routes.

Supports monthly category budget setup, real-time spending calculations,
and alert thresholds. All endpoints enforce ownership via the current JWT user.
"""

import calendar
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user, get_db
from app.models.budget import Budget
from app.models.category import Category
from app.models.enums import CategoryType
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.budget import (
    BudgetAlertItem,
    BudgetAlertResponse,
    BudgetCreate,
    BudgetListResponse,
    BudgetResponse,
    BudgetUpdate,
    CategorySimpleInfo,
)

router = APIRouter(prefix="/budgets", tags=["budgets"])

BUDGET_NOT_FOUND = "Không tìm thấy ngân sách."


def _owned_budget_or_404(db: Session, budget_id: int, user_id: int) -> Budget:
    """Return a Budget owned by *user_id* or raise 404."""
    budget = (
        db.query(Budget)
        .options(joinedload(Budget.category))
        .filter(Budget.id == budget_id, Budget.user_id == user_id)
        .first()
    )
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=BUDGET_NOT_FOUND,
        )
    return budget


def _calculate_budget_status(
    amount: Decimal, spent: Decimal
) -> tuple[Decimal, float, str]:
    """Calculate remaining amount, percentage used and alert status.

    Returns: (remaining_amount, percentage_used, status)
    """
    remaining = amount - spent
    pct = round(float((spent / amount) * 100), 1) if amount > 0 else 0.0

    if spent >= amount:
        budget_status = "exceeded"
    elif spent >= amount * Decimal("0.8"):
        budget_status = "warning"
    else:
        budget_status = "normal"

    return remaining, pct, budget_status


def _build_budget_response(budget: Budget, spent: Decimal) -> BudgetResponse:
    """Build a single BudgetResponse schema object."""
    remaining, pct, b_status = _calculate_budget_status(budget.amount, spent)
    cat_info = None
    if budget.category:
        cat_info = CategorySimpleInfo(
            id=budget.category.id,
            name=budget.category.name,
            icon=budget.category.icon,
            color=budget.category.color,
            type=budget.category.type,
            is_active=budget.category.is_active,
        )
    return BudgetResponse(
        id=budget.id,
        user_id=budget.user_id,
        category_id=budget.category_id,
        category=cat_info,
        amount=budget.amount,
        month=budget.month,
        year=budget.year,
        spent_amount=spent,
        remaining_amount=remaining,
        percentage_used=pct,
        status=b_status,
        created_at=budget.created_at,
    )


@router.post(
    "",
    response_model=BudgetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Thiết lập ngân sách mới cho danh mục trong tháng",
)
def create_budget(
    payload: BudgetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BudgetResponse:
    """Create a new monthly category budget."""
    # 1. Validate category ownership and validity
    category = (
        db.query(Category)
        .filter(
            Category.id == payload.category_id,
            Category.user_id == current_user.id,
            Category.deleted_at.is_(None),
        )
        .first()
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy danh mục được chọn.",
        )

    if not category.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể thiết lập ngân sách cho danh mục đã ẩn.",
        )

    # Validate expense category requirement (422 as specified in requirements)
    if category.type != CategoryType.EXPENSE.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Ngân sách chỉ áp dụng cho danh mục Chi tiêu (Expense).",
        )

    # 2. Check for duplicate budget in the same period
    existing = (
        db.query(Budget)
        .filter(
            Budget.user_id == current_user.id,
            Budget.category_id == payload.category_id,
            Budget.month == payload.month,
            Budget.year == payload.year,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Đã thiết lập ngân sách cho danh mục “{category.name}” trong tháng {payload.month}/{payload.year}.",
        )

    # 3. Create budget
    new_budget = Budget(
        user_id=current_user.id,
        category_id=payload.category_id,
        amount=payload.amount,
        month=payload.month,
        year=payload.year,
    )
    db.add(new_budget)
    db.commit()
    db.refresh(new_budget)

    # 4. Compute spent amount in this period
    last_day = calendar.monthrange(payload.year, payload.month)[1]
    start_date = date(payload.year, payload.month, 1)
    end_date = date(payload.year, payload.month, last_day)

    spent_sum = (
        db.query(sa_func.coalesce(sa_func.sum(Transaction.amount), Decimal("0")))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.category_id == payload.category_id,
            Transaction.type == CategoryType.EXPENSE,
            Transaction.is_deleted.is_(False),
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        .scalar()
        or Decimal("0.00")
    )

    new_budget.category = category
    return _build_budget_response(new_budget, spent_sum)


@router.get(
    "",
    response_model=BudgetListResponse,
    summary="Lấy danh sách ngân sách theo tháng/năm",
)
def get_budgets(
    month: Annotated[
        int | None,
        Query(ge=1, le=12, description="Tháng cần xem (mặc định tháng hiện tại)"),
    ] = None,
    year: Annotated[
        int | None,
        Query(ge=2000, le=2100, description="Năm cần xem (mặc định năm hiện tại)"),
    ] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BudgetListResponse:
    """Retrieve all category budgets for a specific month and year."""
    today = date.today()
    target_month = month or today.month
    target_year = year or today.year

    last_day = calendar.monthrange(target_year, target_month)[1]
    start_date = date(target_year, target_month, 1)
    end_date = date(target_year, target_month, last_day)

    # 1. Fetch user's budgets for this period
    budgets = (
        db.query(Budget)
        .options(joinedload(Budget.category))
        .filter(
            Budget.user_id == current_user.id,
            Budget.month == target_month,
            Budget.year == target_year,
        )
        .order_by(Budget.created_at.asc())
        .all()
    )

    if not budgets:
        return BudgetListResponse(
            month=target_month,
            year=target_year,
            total_budget=Decimal("0.00"),
            total_spent=Decimal("0.00"),
            total_remaining=Decimal("0.00"),
            items=[],
        )

    # 2. Batch calculate spent amounts by category in 1 query
    spent_rows = (
        db.query(
            Transaction.category_id,
            sa_func.coalesce(sa_func.sum(Transaction.amount), Decimal("0")).label(
                "total_spent"
            ),
        )
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.type == CategoryType.EXPENSE,
            Transaction.is_deleted.is_(False),
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        .group_by(Transaction.category_id)
        .all()
    )
    spent_map = {row[0]: Decimal(str(row[1])) for row in spent_rows}

    # 3. Assemble response items
    items = []
    total_budget = Decimal("0.00")
    total_spent = Decimal("0.00")

    for b in budgets:
        spent = spent_map.get(b.category_id, Decimal("0.00"))
        items.append(_build_budget_response(b, spent))
        total_budget += b.amount
        total_spent += spent

    total_remaining = total_budget - total_spent

    return BudgetListResponse(
        month=target_month,
        year=target_year,
        total_budget=total_budget,
        total_spent=total_spent,
        total_remaining=total_remaining,
        items=items,
    )


@router.get(
    "/alerts",
    response_model=BudgetAlertResponse,
    summary="Lấy danh sách cảnh báo ngân sách (chạm 80% hoặc vượt hạn mức)",
)
def get_budget_alerts(
    month: Annotated[
        int | None,
        Query(ge=1, le=12, description="Tháng cần kiểm tra cảnh báo"),
    ] = None,
    year: Annotated[
        int | None,
        Query(ge=2000, le=2100, description="Năm cần kiểm tra cảnh báo"),
    ] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BudgetAlertResponse:
    """Return all budget alerts (warning >= 80% or exceeded >= 100%) for month."""
    budget_list = get_budgets(
        month=month, year=year, db=db, current_user=current_user
    )

    alert_items = []
    for item in budget_list.items:
        if item.status in ("warning", "exceeded"):
            alert_items.append(
                BudgetAlertItem(
                    id=item.id,
                    category_id=item.category_id,
                    category_name=item.category.name if item.category else "Danh mục",
                    category_icon=item.category.icon if item.category else "other",
                    category_color=item.category.color if item.category else "#D69A23",
                    amount=item.amount,
                    spent_amount=item.spent_amount,
                    percentage_used=item.percentage_used,
                    status=item.status,
                )
            )

    # Sort alerts by percentage_used descending
    alert_items.sort(key=lambda a: a.percentage_used, reverse=True)

    return BudgetAlertResponse(count=len(alert_items), items=alert_items)


@router.get(
    "/{budget_id}",
    response_model=BudgetResponse,
    summary="Xem chi tiết 1 ngân sách",
)
def get_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BudgetResponse:
    """Retrieve details and spending progress of a single budget."""
    budget = _owned_budget_or_404(db, budget_id, current_user.id)

    last_day = calendar.monthrange(budget.year, budget.month)[1]
    start_date = date(budget.year, budget.month, 1)
    end_date = date(budget.year, budget.month, last_day)

    spent_sum = (
        db.query(sa_func.coalesce(sa_func.sum(Transaction.amount), Decimal("0")))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.category_id == budget.category_id,
            Transaction.type == CategoryType.EXPENSE,
            Transaction.is_deleted.is_(False),
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        .scalar()
        or Decimal("0.00")
    )

    return _build_budget_response(budget, spent_sum)


@router.patch(
    "/{budget_id}",
    response_model=BudgetResponse,
    summary="Cập nhật hạn mức ngân sách",
)
def update_budget(
    budget_id: int,
    payload: BudgetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BudgetResponse:
    """Update amount of an existing budget."""
    budget = _owned_budget_or_404(db, budget_id, current_user.id)
    budget.amount = payload.amount
    db.commit()
    db.refresh(budget)

    last_day = calendar.monthrange(budget.year, budget.month)[1]
    start_date = date(budget.year, budget.month, 1)
    end_date = date(budget.year, budget.month, last_day)

    spent_sum = (
        db.query(sa_func.coalesce(sa_func.sum(Transaction.amount), Decimal("0")))
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.category_id == budget.category_id,
            Transaction.type == CategoryType.EXPENSE,
            Transaction.is_deleted.is_(False),
            Transaction.transaction_date >= start_date,
            Transaction.transaction_date <= end_date,
        )
        .scalar()
        or Decimal("0.00")
    )

    return _build_budget_response(budget, spent_sum)


@router.delete(
    "/{budget_id}",
    status_code=status.HTTP_200_OK,
    summary="Xóa ngân sách",
)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete a budget record permanently."""
    budget = _owned_budget_or_404(db, budget_id, current_user.id)
    db.delete(budget)
    db.commit()
    return {"detail": "Đã xóa ngân sách thành công."}
