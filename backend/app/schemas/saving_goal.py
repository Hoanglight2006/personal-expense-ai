from datetime import date, datetime, timezone
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.timezone import local_today
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

    @field_validator("amount")
    @classmethod
    def validate_amount_integer(cls, v: Decimal) -> Decimal:
        if v % Decimal("1") != Decimal("0"):
            raise ValueError("Số tiền nạp phải là số nguyên (VNĐ không hỗ trợ số lẻ).")
        return v


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

    @field_validator("created_at", mode="after")
    @classmethod
    def ensure_utc(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class SavingWithdrawalCreate(BaseModel):
    """Public payload for withdrawing saved money from a goal."""

    amount: Decimal = Field(
        ...,
        gt=Decimal("0"),
        max_digits=15,
        decimal_places=2,
        description="Số tiền rút khỏi mục tiêu (VNĐ)",
    )
    idempotency_key: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Khóa retry duy nhất cho một lần rút tiền",
    )
    note: str | None = Field(
        None,
        max_length=255,
        description="Ghi chú cho lần rút tiền",
    )

    @field_validator("amount")
    @classmethod
    def validate_amount_integer(cls, v: Decimal) -> Decimal:
        if v % Decimal("1") != Decimal("0"):
            raise ValueError("Số tiền rút phải là số nguyên (VNĐ không hỗ trợ số lẻ).")
        return v

    model_config = ConfigDict(extra="forbid")


class SavingWithdrawalResponse(BaseModel):
    """Response model for a saving withdrawal record."""

    id: int
    saving_goal_id: int
    amount: Decimal
    note: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", mode="after")
    @classmethod
    def ensure_utc(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


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

    @field_validator("target_amount")
    @classmethod
    def validate_target_integer(cls, v: Decimal) -> Decimal:
        if v % Decimal("1") != Decimal("0"):
            raise ValueError("Số tiền mục tiêu phải là số nguyên (VNĐ không hỗ trợ số lẻ).")
        return v


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
        if v is not None and v < local_today():
            raise ValueError("Hạn chót không được ở trong quá khứ.")
        return v

    @field_validator("initial_deposit")
    @classmethod
    def validate_initial_deposit_integer(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v % Decimal("1") != Decimal("0"):
            raise ValueError("Số tiền nạp ban đầu phải là số nguyên (VNĐ không hỗ trợ số lẻ).")
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

    @field_validator("target_amount")
    @classmethod
    def validate_target_integer(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v % Decimal("1") != Decimal("0"):
            raise ValueError("Số tiền mục tiêu phải là số nguyên (VNĐ không hỗ trợ số lẻ).")
        return v


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
    contributions: list[SavingContributionResponse] = Field(default_factory=list)
    withdrawals: list[SavingWithdrawalResponse] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", mode="after")
    @classmethod
    def ensure_utc(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class SavingGoalListResponse(BaseModel):
    """Aggregated list response with summary metrics for saving goals."""

    total_target_amount: Decimal = Decimal("0.00")
    total_current_amount: Decimal = Decimal("0.00")
    total_goals_count: int = 0
    active_goals_count: int = 0
    completed_goals_count: int = 0
    items: list[SavingGoalResponse] = Field(default_factory=list)
