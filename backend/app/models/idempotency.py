from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class ImportIdempotencyKey(Base):
    """Tracks processed bulk import idempotency keys per user to prevent duplicate submissions."""

    __tablename__ = "import_idempotency_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    idempotency_key = Column(String(128), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_user_idempotency_key"),
    )
