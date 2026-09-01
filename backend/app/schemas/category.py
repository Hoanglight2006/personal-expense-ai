from datetime import date, datetime
from decimal import Decimal
from typing import Literal
import re
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SUPPORTED_CATEGORY_ICONS = frozenset(
    {
        "food",
        "transport",
        "shopping",
        "home",
        "health",
        "education",
        "entertainment",
        "salary",
        "bonus",
        "gift",
        "investment",
        "sports",
        "pets",
        "travel",
        "other",
    }
)
MAX_CATEGORY_NAME_LENGTH = 50
MAX_CATEGORY_NAME_KEY_LENGTH = 150
HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def normalize_category_name(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Tên danh mục không hợp lệ.")
    normalized = unicodedata.normalize("NFKC", value).strip()
    if not normalized:
        raise ValueError("Tên danh mục không được để trống.")
    return normalized


def category_name_key(value: str) -> str:
    key = normalize_category_name(value).casefold()
    if len(key) > MAX_CATEGORY_NAME_KEY_LENGTH:
        raise ValueError("Tên danh mục quá dài sau khi chuẩn hóa.")
    return key


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=MAX_CATEGORY_NAME_LENGTH)
    type: Literal["expense", "income"] = "expense"
    icon: str = "other"
    color: str = "#D69A23"
    model_config = ConfigDict(extra="forbid")

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = normalize_category_name(value)
        category_name_key(normalized)
        return normalized

    @field_validator("icon")
    @classmethod
    def validate_icon(cls, value: str) -> str:
        if value not in SUPPORTED_CATEGORY_ICONS:
            raise ValueError("Biểu tượng danh mục không được hỗ trợ.")
        return value

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        if not HEX_COLOR_PATTERN.fullmatch(value):
            raise ValueError("Màu phải là mã HEX dạng #RRGGBB.")
        return value.upper()


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_CATEGORY_NAME_LENGTH,
    )
    type: Literal["expense", "income"] | None = None
    icon: str | None = None
    color: str | None = None
    model_config = ConfigDict(extra="forbid")

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_category_name(value)
        category_name_key(normalized)
        return normalized

    @field_validator("icon")
    @classmethod
    def validate_icon(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in SUPPORTED_CATEGORY_ICONS:
            raise ValueError("Biểu tượng danh mục không được hỗ trợ.")
        return value

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not HEX_COLOR_PATTERN.fullmatch(value):
            raise ValueError("Màu phải là mã HEX dạng #RRGGBB.")
        return value.upper()

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("Cần cung cấp ít nhất một trường để cập nhật.")
        return self


class CategoryResponse(CategoryBase):
    id: int
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime
    has_transactions: bool = False
    total_amount: Decimal = Decimal("0.00")
    income_amount: Decimal = Decimal("0.00")
    expense_amount: Decimal = Decimal("0.00")
    transaction_count: int = 0
    expense_percentage: Decimal | None = None

    model_config = ConfigDict(from_attributes=True)


class CategoryListResponse(BaseModel):
    start_date: date
    end_date: date
    items: list[CategoryResponse]


CategoryStatusFilter = Literal["active", "hidden", "all"]
CategorySort = Literal["amount_desc", "amount_asc", "name_asc"]
