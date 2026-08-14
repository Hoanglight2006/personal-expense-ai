"""Shared enum types used across multiple models."""

import enum


class CategoryType(str, enum.Enum):
    """Type of category / transaction: income or expense."""

    INCOME = "income"
    EXPENSE = "expense"


class GoalStatus(str, enum.Enum):
    """Status of a saving goal."""

    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ContributionSource(str, enum.Enum):
    """Source of a saving contribution."""

    INCOME_ALLOCATION = "income_allocation"
    MANUAL = "manual"


class PaymentMethod(str, enum.Enum):
    """Accepted payment methods for transactions."""

    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"


class ReportType(str, enum.Enum):
    """Type of AI-generated report."""

    MONTHLY_SUMMARY = "monthly_summary"
    BUDGET_SUGGESTION = "budget_suggestion"
    CHAT_ANSWER = "chat_answer"
