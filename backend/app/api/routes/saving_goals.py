"""Saving goals API routes.

Provides thin HTTP endpoints delegating business logic to SavingService.
All endpoints enforce ownership via the current JWT user.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.enums import GoalStatus
from app.models.user import User
from app.schemas.saving_goal import (
    SavingContributionCreate,
    SavingGoalCreate,
    SavingGoalListResponse,
    SavingGoalResponse,
    SavingGoalUpdate,
    SavingWithdrawalCreate,
)
from app.services.saving_service import SavingService

router = APIRouter(prefix="/saving-goals", tags=["saving-goals"])


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
) -> SavingGoalResponse:
    """Create a new saving goal for the authenticated user, optionally with an initial deposit."""
    return SavingService(db, current_user).create_goal(payload)


@router.get(
    "",
    response_model=SavingGoalListResponse,
    summary="Lấy danh sách mục tiêu tiết kiệm",
)
def list_saving_goals(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    status_filter: Annotated[
        str | None,
        Query(alias="status", description="Lọc theo trạng thái mục tiêu: active, completed, cancelled, all"),
    ] = None,
) -> SavingGoalListResponse:
    """Retrieve all saving goals of the current user with aggregated summary statistics."""
    goal_status: GoalStatus | None = None
    if status_filter and status_filter.lower() != "all":
        try:
            goal_status = GoalStatus(status_filter.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Input should be 'active', 'completed', 'cancelled' or 'all'",
            )
    return SavingService(db, current_user).list_goals(status_filter=goal_status)


@router.get(
    "/{goal_id}",
    response_model=SavingGoalResponse,
    summary="Lấy thông tin chi tiết một mục tiêu tiết kiệm",
)
def get_saving_goal(
    goal_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SavingGoalResponse:
    """Get saving goal detail and contribution history."""
    return SavingService(db, current_user).get_goal(goal_id)


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
) -> SavingGoalResponse:
    """Update goal name, target amount, deadline or status."""
    return SavingService(db, current_user).update_goal(goal_id, payload)


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
) -> SavingGoalResponse:
    """Deposit money into a saving goal and update current_amount atomically."""
    return SavingService(db, current_user).contribute(goal_id, payload)


@router.post(
    "/{goal_id}/withdraw",
    response_model=SavingGoalResponse,
    summary="Rút tiền khỏi mục tiêu tiết kiệm",
)
def withdraw_from_goal(
    goal_id: int,
    payload: SavingWithdrawalCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SavingGoalResponse:
    """Withdraw saved money, preserve history, and release available balance."""
    return SavingService(db, current_user).withdraw(goal_id, payload)


@router.delete(
    "/{goal_id}",
    summary="Xóa mục tiêu tiết kiệm",
)
def delete_saving_goal(
    goal_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    """Delete a saving goal and its contribution history."""
    return SavingService(db, current_user).delete_goal(goal_id)
