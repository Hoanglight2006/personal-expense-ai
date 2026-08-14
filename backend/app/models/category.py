from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Category(Base):
    """Income / expense category, may be a system default or user-created."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name = Column(String(50), nullable=False)
    name_normalized = Column(String(150), nullable=False)
    type = Column(String(10), nullable=False, default="expense", server_default="expense")
    icon = Column(String(30), nullable=False, default="other", server_default="other")
    color = Column(String(7), nullable=False, default="#D69A23", server_default="#D69A23")
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "name_normalized",
            name="uq_category_user_normalized_name",
        ),
        UniqueConstraint("id", "user_id", name="uq_category_id_user"),
    )

    # ---- Relationships ----
    user = relationship("User", back_populates="categories")
    transactions = relationship(
        "Transaction",
        primaryjoin="and_(Category.id == Transaction.category_id, "
        "Category.user_id == Transaction.user_id)",
        foreign_keys="Transaction.category_id",
        back_populates="category",
        cascade="all, delete-orphan",
    )
    budgets = relationship(
        "Budget",
        primaryjoin="and_(Category.id == Budget.category_id, "
        "Category.user_id == Budget.user_id)",
        foreign_keys="Budget.category_id",
        back_populates="category",
        cascade="all, delete-orphan",
    )
