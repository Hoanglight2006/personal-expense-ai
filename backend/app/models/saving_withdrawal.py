from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

if TYPE_CHECKING:
    from app.models.saving_goal import SavingGoal
    from app.models.saving_withdrawal_allocation import SavingWithdrawalAllocation


class SavingWithdrawal(Base):
    """Auditable withdrawal from a saving goal.

    Amounts are stored as positive values. ``SavingGoal.current_amount`` is the
    effective saved amount after subtracting these withdrawals from deposits.
    """

    __tablename__ = "saving_withdrawals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    saving_goal_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("saving_goals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_saving_withdrawal_amount_positive"),
        UniqueConstraint(
            "saving_goal_id",
            "idempotency_key",
            name="uq_saving_withdrawal_goal_key",
        ),
    )

    saving_goal: Mapped["SavingGoal"] = relationship("SavingGoal", back_populates="withdrawals")
    allocations: Mapped[List["SavingWithdrawalAllocation"]] = relationship(
        "SavingWithdrawalAllocation",
        back_populates="withdrawal",
        cascade="all, delete-orphan",
    )
