from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ContributionSource, GoalStatus


# ==========================================
# SAVING CONTRIBUTION SCHEMAS
# ==========================================

class SavingContributionBase(BaseModel):
    """Base fields for a saving contribution."""

    amount: Decimal = Field(
        ...,
        gt=Decimal("0"),
        max_digits=15,
        decimal_places=2,
        description="Số tiền nạp vào mục tiêu (VNĐ)",
    )
    note: str | None = Field(
        None,
        max_length=255,
        description="Ghi chú cho lần nạp tiền",
    )


class SavingContributionCreate(SavingContributionBase):
    """Public payload for a manual contribution to a saving goal.

    Income allocations are created only by the transaction service so clients
    cannot forge a contribution backed by an arbitrary transaction.
    """

    model_config = ConfigDict(extra="forbid")


class SavingContributionResponse(BaseModel):
    """Response model for a saving contribution record."""

    id: int
    saving_goal_id: int
    transaction_id: int | None = None
    amount: Decimal
    source: ContributionSource
    note: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# SAVING GOAL SCHEMAS
# ==========================================

class SavingGoalBase(BaseModel):
    """Base fields for a saving goal."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Tên mục tiêu tiết kiệm",
    )
    target_amount: Decimal = Field(
        ...,
        gt=Decimal("0"),
        max_digits=15,
        decimal_places=2,
        description="Số tiền mục tiêu cần tích lũy (VNĐ)",
    )
    deadline: date | None = Field(
        None,
        description="Hạn chót hoàn thành mục tiêu (YYYY-MM-DD)",
    )


class SavingGoalCreate(SavingGoalBase):
    """Payload for creating a new saving goal."""

    initial_deposit: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        max_digits=15,
        decimal_places=2,
        description="Số tiền nạp ban đầu vào mục tiêu (nếu có)",
    )

    @field_validator("deadline")
    @classmethod
    def validate_deadline_not_past(cls, v: date | None) -> date | None:
        if v is not None and v < date.today():
            raise ValueError("Hạn chót không được ở trong quá khứ.")
        return v


class SavingGoalUpdate(BaseModel):
    """Payload for updating an existing saving goal."""

    name: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Tên mục tiêu mới",
    )
    target_amount: Decimal | None = Field(
        None,
        gt=Decimal("0"),
        max_digits=15,
        decimal_places=2,
        description="Số tiền mục tiêu mới (VNĐ)",
    )
    deadline: date | None = Field(
        None,
        description="Hạn chót mới (YYYY-MM-DD)",
    )
    status: GoalStatus | None = Field(
        None,
        description="Trạng thái mục tiêu (active, completed, cancelled)",
    )


class SavingGoalResponse(BaseModel):
    """Detailed response model for a saving goal."""

    id: int
    user_id: int
    name: str
    target_amount: Decimal
    current_amount: Decimal
    deadline: date | None = None
    status: GoalStatus
    progress_percentage: float = 0.0
    remaining_amount: Decimal = Decimal("0.00")
    days_remaining: int | None = None
    contributions: list[SavingContributionResponse] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SavingGoalListResponse(BaseModel):
    """Aggregated list response with summary metrics for saving goals."""

    total_target_amount: Decimal = Decimal("0.00")
    total_current_amount: Decimal = Decimal("0.00")
    total_goals_count: int = 0
    active_goals_count: int = 0
    completed_goals_count: int = 0
    items: list[SavingGoalResponse] = []
