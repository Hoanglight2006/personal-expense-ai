"""Schemas for AI Features and Trend Analytics."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Monthly Trend Schemas
# ---------------------------------------------------------------------------


class MonthlyTrendItem(BaseModel):
    """Data point for a single month in trend analytics."""

    month: str = Field(..., description="Month in YYYY-MM format")
    year: int
    month_num: int
    label: str = Field(..., description="Human-readable label, e.g. 'Thg 08/2026'")
    total_income: Decimal = Field(default=Decimal("0.00"))
    total_expense: Decimal = Field(default=Decimal("0.00"))
    net_savings: Decimal = Field(default=Decimal("0.00"))
    savings_rate: float = Field(default=0.0)
    top_category: str | None = None
    top_category_amount: Decimal | None = None


class SpendingVelocityItem(BaseModel):
    """Cumulative and daily spending progression for a specific day in the month."""

    day: int
    date_str: str
    cumulative_spend: Decimal = Field(default=Decimal("0.00"))
    ideal_spend: Decimal = Field(default=Decimal("0.00"))
    actual_daily_spend: Decimal = Field(default=Decimal("0.00"))


class SpendingPredictionData(BaseModel):
    """Linear & velocity-based spending projection for the end of the current month."""

    current_spent: Decimal = Field(default=Decimal("0.00"))
    total_budget: Decimal = Field(default=Decimal("0.00"))
    days_passed: int = Field(default=1)
    total_days: int = Field(default=30)
    daily_burn_rate: Decimal = Field(default=Decimal("0.00"))
    projected_end_month_spend: Decimal = Field(default=Decimal("0.00"))
    projected_diff_amount: Decimal = Field(default=Decimal("0.00"))
    is_overrun_risk: bool = Field(default=False)
    risk_level: str = Field(default="safe")  # "safe", "warning", "danger"
    projected_savings_rate: float = Field(default=0.0)


class CategoryAnomalyItem(BaseModel):
    """Detected anomaly surge in category spending compared to 3-month rolling average."""

    category_id: int | None = None
    category_name: str
    category_icon: str | None = None
    category_color: str | None = None
    current_month_amount: Decimal = Field(default=Decimal("0.00"))
    avg_3m_amount: Decimal = Field(default=Decimal("0.00"))
    diff_percent: float = Field(default=0.0)
    diff_amount: Decimal = Field(default=Decimal("0.00"))
    is_spike: bool = Field(default=False)
    note: str = Field(default="")


class MonthlyTrendResponse(BaseModel):
    """Comprehensive multi-month trend analytics, velocity, anomalies and predictions."""

    months_count: int
    items: list[MonthlyTrendItem]
    average_monthly_income: Decimal
    average_monthly_expense: Decimal
    average_monthly_savings: Decimal
    average_savings_rate: float
    smart_summary: str = Field(default="")
    actionable_insights: list[str] = Field(default_factory=list)
    velocity_data: list[SpendingVelocityItem] = Field(default_factory=list)
    prediction_data: SpendingPredictionData | None = None
    anomaly_items: list[CategoryAnomalyItem] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# AI Monthly Report Schemas
# ---------------------------------------------------------------------------


class MonthlyReportRequest(BaseModel):
    """Request payload to generate or fetch AI monthly report."""

    month: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}$",
        description="Month in YYYY-MM format, e.g. '2026-08'",
    )


class MonthlyReportResponse(BaseModel):
    """Structured AI Monthly Report response."""

    month: str
    financial_health_score: int = Field(
        ..., ge=0, le=100, description="Financial Health Score from 0 to 100"
    )
    health_status: str = Field(
        ..., description="Status badge: 'Xuất sắc', 'Tốt', 'Cần chú ý', 'Báo động'"
    )
    total_income: Decimal
    total_expense: Decimal
    net_savings: Decimal
    savings_rate: float
    overview: str
    trend_analysis: str
    top_categories: list[dict[str, Any]] = Field(default_factory=list)
    adjustments: list[str] = Field(
        ..., min_length=1, description="3 actionable adjustment recommendations"
    )
    conclusion: str
    raw_markdown: str
    generated_at: datetime


# ---------------------------------------------------------------------------
# AI Budget Recommendation Schemas
# ---------------------------------------------------------------------------


class BudgetRecommendationItem(BaseModel):
    """AI recommended budget for an expense category."""

    category_id: int
    category_name: str
    category_icon: str | None = None
    category_color: str | None = None
    avg_spent: Decimal
    last_month_spent: Decimal
    recommended_amount: Decimal
    reason: str


class BudgetRecommendationResponse(BaseModel):
    """List of AI budget recommendations for next/target period."""

    target_month: int
    target_year: int
    total_recommended: Decimal
    recommendations: list[BudgetRecommendationItem]


class ApplyRecommendationItem(BaseModel):
    """Single category budget recommendation to apply."""

    category_id: int
    amount: Decimal = Field(..., gt=0)


class ApplyBudgetRecommendationsRequest(BaseModel):
    """Payload to apply selected budget recommendations into the database."""

    target_month: int = Field(..., ge=1, le=12)
    target_year: int = Field(..., ge=2000, le=2100)
    recommendations: list[ApplyRecommendationItem] = Field(..., min_length=1)


class ApplyBudgetRecommendationsResponse(BaseModel):
    """Result of applying recommendations."""

    success: bool = True
    applied_count: int
    message: str
