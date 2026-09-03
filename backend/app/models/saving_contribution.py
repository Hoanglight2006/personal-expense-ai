from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import ContributionSource

if TYPE_CHECKING:
    from app.models.saving_goal import SavingGoal
    from app.models.saving_withdrawal_allocation import SavingWithdrawalAllocation
    from app.models.transaction import Transaction


class SavingContribution(Base):
    """History record of a contribution to a saving goal.

    Two sources:
    - income_allocation: linked to an income Transaction via transaction_id.
    - manual: standalone deposit, transaction_id is NULL.

    FK transaction_id uses ON DELETE SET NULL so that deleting a single
    transaction preserves the contribution history.
    """

    __tablename__ = "saving_contributions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    saving_goal_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("saving_goals.id", ondelete="CASCADE"),
        nullable=False,
    )
    transaction_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("transactions.id", ondelete="SET NULL"),
        nullable=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    source: Mapped[ContributionSource] = mapped_column(Enum(ContributionSource), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_contribution_amount_positive"),
    )

    # ---- Relationships ----
    saving_goal: Mapped["SavingGoal"] = relationship("SavingGoal", back_populates="contributions")
    transaction: Mapped[Optional["Transaction"]] = relationship("Transaction", back_populates="saving_contributions")
    withdrawal_allocations: Mapped[List["SavingWithdrawalAllocation"]] = relationship(
        "SavingWithdrawalAllocation",
        back_populates="contribution",
        cascade="all, delete-orphan",
    )
