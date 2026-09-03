from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import GoalStatus

if TYPE_CHECKING:
    from app.models.saving_contribution import SavingContribution
    from app.models.saving_withdrawal import SavingWithdrawal
    from app.models.user import User


class SavingGoal(Base):
    """Saving goal with a denormalized effective saved amount."""

    __tablename__ = "saving_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    target_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    current_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"), server_default="0")
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[GoalStatus] = mapped_column(
        Enum(GoalStatus), nullable=False, default=GoalStatus.ACTIVE, server_default=GoalStatus.ACTIVE.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("target_amount > 0", name="ck_saving_goal_target_positive"),
        CheckConstraint("current_amount >= 0", name="ck_saving_goal_current_non_negative"),
    )

    # ---- Relationships ----
    user: Mapped["User"] = relationship("User", back_populates="saving_goals")
    contributions: Mapped[List["SavingContribution"]] = relationship(
        "SavingContribution",
        back_populates="saving_goal",
        cascade="all, delete-orphan",
    )
    withdrawals: Mapped[List["SavingWithdrawal"]] = relationship(
        "SavingWithdrawal",
        back_populates="saving_goal",
        cascade="all, delete-orphan",
    )
