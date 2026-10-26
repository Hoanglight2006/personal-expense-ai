"""Gemini client initialization and configuration helper.
"""

from __future__ import annotations

try:
    import google.generativeai as genai
except ImportError:
    genai = None
from app.config import settings
from app.core.prompts import get_prompt

SYSTEM_REPORT_PROMPT = get_prompt("monthly_report", "system_instruction")


def get_gemini_model(system_instruction: str = SYSTEM_REPORT_PROMPT):
    """Initialize Gemini GenerativeModel if configured."""
    if not genai or not settings.GEMINI_API_KEY:
        return None
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(
        settings.GEMINI_MODEL,
        system_instruction=system_instruction,
        generation_config=genai.types.GenerationConfig(
            temperature=0.4,
            max_output_tokens=1500,
        ),
    )


_get_gemini_model = get_gemini_model
