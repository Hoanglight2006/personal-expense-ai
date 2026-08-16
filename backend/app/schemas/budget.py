from datetime import datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class CategorySimpleInfo(BaseModel):
    """Minimal category information embedded in budget responses."""

    id: int
    name: str
    icon: str
    color: str
    type: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class BudgetBase(BaseModel):
    """Shared fields for budget creation."""

    category_id: int = Field(..., description="ID danh mục chi tiêu")
    amount: Decimal = Field(
        ...,
        gt=Decimal("0"),
        max_digits=15,
        decimal_places=2,
        description="Hạn mức ngân sách (VNĐ)",
    )
    month: int = Field(..., ge=1, le=12, description="Tháng áp dụng (1-12)")
    year: int = Field(..., ge=2000, le=2100, description="Năm áp dụng (2000-2100)")


class BudgetCreate(BudgetBase):
    """Payload for creating a monthly category budget."""

    pass


class BudgetUpdate(BaseModel):
    """Payload for updating budget amount."""

    amount: Decimal = Field(
        ...,
        gt=Decimal("0"),
        max_digits=15,
        decimal_places=2,
        description="Hạn mức ngân sách mới (VNĐ)",
    )


class BudgetResponse(BaseModel):
    """Detailed budget response including spending calculations."""

    id: int
    user_id: int
    category_id: int
    category: CategorySimpleInfo | None = None
    amount: Decimal
    month: int
    year: int
    spent_amount: Decimal = Decimal("0.00")
    remaining_amount: Decimal = Decimal("0.00")
    percentage_used: float = 0.0
    status: Literal["normal", "warning", "exceeded"] = "normal"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BudgetListResponse(BaseModel):
    """Summary of monthly budgets and overall totals."""

    month: int
    year: int
    total_budget: Decimal = Decimal("0.00")
    total_spent: Decimal = Decimal("0.00")
    total_remaining: Decimal = Decimal("0.00")
    items: list[BudgetResponse] = []


class BudgetAlertItem(BaseModel):
    """Alert item for categories that reached warning or exceeded threshold."""

    id: int
    category_id: int
    category_name: str
    category_icon: str
    category_color: str
    amount: Decimal
    spent_amount: Decimal
    percentage_used: float
    status: Literal["warning", "exceeded"]

    model_config = ConfigDict(from_attributes=True)


class BudgetAlertResponse(BaseModel):
    """Response containing list of triggered budget alerts."""

    count: int = 0
    items: list[BudgetAlertItem] = []
