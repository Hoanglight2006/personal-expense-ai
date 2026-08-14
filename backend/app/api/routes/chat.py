"""AI Chat API routes.

Provides the chatbot endpoint for the FinAI assistant, which answers
user questions about their personal finances using Gemini AI.
"""

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.ai_chat import GeminiChatService, build_financial_context
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
    """AI-generated reply."""

    reply: str


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
    """
    try:
        service = GeminiChatService()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    # Build financial context from real user data
    financial_context = build_financial_context(db, current_user.id)

    # Generate AI reply
    reply = await service.generate_reply(
        user_message=body.message,
        financial_context=financial_context,
        conversation_history=body.conversation_history,
    )

    return ChatMessageResponse(reply=reply)
