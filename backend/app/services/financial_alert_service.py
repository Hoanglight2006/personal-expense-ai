"""Financial alert service for monitoring budget thresholds and sending email notifications."""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session

from app.core.timezone import local_today
from app.models.user import User
from app.services.budget_service import BudgetService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

# Non-blocking thread pool for dispatching outbound emails
_email_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="financial-alert-email")

# In-memory cooldown cache: (user_id, category_id, status) -> timestamp
# Prevents spamming duplicate alert emails when creating multiple transactions in an already exceeded budget
_ALERT_COOLDOWN_SECONDS = 7200  # 2 hours cooldown per category & alert status
_ALERT_COOLDOWN_CACHE: dict[tuple[int, int, str], float] = {}


def _dispatch_alert_email(
    to_email: str,
    category_name: str,
    budget_amount: float,
    spent_amount: float,
    percentage_used: float,
    status: str,
) -> None:
    """Worker function executed inside thread pool to prevent blocking HTTP requests."""
    try:
        EmailService.send_financial_alert(
            to_email=to_email,
            category_name=category_name,
            budget_amount=budget_amount,
            spent_amount=spent_amount,
            percentage_used=percentage_used,
            status=status,
        )
    except Exception as e:
        logger.error("Lỗi gửi email cảnh báo ngân sách nền tới %s: %s", to_email, e)


class FinancialAlertService:
    """Evaluates financial status and delivers email alerts to verified users asynchronously."""

    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    def check_and_send_budget_alerts(
        self,
        category_id: int | None = None,
        month: int | None = None,
        year: int | None = None,
    ) -> list[dict]:
        """Check budget alerts for month/year and dispatch emails non-blockingly if user is verified."""
        if not getattr(self.user, "is_verified", False):
            logger.info("Người dùng %s chưa xác minh email -> Bỏ qua gửi cảnh báo qua email.", self.user.email)
            return []

        today = local_today()
        target_month = month or today.month
        target_year = year or today.year

        budget_service = BudgetService(self.db, self.user)
        alerts_data = budget_service.get_budget_alerts(month=target_month, year=target_year)

        now = time.time()
        sent_alerts = []

        for alert in alerts_data.items:
            # If specific category_id provided, only alert for that category
            if category_id is not None and alert.category_id != category_id:
                continue

            cache_key = (self.user.id, alert.category_id, alert.status)
            last_sent = _ALERT_COOLDOWN_CACHE.get(cache_key, 0.0)

            # Prevent email spamming if already alerted recently for the same category and status
            if (now - last_sent) < _ALERT_COOLDOWN_SECONDS:
                remaining_cd = int(_ALERT_COOLDOWN_SECONDS - (now - last_sent))
                logger.info(
                    "Bỏ qua gửi email cảnh báo danh mục '%s' (%s) do đang trong thời gian giãn cách (còn %ds).",
                    alert.category_name,
                    alert.status,
                    remaining_cd,
                )
                continue

            # Update cooldown timestamp immediately
            _ALERT_COOLDOWN_CACHE[cache_key] = now

            # Non-blocking async dispatch via thread pool (0ms blocking on HTTP thread)
            _email_executor.submit(
                _dispatch_alert_email,
                to_email=self.user.email,
                category_name=alert.category_name,
                budget_amount=float(alert.amount),
                spent_amount=float(alert.spent_amount),
                percentage_used=float(alert.percentage_used),
                status=alert.status,
            )

            sent_alerts.append({
                "category_id": alert.category_id,
                "category_name": alert.category_name,
                "status": alert.status,
                "percentage_used": alert.percentage_used,
                "async_dispatched": True,
            })

        return sent_alerts
