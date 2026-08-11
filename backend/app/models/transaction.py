from sqlalchemy import CheckConstraint, Column, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import CategoryType


class Transaction(Base):
    """Income or expense transaction record."""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category_id = Column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    type = Column(Enum(CategoryType), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    description = Column(String(255), nullable=True)
    transaction_date = Column(Date, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_transaction_amount_positive"),
    )

    # ---- Relationships ----
    user = relationship("User", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")

    # passive_deletes=True lets the DB handle ON DELETE SET NULL
    # on SavingContribution.transaction_id without SQLAlchemy interference.
    saving_contributions = relationship(
        "SavingContribution", back_populates="transaction", passive_deletes=True
    )
