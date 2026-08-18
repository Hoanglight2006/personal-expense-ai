"""Transaction management API routes.

Supports CRUD, soft-delete/restore, duplicate preparation, search/filter/sort
and paginated listing.  All endpoints enforce ownership via the current JWT user.
"""

import calendar
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func as sa_func, or_
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.category import Category
from app.models.enums import CategoryType, ContributionSource, GoalStatus, PaymentMethod
from app.models.idempotency import ImportIdempotencyKey
from app.models.saving_contribution import SavingContribution
from app.models.saving_goal import SavingGoal
from app.models.saving_withdrawal_allocation import SavingWithdrawalAllocation
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import (
    BulkImportRequest,
    BulkImportResponse,
    CategoryInfo,
    RowResult,
    TransactionCreate,
    TransactionListResponse,
    TransactionResponse,
    TransactionRestoreResponse,
    TransactionSort,
    TransactionSummaryResponse,
    TransactionUpdate,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])

TRANSACTION_NOT_FOUND = "Không tìm thấy giao dịch."
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _recomputed_goal_current_amount(
    db: Session,
    goal_id: int,
    *,
    exclude_transaction_id: int | None = None,
    restore_transaction_id: int | None = None,
) -> Decimal:
    """Rebuild savings from effective deposits minus their consumed amounts."""
    manual_contributions = (
        db.query(SavingContribution)
        .filter(
            SavingContribution.saving_goal_id == goal_id,
            SavingContribution.source == ContributionSource.MANUAL,
        )
        .all()
    )

    allocation_query = (
        db.query(SavingContribution)
        .join(Transaction, Transaction.id == SavingContribution.transaction_id)
        .filter(
            SavingContribution.saving_goal_id == goal_id,
            SavingContribution.source == ContributionSource.INCOME_ALLOCATION,
        )
    )
    if restore_transaction_id is not None:
        allocation_query = allocation_query.filter(
            or_(
                Transaction.is_deleted.is_(False),
                Transaction.id == restore_transaction_id,
            )
        )
    else:
        allocation_query = allocation_query.filter(Transaction.is_deleted.is_(False))
    if exclude_transaction_id is not None:
        allocation_query = allocation_query.filter(
            Transaction.id != exclude_transaction_id
        )

    effective_contributions = manual_contributions + allocation_query.all()
    contribution_ids = [contribution.id for contribution in effective_contributions]
    allocated_by_contribution = {
        contribution_id: Decimal(str(allocated_amount))
        for contribution_id, allocated_amount in (
            db.query(
                SavingWithdrawalAllocation.contribution_id,
                sa_func.coalesce(sa_func.sum(SavingWithdrawalAllocation.amount), 0),
            )
            .filter(SavingWithdrawalAllocation.contribution_id.in_(contribution_ids))
            .group_by(SavingWithdrawalAllocation.contribution_id)
            .all()
            if contribution_ids
            else []
        )
    }
    return sum(
        (
            max(
                Decimal("0.00"),
                Decimal(str(contribution.amount))
                - allocated_by_contribution.get(contribution.id, Decimal("0.00")),
            )
            for contribution in effective_contributions
        ),
        Decimal("0.00"),
    )


def _owned_transaction_or_404(
    db: Session,
    transaction_id: int,
    user_id: int,
    *,
    include_deleted: bool = False,
) -> Transaction:
    """Return a Transaction owned by *user_id* or raise 404."""
    query = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id,
    )
    if not include_deleted:
        query = query.filter(Transaction.is_deleted.is_(False))
    txn = query.first()
    if txn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=TRANSACTION_NOT_FOUND
        )
    return txn


def _validate_category(
    db: Session,
    category_id: int,
    user_id: int,
    transaction_type: CategoryType,
    *,
    require_active: bool = True,
) -> Category:
    """Ensure the category belongs to the user and is not deleted.

    When *require_active* is ``True`` (default for new transactions), the
    category must also be active.
    """
    category = (
        db.query(Category)
        .filter(
            Category.id == category_id,
            Category.user_id == user_id,
            Category.deleted_at.is_(None),
        )
        .with_for_update()
        .first()
    )
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy danh mục.",
        )
    if require_active and not category.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Không thể sử dụng danh mục đã ẩn cho giao dịch mới.",
        )
    if category.type != transaction_type.value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Loại giao dịch không khớp với loại danh mục.",
        )
    return category


def _transaction_response(txn: Transaction) -> TransactionResponse:
    category_info = None
    if txn.category:
        category_info = CategoryInfo(
            id=txn.category.id,
            name=txn.category.name,
            icon=txn.category.icon,
            color=txn.category.color,
            is_active=txn.category.is_active,
        )
    return TransactionResponse(
        id=txn.id,
        amount=txn.amount,
        type=txn.type,
        category_id=txn.category_id,
        category=category_info,
        transaction_date=txn.transaction_date,
        description=txn.description,
        payment_method=txn.payment_method,
        is_deleted=txn.is_deleted,
        created_at=txn.created_at,
        updated_at=txn.updated_at,
        deleted_at=txn.deleted_at,
    )


def _get_user_available_balance(db: Session, user_id: int) -> Decimal:
    """Compute available unallocated balance = Total Income - Total Expense - Total in Active/Completed Saving Goals."""
    income_sum = (
        db.query(sa_func.coalesce(sa_func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == CategoryType.INCOME,
            Transaction.is_deleted.is_(False),
        )
        .scalar()
    )
    expense_sum = (
        db.query(sa_func.coalesce(sa_func.sum(Transaction.amount), 0))
        .filter(
            Transaction.user_id == user_id,
            Transaction.type == CategoryType.EXPENSE,
            Transaction.is_deleted.is_(False),
        )
        .scalar()
    )
    saving_sum = (
        db.query(sa_func.coalesce(sa_func.sum(SavingGoal.current_amount), 0))
        .filter(
            SavingGoal.user_id == user_id,
            SavingGoal.status != GoalStatus.CANCELLED,
        )
        .scalar()
    )
    return Decimal(str(income_sum)) - Decimal(str(expense_sum)) - Decimal(str(saving_sum))


def _lock_user_balance(db: Session, user_id: int) -> None:
    """Serialize balance-changing operations for one user until commit/rollback."""
    db.query(User.id).filter(User.id == user_id).with_for_update().one()


def _balance_effect(transaction_type: CategoryType, amount: Decimal) -> Decimal:
    normalized_amount = Decimal(str(amount))
    return normalized_amount if transaction_type == CategoryType.INCOME else -normalized_amount


def _ensure_projected_balance(
    db: Session,
    user_id: int,
    delta: Decimal,
    detail: str,
) -> None:
    if _get_user_available_balance(db, user_id) + delta < Decimal("0"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def _commit_or_raise(db: Session) -> None:
    try:
        db.commit()
    except DataError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Dữ liệu giao dịch vượt quá giới hạn lưu trữ.",
        )
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Dữ liệu giao dịch xung đột. Vui lòng thử lại.",
        )


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    _lock_user_balance(db, current_user.id)
    _validate_category(
        db, payload.category_id, current_user.id, payload.type, require_active=True
    )

    allocation = (
        payload.saving_goal_amount
        if payload.saving_goal_id is not None and payload.saving_goal_amount is not None
        else Decimal("0")
    )
    delta = _balance_effect(payload.type, payload.amount) - allocation
    _ensure_projected_balance(
        db,
        current_user.id,
        delta,
        (
            f"Số tiền chi tiêu ({payload.amount:,.0f} đ) vượt quá số dư khả dụng "
            "hiện có. Vui lòng thêm thu nhập trước khi chi tiêu."
        ),
    )

    goal = None
    if payload.type == CategoryType.INCOME and payload.saving_goal_id is not None:
        goal = (
            db.query(SavingGoal)
            .filter(
                SavingGoal.id == payload.saving_goal_id,
                SavingGoal.user_id == current_user.id,
            )
            .with_for_update()
            .first()
        )
        if goal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy mục tiêu tiết kiệm.",
            )
        if goal.status == GoalStatus.COMPLETED or goal.current_amount >= goal.target_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mục tiêu tiết kiệm đã hoàn thành, không thể trích thêm tiền.",
            )
        if goal.status == GoalStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mục tiêu tiết kiệm đã bị hủy hoặc tạm dừng.",
            )

        remaining_needed = Decimal(str(goal.target_amount)) - Decimal(str(goal.current_amount))
        if payload.saving_goal_amount is not None and payload.saving_goal_amount > remaining_needed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Số tiền trích ({payload.saving_goal_amount:,.0f} đ) vượt quá số tiền còn thiếu của mục tiêu ({remaining_needed:,.0f} đ).",
            )

    txn = Transaction(
        user_id=current_user.id,
        category_id=payload.category_id,
        type=payload.type,
        amount=payload.amount,
        description=payload.description,
        transaction_date=payload.transaction_date,
        payment_method=payload.payment_method,
    )
    db.add(txn)
    db.flush()

    if goal is not None and payload.saving_goal_amount is not None:
        contrib = SavingContribution(
            saving_goal_id=goal.id,
            transaction_id=txn.id,
            amount=payload.saving_goal_amount,
            source=ContributionSource.INCOME_ALLOCATION,
            note=f"Trích từ nguồn thu: {txn.description or 'Thu nhập'}",
        )
        db.add(contrib)
        goal.current_amount = Decimal(str(goal.current_amount)) + payload.saving_goal_amount
        if goal.current_amount >= goal.target_amount and goal.status == GoalStatus.ACTIVE:
            goal.status = GoalStatus.COMPLETED

    _commit_or_raise(db)
    db.refresh(txn)
    return _transaction_response(txn)


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    search: Annotated[str | None, Query(max_length=255)] = None,
    date_start: date | None = None,
    date_end: date | None = None,
    amount_min: Decimal | None = None,
    amount_max: Decimal | None = None,
    type: CategoryType | None = None,
    category_id: int | None = None,
    payment_method: PaymentMethod | None = None,
    sort: TransactionSort = "date_desc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionListResponse:
    # Validate ranges
    if date_start and date_end and date_start > date_end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Ngày bắt đầu không được sau ngày kết thúc.",
        )
    if amount_min is not None and amount_max is not None and amount_min > amount_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Số tiền tối thiểu không được lớn hơn số tiền tối đa.",
        )
    if category_id is not None:
        # Ensure the category belongs to the user; hidden categories are OK in filters
        cat = (
            db.query(Category)
            .filter(Category.id == category_id, Category.user_id == current_user.id)
            .first()
        )
        if cat is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy danh mục.",
            )

    query = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.is_deleted.is_(False),
    )

    # Apply filters
    if search:
        keyword = search.strip()
        if keyword:
            query = query.filter(
                Transaction.description.contains(keyword, autoescape=True)
            )
    if date_start:
        query = query.filter(Transaction.transaction_date >= date_start)
    if date_end:
        query = query.filter(Transaction.transaction_date <= date_end)
    if amount_min is not None:
        query = query.filter(Transaction.amount >= amount_min)
    if amount_max is not None:
        query = query.filter(Transaction.amount <= amount_max)
    if type:
        query = query.filter(Transaction.type == type)
    if category_id is not None:
        query = query.filter(Transaction.category_id == category_id)
    if payment_method:
        query = query.filter(Transaction.payment_method == payment_method)

    total_count = query.count()

    # Apply sort
    if sort == "date_asc":
        query = query.order_by(Transaction.transaction_date.asc(), Transaction.id.asc())
    elif sort == "amount_desc":
        query = query.order_by(Transaction.amount.desc(), Transaction.id.desc())
    elif sort == "amount_asc":
        query = query.order_by(Transaction.amount.asc(), Transaction.id.asc())
    else:  # date_desc (default)
        query = query.order_by(
            Transaction.transaction_date.desc(), Transaction.id.desc()
        )

    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    return TransactionListResponse(
        items=[_transaction_response(txn) for txn in items],
        total_count=total_count,
        page=page,
        page_size=page_size,
    )


@router.get("/trash", response_model=TransactionListResponse)
def list_trash(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    sort: TransactionSort = "date_desc",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionListResponse:
    query = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.is_deleted.is_(True),
    )
    total_count = query.count()

    if sort == "date_asc":
        query = query.order_by(Transaction.transaction_date.asc(), Transaction.id.asc())
    elif sort == "amount_desc":
        query = query.order_by(Transaction.amount.desc(), Transaction.id.desc())
    elif sort == "amount_asc":
        query = query.order_by(Transaction.amount.asc(), Transaction.id.asc())
    else:
        query = query.order_by(
            Transaction.transaction_date.desc(), Transaction.id.desc()
        )

    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    return TransactionListResponse(
        items=[_transaction_response(txn) for txn in items],
        total_count=total_count,
        page=page,
        page_size=page_size,
    )


@router.get("/summary", response_model=TransactionSummaryResponse)
def get_transaction_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionSummaryResponse:
    """Return financial summary metrics: initial balance, all-time flow, and current month flow."""
    today = date.today()
    first_of_month = today.replace(day=1)
    last_day = calendar.monthrange(today.year, today.month)[1]
    last_of_month = today.replace(day=last_day)

    # 1. All-time income & expense
    all_time_stats = (
        db.query(
            Transaction.type,
            sa_func.coalesce(sa_func.sum(Transaction.amount), 0).label("total"),
        )
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.is_deleted.is_(False),
        )
        .group_by(Transaction.type)
        .all()
    )
    all_time_income = Decimal("0.00")
    all_time_expense = Decimal("0.00")
    for txn_type, total in all_time_stats:
        if txn_type == CategoryType.INCOME:
            all_time_income = Decimal(total).quantize(Decimal("0.01"))
        elif txn_type == CategoryType.EXPENSE:
            all_time_expense = Decimal(total).quantize(Decimal("0.01"))

    # 2. Month income & expense
    month_stats = (
        db.query(
            Transaction.type,
            sa_func.coalesce(sa_func.sum(Transaction.amount), 0).label("total"),
        )
        .filter(
            Transaction.user_id == current_user.id,
            Transaction.is_deleted.is_(False),
            Transaction.transaction_date >= first_of_month,
            Transaction.transaction_date <= last_of_month,
        )
        .group_by(Transaction.type)
        .all()
    )
    month_income = Decimal("0.00")
    month_expense = Decimal("0.00")
    for txn_type, total in month_stats:
        if txn_type == CategoryType.INCOME:
            month_income = Decimal(total).quantize(Decimal("0.01"))
        elif txn_type == CategoryType.EXPENSE:
            month_expense = Decimal(total).quantize(Decimal("0.01"))

    # 3. Total in active/completed Saving Goals
    saving_balance_raw = (
        db.query(sa_func.coalesce(sa_func.sum(SavingGoal.current_amount), 0))
        .filter(
            SavingGoal.user_id == current_user.id,
            SavingGoal.status != GoalStatus.CANCELLED,
        )
        .scalar()
    )
    saving_balance = Decimal(str(saving_balance_raw)).quantize(Decimal("0.01"))

    total_balance = all_time_income - all_time_expense
    available_balance = total_balance - saving_balance
    month_net = month_income - month_expense

    return TransactionSummaryResponse(
        total_balance=total_balance,
        available_balance=available_balance,
        saving_balance=saving_balance,
        all_time_income=all_time_income,
        all_time_expense=all_time_expense,
        month_income=month_income,
        month_expense=month_expense,
        month_net=month_net,
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    txn = _owned_transaction_or_404(db, transaction_id, current_user.id)
    return _transaction_response(txn)


@router.patch("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    _lock_user_balance(db, current_user.id)
    txn = _owned_transaction_or_404(db, transaction_id, current_user.id)

    changes = payload.model_dump(exclude_unset=True)

    # Resolve effective type and category_id after potential changes
    effective_type = changes.get("type", txn.type)
    effective_category_id = changes.get("category_id", txn.category_id)
    effective_amount = Decimal(str(changes.get("amount", txn.amount)))

    # If transaction has linked saving contributions, protect data integrity
    contributions = (
        db.query(SavingContribution)
        .filter(SavingContribution.transaction_id == txn.id)
        .all()
    )
    if contributions:
        total_allocated = sum(Decimal(str(c.amount)) for c in contributions)
        if effective_type == CategoryType.EXPENSE and txn.type == CategoryType.INCOME:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Giao dịch thu nhập này đang trích {total_allocated:,.0f} đ vào mục tiêu tiết kiệm, không thể đổi loại thành chi tiêu.",
            )
        if "amount" in changes and Decimal(str(changes["amount"])) < total_allocated:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Số tiền thu nhập mới ({changes['amount']:,.0f} đ) không thể nhỏ hơn tổng số tiền đã trích vào mục tiêu tiết kiệm ({total_allocated:,.0f} đ).",
            )

    old_effect = _balance_effect(txn.type, Decimal(str(txn.amount)))
    new_effect = _balance_effect(effective_type, effective_amount)
    balance_error = "Thay đổi này sẽ làm số dư khả dụng bị âm."
    if (
        txn.type == CategoryType.EXPENSE
        and effective_type == CategoryType.EXPENSE
        and effective_amount > Decimal(str(txn.amount))
    ):
        balance_error = "Số tiền chi tiêu tăng thêm vượt quá số dư khả dụng hiện có."
    _ensure_projected_balance(
        db,
        current_user.id,
        new_effect - old_effect,
        balance_error,
    )

    # If category or type is changing, validate the new combination
    if "category_id" in changes or "type" in changes:
        # If the category is changing, the new one must be active
        category_is_changing = (
            "category_id" in changes and changes["category_id"] != txn.category_id
        )
        _validate_category(
            db,
            effective_category_id,
            current_user.id,
            effective_type,
            require_active=category_is_changing,
        )

    for field, value in changes.items():
        setattr(txn, field, value)

    _commit_or_raise(db)
    db.refresh(txn)
    return _transaction_response(txn)


@router.post("/{transaction_id}/trash", response_model=TransactionResponse)
def trash_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    _lock_user_balance(db, current_user.id)
    txn = _owned_transaction_or_404(db, transaction_id, current_user.id)

    # Adjust linked saving goals when income transaction is trashed
    contributions = (
        db.query(SavingContribution)
        .filter(SavingContribution.transaction_id == txn.id)
        .all()
    )
    goal_ids = sorted({contribution.saving_goal_id for contribution in contributions})
    linked_goals = (
        db.query(SavingGoal)
        .filter(
            SavingGoal.id.in_(goal_ids),
            SavingGoal.user_id == current_user.id,
        )
        .order_by(SavingGoal.id)
        .with_for_update()
        .all()
        if goal_ids
        else []
    )
    projected_goal_amounts = {
        goal.id: _recomputed_goal_current_amount(
            db,
            goal.id,
            exclude_transaction_id=txn.id,
        )
        for goal in linked_goals
    }
    released_savings = sum(
        (
            Decimal(str(goal.current_amount)) - projected_goal_amounts[goal.id]
            for goal in linked_goals
            if goal.status != GoalStatus.CANCELLED
        ),
        Decimal("0"),
    )
    _ensure_projected_balance(
        db,
        current_user.id,
        -_balance_effect(txn.type, Decimal(str(txn.amount))) + released_savings,
        "Không thể xóa nguồn thu vì thao tác này sẽ làm số dư khả dụng bị âm.",
    )
    for goal in linked_goals:
        goal.current_amount = projected_goal_amounts[goal.id]
        if goal.status == GoalStatus.COMPLETED and goal.current_amount < goal.target_amount:
            goal.status = GoalStatus.ACTIVE

    txn.is_deleted = True
    txn.deleted_at = datetime.now(timezone.utc)
    _commit_or_raise(db)
    db.refresh(txn)
    return _transaction_response(txn)


@router.post("/{transaction_id}/restore", response_model=TransactionRestoreResponse)
def restore_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionRestoreResponse:
    _lock_user_balance(db, current_user.id)
    txn = _owned_transaction_or_404(
        db, transaction_id, current_user.id, include_deleted=True
    )
    if not txn.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Giao dịch này không nằm trong thùng rác.",
        )

    # Restore linked contribution amounts whenever the goal still exists.
    # Cancelled goals remain excluded from available-balance calculations, but
    # their current_amount must stay consistent with contribution history so a
    # later reactivation reserves the restored allocation again.
    contributions = (
        db.query(SavingContribution)
        .filter(SavingContribution.transaction_id == txn.id)
        .all()
    )
    goal_ids = sorted({contribution.saving_goal_id for contribution in contributions})
    linked_goals = (
        db.query(SavingGoal)
        .filter(
            SavingGoal.id.in_(goal_ids),
            SavingGoal.user_id == current_user.id,
        )
        .order_by(SavingGoal.id)
        .with_for_update()
        .all()
        if goal_ids
        else []
    )
    projected_goal_amounts = {
        goal.id: _recomputed_goal_current_amount(
            db,
            goal.id,
            restore_transaction_id=txn.id,
        )
        for goal in linked_goals
    }
    restored_savings = sum(
        (
            projected_goal_amounts[goal.id] - Decimal(str(goal.current_amount))
            for goal in linked_goals
            if goal.status != GoalStatus.CANCELLED
        ),
        Decimal("0"),
    )
    _ensure_projected_balance(
        db,
        current_user.id,
        _balance_effect(txn.type, Decimal(str(txn.amount))) - restored_savings,
        (
            "Khôi phục giao dịch chi tiêu sẽ làm số dư khả dụng bị âm."
            if txn.type == CategoryType.EXPENSE
            else "Không thể khôi phục giao dịch vì thao tác này sẽ làm số dư khả dụng bị âm."
        ),
    )
    for goal in linked_goals:
        goal.current_amount = projected_goal_amounts[goal.id]
        if goal.current_amount >= goal.target_amount and goal.status == GoalStatus.ACTIVE:
            goal.status = GoalStatus.COMPLETED

    warning = None
    category = (
        db.query(Category)
        .filter(Category.id == txn.category_id, Category.user_id == current_user.id)
        .first()
    )
    if category and not category.is_active:
        warning = (
            f'Danh mục "{category.name}" hiện đã ẩn. '
            "Giao dịch được khôi phục nhưng bạn nên cập nhật danh mục."
        )

    txn.is_deleted = False
    txn.deleted_at = None
    _commit_or_raise(db)
    db.refresh(txn)
    return TransactionRestoreResponse(
        transaction=_transaction_response(txn),
        category_warning=warning,
    )


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction_permanently(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    txn = _owned_transaction_or_404(
        db, transaction_id, current_user.id, include_deleted=True
    )
    if not txn.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Giao dịch phải ở trong thùng rác trước khi xóa vĩnh viễn.",
        )
    # Remove associated saving contributions
    db.query(SavingContribution).filter(
        SavingContribution.transaction_id == txn.id
    ).delete(synchronize_session=False)

    db.delete(txn)
    _commit_or_raise(db)


@router.post("/{transaction_id}/duplicate", response_model=TransactionResponse)
def duplicate_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    """Return the data of a transaction suitable for pre-filling a create form.

    Does NOT create a new record. The frontend opens a create form with the
    returned data (except id, timestamps and deletion state).
    """
    txn = _owned_transaction_or_404(db, transaction_id, current_user.id)
    return _transaction_response(txn)


# ---------------------------------------------------------------------------
# Bulk import (confirmed rows from Excel / OCR preview)
# ---------------------------------------------------------------------------


@router.post("/import", response_model=BulkImportResponse)
def import_transactions(
    payload: BulkImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BulkImportResponse:
    """Import a batch of user-confirmed transactions.

    Uses a database-backed idempotency key to prevent duplicate submissions across workers.
    """
    _lock_user_balance(db, current_user.id)
    existing_key = (
        db.query(ImportIdempotencyKey)
        .filter(
            ImportIdempotencyKey.user_id == current_user.id,
            ImportIdempotencyKey.idempotency_key == payload.idempotency_key,
        )
        .first()
    )
    if existing_key is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Phiên nhập này đã được xử lý. Vui lòng tải lại trang để nhập mới.",
        )

    results: list[RowResult] = []
    success_count = 0
    error_count = 0
    current_avail = _get_user_available_balance(db, current_user.id)

    for idx, row in enumerate(payload.rows):
        try:
            with db.begin_nested():
                # Validate category
                cat = (
                    db.query(Category)
                    .filter(
                        Category.id == row.category_id,
                        Category.user_id == current_user.id,
                        Category.deleted_at.is_(None),
                    )
                    .with_for_update()
                    .first()
                )
                if cat is None:
                    raise ValueError("Không tìm thấy danh mục.")
                if not cat.is_active:
                    raise ValueError("Không thể sử dụng danh mục đã ẩn.")
                if cat.type != row.type.value:
                    raise ValueError("Loại giao dịch không khớp với loại danh mục.")

                next_avail = current_avail + _balance_effect(row.type, row.amount)
                if next_avail < Decimal("0"):
                    if row.type == CategoryType.EXPENSE:
                        raise ValueError(
                            f"Số tiền chi tiêu ({row.amount:,.0f} đ) vượt quá số dư khả dụng hiện có ({current_avail:,.0f} đ)."
                        )

                txn = Transaction(
                    user_id=current_user.id,
                    category_id=row.category_id,
                    type=row.type,
                    amount=row.amount,
                    description=row.description,
                    transaction_date=row.transaction_date,
                    payment_method=row.payment_method,
                )
                db.add(txn)
                db.flush()
            current_avail = next_avail
            results.append(
                RowResult(index=idx, status="success", transaction_id=txn.id)
            )
            success_count += 1
        except (ValueError, HTTPException, Exception) as exc:
            msg = exc.detail if isinstance(exc, HTTPException) else str(exc)
            results.append(RowResult(index=idx, status="error", error=msg))
            error_count += 1

    if success_count > 0:
        db.add(
            ImportIdempotencyKey(
                user_id=current_user.id,
                idempotency_key=payload.idempotency_key,
            )
        )
        _commit_or_raise(db)

    return BulkImportResponse(
        total=len(payload.rows),
        success_count=success_count,
        error_count=error_count,
        skipped_count=0,
        results=results,
    )
