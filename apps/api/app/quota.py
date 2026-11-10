"""Concurrency quota and long-run confirmation ()."""

from __future__ import annotations

from dataclasses import dataclass

from app.errors import ApiError

SECOND_CONFIRM_SECONDS = 30 * 60


@dataclass(frozen=True)
class QuotaDecision:
    position: int
    estimated_seconds: float


def estimate_seconds(nnz: int, n_steps: int, repeats: int, cores: int = 8) -> float:
    """Capacity shape: work / (cores * throughput)."""
    throughput = 250_000.0  # edges*steps per second per core (calibrated placeholder)
    return max(1.0, nnz * n_steps * repeats / (cores * throughput))


def check_quota(
    active_jobs: int,
    limit: int,
    estimated_seconds: float,
    *,
    confirmed: bool = False,
) -> QuotaDecision:
    if active_jobs >= limit:
        raise ApiError(
            409,
            "QUOTA_EXCEEDED",
            "concurrent job quota exceeded",
            {
                "position": active_jobs - limit + 1,
                "estimated_seconds": round(estimated_seconds, 1),
            },
        )
    if estimated_seconds > SECOND_CONFIRM_SECONDS and not confirmed:
        raise ApiError(
            428,
            "CONFIRM_REQUIRED",
            "run is estimated above 30 minutes and needs secondary confirmation",
            {"estimated_seconds": round(estimated_seconds, 1)},
        )
    return QuotaDecision(position=0, estimated_seconds=estimated_seconds)
