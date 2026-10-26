"""Budget management and spending alerts API routes.

Provides thin HTTP endpoints delegating business logic to BudgetService.
All endpoints enforce ownership via the current JWT user.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.budget import (
    BudgetAlertResponse,
    BudgetCreate,
    BudgetListResponse,
    BudgetResponse,
    BudgetUpdate,
)
from app.services.budget_service import BudgetService

router = APIRouter(prefix="/budgets", tags=["budgets"])


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
    return BudgetService(db, current_user).create_budget(payload)


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
    return BudgetService(db, current_user).get_budgets(month=month, year=year)


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
    return BudgetService(db, current_user).get_budget_alerts(month=month, year=year)


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
    return BudgetService(db, current_user).get_budget(budget_id)


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
    return BudgetService(db, current_user).update_budget(budget_id, payload)


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
    return BudgetService(db, current_user).delete_budget(budget_id)
