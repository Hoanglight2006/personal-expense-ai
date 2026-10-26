"""Core AI and Financial Trend Analytics Service.

Facade module delegating to specialized engines under app.core.ai:
- trend_analyzer: Monthly trend aggregation, velocity, predictions, anomalies.
- report_generator: Deterministic monthly financial summaries and AI narrative reports.
- budget_suggester: Smart budget recommendations and 1-click batch application.
- gemini_client: Gemini GenerativeModel initialization and configuration.
"""

from __future__ import annotations

try:
    import google.generativeai as genai
except ImportError:
    genai = None
from sqlalchemy.orm import Session

from app.core.ai.budget_suggester import (
    apply_budget_recommendations,
    generate_budget_recommendations as _generate_budget_recommendations,
)
from app.core.ai.gemini_client import (
    SYSTEM_REPORT_PROMPT,
    get_gemini_model,
)
from app.core.ai.report_generator import (
    calculate_monthly_financial_summary,
    generate_monthly_ai_report as _generate_monthly_ai_report,
)
from app.core.ai.trend_analyzer import get_monthly_trend_data
from app.schemas.ai import (
    BudgetRecommendationResponse,
    MonthlyReportResponse,
)

_get_gemini_model = get_gemini_model


def _get_current_model(system_instruction: str = SYSTEM_REPORT_PROMPT):
    """Resolve model, respecting test patches on app.core.ai_service.genai.GenerativeModel."""
    from app.config import settings

    if not genai or not settings.GEMINI_API_KEY:
        return None
    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        return genai.GenerativeModel(
            settings.GEMINI_MODEL,
            system_instruction=system_instruction,
            generation_config=genai.types.GenerationConfig(
                temperature=0.4,
                max_output_tokens=1500,
            ),
        )
    except Exception:
        return None


async def generate_monthly_ai_report(
    db: Session, user_id: int, month_str: str, focus: str = "comprehensive"
) -> MonthlyReportResponse:
    """Generate an AI monthly spending report adhering to REQUIREMENTS.md."""
    return await _generate_monthly_ai_report(
        db, user_id, month_str, focus=focus, get_model_fn=_get_current_model
    )


async def generate_budget_recommendations(
    db: Session,
    user_id: int,
    target_month: int,
    target_year: int,
    lookback_months: int = 3,
) -> BudgetRecommendationResponse:
    """Generate smart budget recommendations for active expense categories."""
    return await _generate_budget_recommendations(
        db,
        user_id,
        target_month,
        target_year,
        lookback_months=lookback_months,
        get_model_fn=_get_current_model,
    )


__all__ = [
    "SYSTEM_REPORT_PROMPT",
    "_get_gemini_model",
    "apply_budget_recommendations",
    "calculate_monthly_financial_summary",
    "generate_budget_recommendations",
    "generate_monthly_ai_report",
    "get_monthly_trend_data",
    "genai",
]
