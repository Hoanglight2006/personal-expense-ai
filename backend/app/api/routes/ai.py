"""AI and Trend Analytics API routes.

Provides endpoints for:
- 6-month monthly financial trends (Income vs Expense vs Savings)
- AI Monthly Report according to REQUIREMENTS.md prompt specs
- AI Budget Recommendations and 1-click batch application
"""

from datetime import date
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.ai_service import (
    apply_budget_recommendations,
    generate_budget_recommendations,
    generate_monthly_ai_report,
    get_monthly_trend_data,
)
from app.models.user import User
from app.schemas.ai import (
    ApplyBudgetRecommendationsRequest,
    ApplyBudgetRecommendationsResponse,
    BudgetRecommendationResponse,
    MonthlyReportRequest,
    MonthlyReportResponse,
    MonthlyTrendResponse,
)

router = APIRouter(prefix="/ai", tags=["ai"])


# ---------------------------------------------------------------------------
# 1. Financial Trend Analytics
# ---------------------------------------------------------------------------


@router.get(
    "/trend",
    response_model=MonthlyTrendResponse,
    summary="Thống kê xu hướng thu chi qua chuỗi thời gian (6 tháng gần nhất)",
)
def get_trend_statistics(
    months: Annotated[int, Query(ge=1, le=24, description="Số tháng thống kê")] = 6,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MonthlyTrendResponse:
    """Return historical income, expense and net savings trend across months."""
    return get_monthly_trend_data(db, current_user.id, months=months)


# ---------------------------------------------------------------------------
# 2. AI Monthly Spending Report
# ---------------------------------------------------------------------------


@router.post(
    "/monthly-report",
    response_model=MonthlyReportResponse,
    summary="Sinh báo cáo phân tích chi tiêu AI theo tháng",
)
async def create_monthly_report(
    payload: MonthlyReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MonthlyReportResponse:
    """Generate structured AI monthly financial report following REQUIREMENTS.md."""
    return await generate_monthly_ai_report(db, current_user.id, payload.month)


# ---------------------------------------------------------------------------
# 3. AI Budget Recommendations
# ---------------------------------------------------------------------------


@router.get(
    "/budget-recommendations",
    response_model=BudgetRecommendationResponse,
    summary="Lấy gợi ý ngân sách từ AI dựa trên lịch sử chi tiêu",
)
async def get_ai_budget_recommendations(
    month: Annotated[
        str | None,
        Query(
            pattern=r"^\d{4}-\d{2}$",
            description="Tháng cần lập ngân sách (YYYY-MM). Mặc định là tháng tiếp theo.",
        ),
    ] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BudgetRecommendationResponse:
    """Compute 1-3 month historical averages and generate AI budget suggestions."""
    today = date.today()
    if month:
        parts = month.split("-")
        target_year = int(parts[0])
        target_month = int(parts[1])
    else:
        # Next month by default
        target_month = today.month + 1 if today.month < 12 else 1
        target_year = today.year if today.month < 12 else today.year + 1

    return await generate_budget_recommendations(
        db, current_user.id, target_month=target_month, target_year=target_year
    )


@router.post(
    "/apply-budget-recommendations",
    response_model=ApplyBudgetRecommendationsResponse,
    summary="Áp dụng hàng loạt ngân sách gợi ý vào hệ thống",
)
def apply_ai_budget_recommendations(
    payload: ApplyBudgetRecommendationsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplyBudgetRecommendationsResponse:
    """Apply the selected AI budget recommendations into user's budget table."""
    applied_count, msg = apply_budget_recommendations(
        db,
        current_user.id,
        target_month=payload.target_month,
        target_year=payload.target_year,
        recommendations=payload.recommendations,
    )
    return ApplyBudgetRecommendationsResponse(
        success=True,
        applied_count=applied_count,
        message=msg,
    )
