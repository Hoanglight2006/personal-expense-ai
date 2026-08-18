from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SavingWithdrawal(Base):
    """Auditable withdrawal from a saving goal.

    Amounts are stored as positive values. ``SavingGoal.current_amount`` is the
    effective saved amount after subtracting these withdrawals from deposits.
    """

    __tablename__ = "saving_withdrawals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    saving_goal_id = Column(
        Integer,
        ForeignKey("saving_goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount = Column(Numeric(15, 2), nullable=False)
    idempotency_key = Column(String(64), nullable=False)
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_saving_withdrawal_amount_positive"),
        UniqueConstraint(
            "saving_goal_id",
            "idempotency_key",
            name="uq_saving_withdrawal_goal_key",
        ),
    )

    saving_goal = relationship("SavingGoal", back_populates="withdrawals")
    allocations = relationship(
        "SavingWithdrawalAllocation",
        back_populates="withdrawal",
        cascade="all, delete-orphan",
    )
