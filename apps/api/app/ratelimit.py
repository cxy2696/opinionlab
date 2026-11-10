"""Token-bucket rate limiting: global / IP / user / org."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.security import decode_token
from app.settings import settings


@dataclass
class _Bucket:
    tokens: float
    updated: float = field(default_factory=time.monotonic)


_buckets: dict[str, _Bucket] = {}


def _allow(key: str, rate: float, capacity: float | None = None) -> bool:
    now = time.monotonic()
    bucket = _buckets.get(key)
    cap = capacity or rate
    if bucket is None:
        bucket = _Bucket(tokens=cap, updated=now)
        _buckets[key] = bucket
    elapsed = now - bucket.updated
    bucket.tokens = min(cap, bucket.tokens + elapsed * rate)
    bucket.updated = now
    if bucket.tokens < 1.0:
        return False
    bucket.tokens -= 1.0
    return True


def reset() -> None:
    _buckets.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: object) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        user_key = ""
        org_key = ""
        authorization = request.headers.get("Authorization", "")
        if authorization.startswith("Bearer "):
            try:
                payload = decode_token(authorization[7:], "access")
                user_key, org_key = str(payload.get("sub", "")), str(payload.get("org_id", ""))
            except ValueError:
                pass
        checks = [
            ("global", float(settings.rate_limit_global_rps)),
            (f"ip:{client_ip}", float(settings.rate_limit_ip_rps)),
        ]
        if user_key:
            checks.append((f"user:{user_key}", float(settings.rate_limit_user_rps)))
        if org_key:
            checks.append((f"org:{org_key}", float(settings.rate_limit_org_rps)))
        for key, rate in checks:
            if not _allow(key, rate):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "RATE_LIMITED",
                            "message": "too many requests",
                            "details": {"scope": key.split(":")[0]},
                            "trace_id": getattr(request.state, "trace_id", ""),
                        }
                    },
                    headers={"Retry-After": "1"},
                )
        response: Response = await call_next(request)  # type: ignore[operator]
        return response
