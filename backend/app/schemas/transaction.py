"""Pydantic schemas for Transaction CRUD, filtering and import."""

from datetime import date, datetime
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

    model_config = ConfigDict(extra="forbid")

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, value) -> Decimal:
        return _validate_amount(value)

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, value) -> str | None:
        return _clean_description(value)


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

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, value) -> Decimal | None:
        if value is None:
            return None
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

    model_config = ConfigDict(from_attributes=True)


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


class BulkTransactionRow(BaseModel):
    """A single row in a bulk import request."""

    amount: Decimal
    type: CategoryType
    category_id: int
    transaction_date: date
    description: str | None = Field(
        default=None, max_length=MAX_TRANSACTION_NOTE_LENGTH
    )
    payment_method: PaymentMethod = PaymentMethod.BANK_TRANSFER

    model_config = ConfigDict(extra="forbid")

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, value) -> Decimal:
        return _validate_amount(value)

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, value) -> str | None:
        return _clean_description(value)


class BulkImportRequest(BaseModel):
    """Request body for confirmed bulk import."""

    idempotency_key: str = Field(..., min_length=1, max_length=64)
    rows: list[BulkTransactionRow] = Field(..., min_length=1, max_length=1000)

    model_config = ConfigDict(extra="forbid")


class RowResult(BaseModel):
    """Result for a single row in a bulk import."""

    index: int
    status: Literal["success", "error", "skipped"]
    error: str | None = None
    transaction_id: int | None = None


class BulkImportResponse(BaseModel):
    """Response for a bulk import operation."""

    total: int
    success_count: int
    error_count: int
    skipped_count: int
    results: list[RowResult]


class TransactionSummaryResponse(BaseModel):
    """Financial balance and flow summary response."""

    available_balance: Decimal
    all_time_income: Decimal
    all_time_expense: Decimal
    month_income: Decimal
    month_expense: Decimal
    month_net: Decimal

