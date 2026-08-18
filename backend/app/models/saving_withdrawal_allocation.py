from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class SavingWithdrawalAllocation(Base):
    """Maps a withdrawal amount to the deposits it consumed."""

    __tablename__ = "saving_withdrawal_allocations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    withdrawal_id = Column(
        Integer,
        ForeignKey("saving_withdrawals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contribution_id = Column(
        Integer,
        ForeignKey("saving_contributions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount = Column(Numeric(15, 2), nullable=False)

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

    withdrawal = relationship("SavingWithdrawal", back_populates="allocations")
    contribution = relationship("SavingContribution", back_populates="withdrawal_allocations")
