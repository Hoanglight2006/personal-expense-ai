from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, Enum, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import UserRole

if TYPE_CHECKING:
    from app.models.ai_report import AIReport
    from app.models.budget import Budget
    from app.models.category import Category
    from app.models.saving_goal import SavingGoal
    from app.models.transaction import Transaction


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=UserRole.USER,
        server_default=UserRole.USER.value,
    )
    is_locked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    verification_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    verification_code_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reset_password_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    reset_password_code_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    has_seen_initial_balance_guide: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("idx_users_role_status", "role", "is_locked"),
    )

    # ---- Relationships (1:N, cascade delete all children) ----
    categories: Mapped[List["Category"]] = relationship(
        "Category", back_populates="user", cascade="all, delete-orphan"
    )
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    budgets: Mapped[List["Budget"]] = relationship(
        "Budget", back_populates="user", cascade="all, delete-orphan"
    )
    saving_goals: Mapped[List["SavingGoal"]] = relationship(
        "SavingGoal", back_populates="user", cascade="all, delete-orphan"
    )
    ai_reports: Mapped[List["AIReport"]] = relationship(
        "AIReport", back_populates="user", cascade="all, delete-orphan"
    )
