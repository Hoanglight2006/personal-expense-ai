"""Timezone helpers for Vietnam Standard Time (Asia/Ho_Chi_Minh - UTC+7)."""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta

VIETNAM_TZ_OFFSET = timezone(timedelta(hours=7), name="Asia/Ho_Chi_Minh")


def local_now() -> datetime:
    """Return current datetime in Vietnam time (UTC+7)."""
    return datetime.now(VIETNAM_TZ_OFFSET)


def local_today() -> date:
    """Return current date in Vietnam time (UTC+7)."""
    return local_now().date()
