from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import CategoryType, PaymentMethod


class Transaction(Base):
    """Income or expense transaction record."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category_id = Column(Integer, nullable=False)
    type = Column(Enum(CategoryType), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    description = Column(String(255), nullable=True)
    transaction_date = Column(Date, nullable=False)
    payment_method = Column(
        Enum(PaymentMethod),
        nullable=False,
        default=PaymentMethod.CASH,
        server_default=PaymentMethod.CASH.value,
    )
    is_deleted = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at = Column(DateTime, nullable=True)

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
    user = relationship("User", back_populates="transactions")
    category = relationship(
        "Category",
        primaryjoin="and_(Transaction.category_id == Category.id, "
        "Transaction.user_id == Category.user_id)",
        foreign_keys=[category_id],
        back_populates="transactions",
    )

    # passive_deletes=True lets the DB handle ON DELETE SET NULL
    # on SavingContribution.transaction_id without SQLAlchemy interference.
    saving_contributions = relationship(
        "SavingContribution", back_populates="transaction", passive_deletes=True
    )
