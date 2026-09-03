from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, Numeric, SmallInteger, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.user import User


class Budget(Base):
    """Monthly budget limit per category."""

    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        ForeignKeyConstraint(
            ["category_id", "user_id"],
            ["categories.id", "categories.user_id"],
            name="fk_budget_category_owner",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "user_id", "category_id", "month", "year",
            name="uq_budget_user_category_period",
        ),
        CheckConstraint("amount > 0", name="ck_budget_amount_positive"),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_budget_month_range"),
    )

    # ---- Relationships ----
    user: Mapped["User"] = relationship("User", back_populates="budgets")
    category: Mapped["Category"] = relationship(
        "Category",
        primaryjoin="and_(Budget.category_id == Category.id, "
        "Budget.user_id == Category.user_id)",
        foreign_keys="Budget.category_id",
        back_populates="budgets",
    )
