"""Short-lived per-dataset ingest locks (single-flight)."""

from __future__ import annotations

import time

_TTL_SECONDS = 30 * 60
_locks: dict[str, float] = {}


def acquire_ingest_lock(dataset_id: str, now: float | None = None) -> bool:
    current = time.monotonic() if now is None else now
    expires = _locks.get(dataset_id)
    if expires is not None and expires > current:
        return False
    _locks[dataset_id] = current + _TTL_SECONDS
    return True


def release_ingest_lock(dataset_id: str) -> None:
    _locks.pop(dataset_id, None)
