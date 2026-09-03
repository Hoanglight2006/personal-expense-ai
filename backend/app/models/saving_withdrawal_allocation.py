from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.saving_contribution import SavingContribution
    from app.models.saving_withdrawal import SavingWithdrawal


class SavingWithdrawalAllocation(Base):
    """Maps a withdrawal amount to the deposits it consumed."""

    __tablename__ = "saving_withdrawal_allocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    withdrawal_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("saving_withdrawals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contribution_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("saving_contributions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="ck_saving_withdrawal_allocation_amount_positive",
        ),
        UniqueConstraint(
            "withdrawal_id",
            "contribution_id",
            name="uq_withdrawal_contribution",
        ),
    )

    withdrawal: Mapped["SavingWithdrawal"] = relationship("SavingWithdrawal", back_populates="allocations")
    contribution: Mapped["SavingContribution"] = relationship("SavingContribution", back_populates="withdrawal_allocations")
