"""Pydantic schemas for Transaction CRUD, filtering and import."""

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import CategoryType, PaymentMethod

MAX_TRANSACTION_NOTE_LENGTH = 255
MAX_AMOUNT = Decimal("9999999999999.99")  # Numeric(15, 2)


def _clean_description(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed if trimmed else None


def _validate_amount(value) -> Decimal:
    """Validate and normalise an amount to Decimal(15,2), > 0."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Số tiền không hợp lệ.")
    if amount.is_nan() or amount.is_infinite():
        raise ValueError("Số tiền không hợp lệ.")
    if amount <= 0:
        raise ValueError("Số tiền phải lớn hơn 0.")
    if amount % Decimal("1") != Decimal("0"):
        raise ValueError("Số tiền phải là số nguyên (VNĐ không hỗ trợ số lẻ).")
    # Quantize to 2 decimal places
    amount = amount.quantize(Decimal("0.01"))
    if amount > MAX_AMOUNT:
        raise ValueError("Số tiền vượt quá giới hạn cho phép.")
    return amount


class TransactionCreate(BaseModel):
    """Schema for creating a new transaction."""

    amount: Decimal
    type: CategoryType
    category_id: int
    transaction_date: date
    description: str | None = Field(
        default=None, max_length=MAX_TRANSACTION_NOTE_LENGTH
    )
    payment_method: PaymentMethod = PaymentMethod.CASH
    saving_goal_id: int | None = None
    saving_goal_amount: Decimal | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, value) -> Decimal:
        return _validate_amount(value)

    @field_validator("saving_goal_amount", mode="before")
    @classmethod
    def validate_saving_goal_amount(cls, value) -> Decimal | None:
        if value is None or value == "":
            return None
        amt = _validate_amount(value)
        if amt % Decimal("1") != Decimal("0"):
            raise ValueError("Số tiền trích vào mục tiêu phải là số nguyên (VNĐ không hỗ trợ số lẻ).")
        return amt

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, value) -> str | None:
        return _clean_description(value)

    @model_validator(mode="after")
    def validate_saving_goal_allocation(self):
        if self.saving_goal_id is not None:
            if self.type != CategoryType.INCOME:
                raise ValueError("Chỉ có thể trích tiền vào mục tiêu tiết kiệm đối với giao dịch thu nhập.")
            if self.saving_goal_amount is None or self.saving_goal_amount <= 0:
                raise ValueError("Vui lòng nhập số tiền hợp lệ cần trích vào mục tiêu tiết kiệm.")
            if self.saving_goal_amount > self.amount:
                raise ValueError("Số tiền trích vào mục tiêu tiết kiệm không được vượt quá số tiền thu nhập.")
        return self


class TransactionUpdate(BaseModel):
    """Schema for partial update of a transaction."""

    amount: Decimal | None = None
    type: CategoryType | None = None
    category_id: int | None = None
    transaction_date: date | None = None
    description: str | None = Field(
        default=None, max_length=MAX_TRANSACTION_NOTE_LENGTH
    )
    payment_method: PaymentMethod | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "amount",
        "type",
        "category_id",
        "transaction_date",
        "payment_method",
        mode="before",
    )
    @classmethod
    def reject_null_required_fields(cls, value):
        if value is None:
            raise ValueError("Trường cập nhật này không được để trống.")
        return value

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, value) -> Decimal:
        return _validate_amount(value)

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, value) -> str | None:
        return _clean_description(value)

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("Cần cung cấp ít nhất một trường để cập nhật.")
        return self


class CategoryInfo(BaseModel):
    """Embedded category information inside a transaction response."""

    id: int
    name: str
    icon: str
    color: str
    is_active: bool
    is_deleted: bool = False
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TransactionResponse(BaseModel):
    """Schema for a single transaction returned to the client."""

    id: int
    amount: Decimal
    type: CategoryType
    category_id: int
    category: CategoryInfo | None = None
    transaction_date: date
    description: str | None
    payment_method: PaymentMethod
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    saving_goal_id: int | None = None
    saving_goal_name: str | None = None
    saving_goal_amount: Decimal | None = None
    movement_type: str | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", "updated_at", "deleted_at", mode="after")
    @classmethod
    def ensure_utc(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class TransactionListResponse(BaseModel):
    """Paginated list of transactions."""

    items: list[TransactionResponse]
    total_count: int
    page: int
    page_size: int


class TransactionRestoreResponse(BaseModel):
    """Response for restore action, includes category warning if applicable."""

    transaction: TransactionResponse
    category_warning: str | None = None


# ---- Sorting & Filtering ----

TransactionSort = Literal["date_desc", "date_asc", "amount_desc", "amount_asc"]


class TransactionSummaryResponse(BaseModel):
    """Financial balance and flow summary response."""

    total_balance: Decimal
    available_balance: Decimal
    saving_balance: Decimal
    all_time_income: Decimal
    all_time_expense: Decimal
    month_income: Decimal
    month_expense: Decimal
    month_net: Decimal
