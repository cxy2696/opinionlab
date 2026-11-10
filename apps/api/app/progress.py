"""Run progress counters: Redis when available, in-memory fallback for tests."""

from __future__ import annotations

import threading
from typing import Any

from app.settings import settings

_lock = threading.Lock()
_memory: dict[str, dict[str, int]] = {}
_redis: Any = None
_redis_checked = False


def _client() -> Any:
    global _redis, _redis_checked
    if _redis_checked:
        return _redis
    _redis_checked = True
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, socket_timeout=1.0)
        client.ping()
        _redis = client
    except Exception:  # pragma: no cover - depends on environment
        _redis = None
    return _redis


def set_progress(run_id: str, done: int, total: int) -> None:
    client = _client()
    if client is not None:
        try:
            client.hset(f"run:progress:{run_id}", mapping={"done": done, "total": total})
            return
        except Exception:  # pragma: no cover
            pass
    with _lock:
        _memory[run_id] = {"done": done, "total": total}


def get_progress(run_id: str) -> dict[str, int]:
    client = _client()
    if client is not None:
        try:
            payload = client.hgetall(f"run:progress:{run_id}")
            if payload:
                return {
                    "done": int(payload.get(b"done", payload.get("done", 0))),
                    "total": int(payload.get(b"total", payload.get("total", 0))),
                }
        except Exception:  # pragma: no cover
            pass
    with _lock:
        return dict(_memory.get(run_id, {"done": 0, "total": 0}))
