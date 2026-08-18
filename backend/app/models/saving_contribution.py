from sqlalchemy import CheckConstraint, Column, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import ContributionSource


class SavingContribution(Base):
    """History record of a contribution to a saving goal.

    Two sources:
    - income_allocation: linked to an income Transaction via transaction_id.
    - manual: standalone deposit, transaction_id is NULL.

    FK transaction_id uses ON DELETE SET NULL so that deleting a single
    transaction preserves the contribution history.
    """

    __tablename__ = "saving_contributions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    saving_goal_id = Column(
        Integer,
        ForeignKey("saving_goals.id", ondelete="CASCADE"),
        nullable=False,
    )
    transaction_id = Column(
        Integer,
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    amount = Column(Numeric(15, 2), nullable=False)
    source = Column(Enum(ContributionSource), nullable=False)
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_contribution_amount_positive"),
    )

    # ---- Relationships ----
    saving_goal = relationship("SavingGoal", back_populates="contributions")
    transaction = relationship("Transaction", back_populates="saving_contributions")
    withdrawal_allocations = relationship(
        "SavingWithdrawalAllocation",
        back_populates="contribution",
        cascade="all, delete-orphan",
    )
