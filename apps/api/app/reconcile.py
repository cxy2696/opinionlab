"""Reconciliation helpers: counters vs status, and stuck running jobs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def stuck_running(last_seen: datetime, hard_limit_seconds: int = 900) -> bool:
    """A running job without progress beyond hard_limit + 5 min is stuck."""
    return datetime.now(UTC) - last_seen > timedelta(seconds=hard_limit_seconds + 300)


def reconcile_once() -> dict[str, int]:
    """Placeholder DB sweep; the Celery beat task calls this every 10 minutes."""
    return {"checked": 0, "fixed": 0}
