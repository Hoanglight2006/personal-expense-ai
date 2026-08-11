from sqlalchemy import CheckConstraint, Column, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import GoalStatus


class SavingGoal(Base):
    """Saving goal with denormalized current_amount = SUM(contributions)."""

    __tablename__ = "saving_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(100), nullable=False)
    target_amount = Column(Numeric(15, 2), nullable=False)
    current_amount = Column(Numeric(15, 2), nullable=False, server_default="0")
    deadline = Column(Date, nullable=True)
    status = Column(
        Enum(GoalStatus), nullable=False, server_default=GoalStatus.ACTIVE.value
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("target_amount > 0", name="ck_saving_goal_target_positive"),
        CheckConstraint("current_amount >= 0", name="ck_saving_goal_current_non_negative"),
    )

    # ---- Relationships ----
    user = relationship("User", back_populates="saving_goals")
    contributions = relationship(
        "SavingContribution",
        back_populates="saving_goal",
        cascade="all, delete-orphan",
    )
