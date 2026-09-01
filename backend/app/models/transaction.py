from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import CategoryType, PaymentMethod

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.saving_contribution import SavingContribution
    from app.models.user import User


class Transaction(Base):
    """Income or expense transaction record."""

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[CategoryType] = mapped_column(Enum(CategoryType), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod),
        nullable=False,
        default=PaymentMethod.CASH,
        server_default=PaymentMethod.CASH.value,
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["category_id", "user_id"],
            ["categories.id", "categories.user_id"],
            name="fk_transaction_category_owner",
            ondelete="CASCADE",
        ),
        CheckConstraint("amount > 0", name="ck_transaction_amount_positive"),
    )

    # ---- Relationships ----
    user: Mapped["User"] = relationship("User", back_populates="transactions")
    category: Mapped["Category"] = relationship(
        "Category",
        primaryjoin="and_(Transaction.category_id == Category.id, "
        "Transaction.user_id == Category.user_id)",
        foreign_keys=[category_id],
        back_populates="transactions",
    )

    # passive_deletes=True lets the DB handle ON DELETE SET NULL
    # on SavingContribution.transaction_id without SQLAlchemy interference.
    saving_contributions: Mapped[List["SavingContribution"]] = relationship(
        "SavingContribution", back_populates="transaction", passive_deletes=True
    )
