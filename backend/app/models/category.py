from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.models.budget import Budget
    from app.models.transaction import Transaction
    from app.models.user import User


class Category(Base):
    """Income / expense category, may be a system default or user-created."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(150), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False, default="expense", server_default="expense")
    icon: Mapped[str] = mapped_column(String(30), nullable=False, default="other", server_default="other")
    color: Mapped[str] = mapped_column(String(7), nullable=False, default="#D69A23", server_default="#D69A23")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "name_normalized",
            name="uq_category_user_normalized_name",
        ),
        UniqueConstraint("id", "user_id", name="uq_category_id_user"),
    )

    # ---- Relationships ----
    user: Mapped["User"] = relationship("User", back_populates="categories")
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        primaryjoin="and_(Category.id == Transaction.category_id, "
        "Category.user_id == Transaction.user_id)",
        foreign_keys="Transaction.category_id",
        back_populates="category",
        cascade="all, delete-orphan",
    )
    budgets: Mapped[List["Budget"]] = relationship(
        "Budget",
        primaryjoin="and_(Category.id == Budget.category_id, "
        "Category.user_id == Budget.user_id)",
        foreign_keys="Budget.category_id",
        back_populates="category",
        cascade="all, delete-orphan",
    )
