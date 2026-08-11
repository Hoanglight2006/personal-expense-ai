from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, SmallInteger, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base
from app.models.enums import ReportType


class AIReport(Base):
    """Log of AI interactions – stores masked prompt and AI response."""

    __tablename__ = "ai_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    report_type = Column(Enum(ReportType), nullable=False)
    prompt_sent = Column(Text, nullable=False)
    ai_response = Column(Text, nullable=False)
    period_month = Column(SmallInteger, nullable=True)
    period_year = Column(SmallInteger, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # ---- Relationships ----
    user = relationship("User", back_populates="ai_reports")
