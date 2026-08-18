"""Saving goals API routes.

Provides endpoints for creating, retrieving, updating, deleting saving goals,
and recording saving contributions (deposits) within atomic database transactions.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func as sa_func
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_db
from app.models.enums import CategoryType, ContributionSource, GoalStatus
from app.models.saving_contribution import SavingContribution
from app.models.saving_goal import SavingGoal
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.saving_goal import (
    SavingContributionCreate,
    SavingContributionResponse,
    SavingGoalCreate,
    SavingGoalListResponse,
    SavingGoalResponse,
    SavingGoalUpdate,
)

router = APIRouter(prefix="/saving-goals", tags=["saving-goals"])

GOAL_NOT_FOUND = "Không tìm thấy mục tiêu tiết kiệm."


def _get_goal_or_404(
    db: Session, goal_id: int, user_id: int, *, lock: bool = False
) -> SavingGoal:
    """Retrieve a saving goal owned by *user_id* or raise HTTP 404."""
    query = (
        db.query(SavingGoal)
        .options(selectinload(SavingGoal.contributions))
        .filter(SavingGoal.id == goal_id, SavingGoal.user_id == user_id)
    )
    if lock:
        query = query.with_for_update()
    goal = query.first()
    if goal is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=GOAL_NOT_FOUND,
        )
    return goal


def _lock_user_balance(db: Session, user_id: int) -> None:
    """Serialize every balance-changing operation for one user."""
    db.query(User.id).filter(User.id == user_id).with_for_update().one()


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


def _enrich_goal_response(goal: SavingGoal) -> SavingGoalResponse:
    """Compute progress percentage, remaining amount, days left, and format contributions."""
    target = Decimal(str(goal.target_amount))
    current = Decimal(str(goal.current_amount))

    # Calculate percentage
    progress = 0.0
    if target > Decimal("0"):
        progress = float(round((current / target) * 100, 1))

    # Calculate remaining amount
    remaining = max(Decimal("0.00"), target - current)

    # Calculate days remaining
    days_left: int | None = None
    if goal.deadline is not None:
        days_left = (goal.deadline - date.today()).days

    # Sort contributions newest first
    sorted_contributions = sorted(
        goal.contributions,
        key=lambda c: c.created_at,
        reverse=True,
    )
    contrib_responses = [
        SavingContributionResponse.model_validate(c) for c in sorted_contributions
    ]

    return SavingGoalResponse(
        id=goal.id,
        user_id=goal.user_id,
        name=goal.name,
        target_amount=target,
        current_amount=current,
        deadline=goal.deadline,
        status=goal.status,
        progress_percentage=progress,
        remaining_amount=remaining,
        days_remaining=days_left,
        contributions=contrib_responses,
        created_at=goal.created_at,
    )


@router.post(
    "",
    response_model=SavingGoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo mục tiêu tiết kiệm mới",
)
def create_saving_goal(
    payload: SavingGoalCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Create a new saving goal for the authenticated user, optionally with an initial deposit."""
    _lock_user_balance(db, current_user.id)
    initial_deposit = payload.initial_deposit or Decimal("0")
    if initial_deposit > Decimal("0"):
        available_balance = _get_user_available_balance(db, current_user.id)
        if initial_deposit > available_balance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Số tiền nạp ban đầu ({initial_deposit:,.0f} đ) vượt quá số dư khả dụng hiện có ({available_balance:,.0f} đ).",
            )

    initial_status = GoalStatus.ACTIVE
    if initial_deposit >= payload.target_amount:
        initial_status = GoalStatus.COMPLETED

    goal = SavingGoal(
        user_id=current_user.id,
        name=payload.name.strip(),
        target_amount=payload.target_amount,
        current_amount=initial_deposit,
        deadline=payload.deadline,
        status=initial_status,
    )
    db.add(goal)
    db.flush()  # populate goal.id

    if initial_deposit > Decimal("0"):
        contribution = SavingContribution(
            saving_goal_id=goal.id,
            amount=initial_deposit,
            source=ContributionSource.MANUAL,
            note="Khoản nạp ban đầu",
        )
        db.add(contribution)

    db.commit()
    db.refresh(goal)
    return _enrich_goal_response(goal)


@router.get(
    "",
    response_model=SavingGoalListResponse,
    summary="Lấy danh sách mục tiêu tiết kiệm",
)
def list_saving_goals(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[
        GoalStatus | None,
        Query(alias="status", description="Lọc theo trạng thái mục tiêu"),
    ] = None,
):
    """Retrieve all saving goals of the current user with aggregated summary statistics."""
    # Query all goals of user for summary metrics
    all_goals = (
        db.query(SavingGoal)
        .options(selectinload(SavingGoal.contributions))
        .filter(SavingGoal.user_id == current_user.id)
        .order_by(desc(SavingGoal.created_at))
        .all()
    )

    total_target = Decimal("0.00")
    total_current = Decimal("0.00")
    active_count = 0
    completed_count = 0

    for g in all_goals:
        total_target += Decimal(str(g.target_amount))
        total_current += Decimal(str(g.current_amount))
        if g.status == GoalStatus.ACTIVE:
            active_count += 1
        elif g.status == GoalStatus.COMPLETED:
            completed_count += 1

    # Filter items if requested
    filtered_goals = all_goals
    if status_filter is not None:
        filtered_goals = [g for g in all_goals if g.status == status_filter]

    items = [_enrich_goal_response(g) for g in filtered_goals]

    return SavingGoalListResponse(
        total_target_amount=total_target,
        total_current_amount=total_current,
        total_goals_count=len(all_goals),
        active_goals_count=active_count,
        completed_goals_count=completed_count,
        items=items,
    )


@router.get(
    "/{goal_id}",
    response_model=SavingGoalResponse,
    summary="Lấy thông tin chi tiết một mục tiêu tiết kiệm",
)
def get_saving_goal(
    goal_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Get saving goal detail and contribution history."""
    goal = _get_goal_or_404(db, goal_id, current_user.id)
    return _enrich_goal_response(goal)


@router.patch(
    "/{goal_id}",
    response_model=SavingGoalResponse,
    summary="Cập nhật mục tiêu tiết kiệm",
)
def update_saving_goal(
    goal_id: int,
    payload: SavingGoalUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Update goal name, target amount, deadline or status."""
    _lock_user_balance(db, current_user.id)
    goal = _get_goal_or_404(db, goal_id, current_user.id, lock=True)

    if goal.status == GoalStatus.COMPLETED or goal.current_amount >= goal.target_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mục tiêu đã hoàn thành không thể chỉnh sửa.",
        )

    if payload.name is not None:
        name_val = payload.name.strip()
        if not name_val:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tên mục tiêu không được để trống.",
            )
        goal.name = name_val

    if payload.target_amount is not None:
        goal.target_amount = payload.target_amount
        # Recheck status if active / completed
        if goal.current_amount >= goal.target_amount and goal.status == GoalStatus.ACTIVE:
            goal.status = GoalStatus.COMPLETED
        elif goal.current_amount < goal.target_amount and goal.status == GoalStatus.COMPLETED and payload.status is None:
            goal.status = GoalStatus.ACTIVE

    if payload.deadline is not None:
        goal.deadline = payload.deadline

    if payload.status is not None:
        if (
            goal.status == GoalStatus.CANCELLED
            and payload.status != GoalStatus.CANCELLED
        ):
            available_balance = _get_user_available_balance(db, current_user.id)
            if Decimal(str(goal.current_amount)) > available_balance:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Không thể kích hoạt lại mục tiêu vì số tiền đang tích lũy "
                        "vượt quá số dư khả dụng hiện có."
                    ),
                )
        goal.status = payload.status

    db.commit()
    db.refresh(goal)
    return _enrich_goal_response(goal)


@router.post(
    "/{goal_id}/contribute",
    response_model=SavingGoalResponse,
    summary="Nạp tiền tiết kiệm vào mục tiêu",
)
def contribute_to_goal(
    goal_id: int,
    payload: SavingContributionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Deposit money into a saving goal and update current_amount atomically."""
    _lock_user_balance(db, current_user.id)
    goal = _get_goal_or_404(db, goal_id, current_user.id, lock=True)

    if goal.status == GoalStatus.COMPLETED or goal.current_amount >= goal.target_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mục tiêu đã hoàn thành, không thể nạp thêm tiền.",
        )

    if goal.status == GoalStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể nạp tiền vào mục tiêu đã bị hủy hoặc tạm dừng.",
        )

    # Validate remaining needed amount
    remaining_needed = Decimal(str(goal.target_amount)) - Decimal(str(goal.current_amount))
    if payload.amount > remaining_needed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Số tiền nạp ({payload.amount:,.0f} đ) vượt quá số tiền còn thiếu của mục tiêu ({remaining_needed:,.0f} đ).",
        )

    available_balance = _get_user_available_balance(db, current_user.id)
    if payload.amount > available_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Số tiền nạp ({payload.amount:,.0f} đ) vượt quá số dư khả dụng hiện có ({available_balance:,.0f} đ).",
        )

    contribution = SavingContribution(
        saving_goal_id=goal.id,
        transaction_id=None,
        amount=payload.amount,
        source=ContributionSource.MANUAL,
        note=payload.note.strip() if payload.note else None,
    )
    db.add(contribution)

    # Increment current_amount
    new_amount = Decimal(str(goal.current_amount)) + payload.amount
    goal.current_amount = new_amount

    # Auto-complete if 100% target reached
    if goal.current_amount >= goal.target_amount and goal.status == GoalStatus.ACTIVE:
        goal.status = GoalStatus.COMPLETED

    db.commit()
    db.refresh(goal)
    return _enrich_goal_response(goal)


@router.delete(
    "/{goal_id}",
    summary="Xóa mục tiêu tiết kiệm",
)
def delete_saving_goal(
    goal_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Delete a saving goal and its contribution history."""
    _lock_user_balance(db, current_user.id)
    goal = _get_goal_or_404(db, goal_id, current_user.id, lock=True)
    db.delete(goal)
    db.commit()
    return {"detail": "Đã xóa mục tiêu tiết kiệm thành công."}
