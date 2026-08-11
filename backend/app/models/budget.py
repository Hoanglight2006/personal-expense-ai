from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, Numeric, SmallInteger, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Budget(Base):
    """Monthly budget limit per category."""

    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category_id = Column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    amount = Column(Numeric(15, 2), nullable=False)
    month = Column(SmallInteger, nullable=False)
    year = Column(SmallInteger, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint(
            "user_id", "category_id", "month", "year",
            name="uq_budget_user_category_period",
        ),
        CheckConstraint("amount > 0", name="ck_budget_amount_positive"),
        CheckConstraint("month >= 1 AND month <= 12", name="ck_budget_month_range"),
    )

    # ---- Relationships ----
    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")
