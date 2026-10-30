"""AI Chat API routes.

Provides the chatbot endpoint for the FinAI assistant, which answers
user questions about their personal finances using Gemini AI.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.ai_chat import GeminiChatService, build_financial_context, mask_sensitive_data
from app.core.timezone import local_today
from app.models.ai_report import AIReport
from app.models.enums import ReportType
from app.models.user import User

router = APIRouter(prefix="/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ChatMessageRequest(BaseModel):
    """Incoming chat message from the user."""

    message: str = Field(..., min_length=1, max_length=1000)
    conversation_history: list[dict] = Field(default_factory=list)


class ChatMessageResponse(BaseModel):
    """AI-generated reply with optional RAG knowledge sources."""

    reply: str
    rag_sources: list[str] = Field(
        default_factory=list,
        description="Danh sách tài liệu tri thức tài chính được truy xuất (RAG)",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(
    body: ChatMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Process a user chat message and return an AI-generated reply.

    The AI receives a summarized view of the user's financial data
    (monthly totals by category, recent transactions) as context.
    All sensitive numbers (account numbers, card numbers) are masked before dispatch.
    """
    try:
        service = GeminiChatService()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    # Mask sensitive credentials or transaction IDs in user input
    safe_message = mask_sensitive_data(body.message)

    # Build financial context from real user data (aggregated & masked)
    financial_context = build_financial_context(db, current_user.id)

    # Generate AI reply with RAG financial knowledge sources
    reply, rag_sources = await service.generate_reply_with_sources(
        user_message=safe_message,
        financial_context=financial_context,
        conversation_history=body.conversation_history,
    )

    # Log interaction for audit trail (KT3 & Ethics rubric)
    try:
        today = local_today()
        log_entry = AIReport(
            user_id=current_user.id,
            report_type=ReportType.CHAT_ANSWER,
            prompt_sent=safe_message,
            ai_response=reply,
            period_month=today.month,
            period_year=today.year,
        )
        db.add(log_entry)
        db.commit()
    except Exception:
        db.rollback()

    return ChatMessageResponse(reply=reply, rag_sources=rag_sources)
