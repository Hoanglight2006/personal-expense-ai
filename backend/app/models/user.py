from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # ---- Relationships (1:N, cascade delete all children) ----
    categories = relationship(
        "Category", back_populates="user", cascade="all, delete-orphan"
    )
    transactions = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    budgets = relationship(
        "Budget", back_populates="user", cascade="all, delete-orphan"
    )
    saving_goals = relationship(
        "SavingGoal", back_populates="user", cascade="all, delete-orphan"
    )
    ai_reports = relationship(
        "AIReport", back_populates="user", cascade="all, delete-orphan"
    )
