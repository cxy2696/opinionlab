"""Connector abstraction with whitelist, token bucket and circuit breaker.

Only public, whitelisted sites and user-owned exports are allowed. Any login
wall / captcha / credential-bearing request is a policy violation and trips the
breaker immediately.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from urllib.parse import parse_qs, urlparse


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class ConnectorError(RuntimeError):
    pass


class PolicyViolation(ConnectorError):
    pass


class CircuitOpenError(ConnectorError):
    pass


class RateLimitedError(ConnectorError):
    pass


FORBIDDEN_URL_MARKERS = ("login", "signin", "sign-in", "captcha", "challenge", "verify")
FORBIDDEN_PARAMS = ("cookie", "cookies", "password", "passwd", "token", "session")


@dataclass(frozen=True)
class ConnectorConfig:
    allowed_hosts: frozenset[str] = frozenset()
    requests_per_second: float = 2.0
    failure_threshold: int = 5
    cooldown_seconds: int = 1800

    def host_allowed(self, host: str) -> bool:
        lowered = host.lower()
        return any(
            lowered == allowed.lower() or lowered.endswith("." + allowed.lower())
            for allowed in self.allowed_hosts
        )


class TokenBucket:
    """Per-site global token bucket (default 2 req/s)."""

    def __init__(self, rate: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.rate = rate
        self.capacity = rate
        self.tokens = rate
        self.updated = clock()
        self.clock = clock

    def acquire(self) -> bool:
        now = self.clock()
        self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
        self.updated = now
        if self.tokens < 1.0:
            return False
        self.tokens -= 1.0
        return True


class CircuitBreaker:
    """5 consecutive failures open the circuit for 30 minutes, then half-open."""

    def __init__(
        self,
        config: ConnectorConfig,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.config = config
        self.clock = clock
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.opened_at = 0.0
        self.probe_in_flight = False

    def allow(self) -> bool:
        if self.state is CircuitState.OPEN:
            if self.clock() - self.opened_at >= self.config.cooldown_seconds:
                self.state = CircuitState.HALF_OPEN
                self.probe_in_flight = False
            else:
                return False
        if self.state is CircuitState.HALF_OPEN:
            if self.probe_in_flight:
                return False
            self.probe_in_flight = True
        return True

    def record_success(self) -> None:
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.probe_in_flight = False

    def record_failure(self) -> None:
        if self.state is CircuitState.HALF_OPEN:
            self.trip()
            return
        self.failures += 1
        if self.failures >= self.config.failure_threshold:
            self.trip()

    def trip(self) -> None:
        self.state = CircuitState.OPEN
        self.opened_at = self.clock()
        self.probe_in_flight = False


@dataclass
class Connector:
    """Whitelisted fetch path; ``fetcher`` is injectable for tests."""

    config: ConnectorConfig
    fetcher: Callable[[str, dict[str, str]], dict[str, object]]
    clock: Callable[[], float] = time.monotonic
    buckets: dict[str, TokenBucket] = field(default_factory=dict)
    breaker: CircuitBreaker = field(init=False)

    def __post_init__(self) -> None:
        self.breaker = CircuitBreaker(self.config, self.clock)

    def _validate(self, url: str, params: dict[str, str]) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise PolicyViolation("only http(s) URLs are allowed")
        if not self.config.host_allowed(parsed.hostname or ""):
            raise PolicyViolation(f"host {parsed.hostname!r} is not whitelisted")
        path = parsed.path.lower()
        if any(marker in path for marker in FORBIDDEN_URL_MARKERS):
            self.breaker.trip()
            raise PolicyViolation("login walls and captcha bypasses are forbidden")
        lowered_params = {key.lower() for key in params}
        if any(key in lowered_params for key in FORBIDDEN_PARAMS):
            self.breaker.trip()
            raise PolicyViolation("credential/cookie parameters are forbidden")
        if parse_qs(parsed.query) and any(
            key in {k.lower() for k in parse_qs(parsed.query)} for key in FORBIDDEN_PARAMS
        ):
            self.breaker.trip()
            raise PolicyViolation("credential/cookie query parameters are forbidden")
        return parsed.hostname or ""

    def fetch(self, url: str, params: dict[str, str] | None = None) -> dict[str, object]:
        query = params or {}
        host = self._validate(url, query)
        if not self.breaker.allow():
            raise CircuitOpenError(f"connector circuit open for {host}")
        bucket = self.buckets.setdefault(
            host, TokenBucket(self.config.requests_per_second, self.clock)
        )
        if not bucket.acquire():
            raise RateLimitedError(f"rate limit exceeded for {host}")
        try:
            payload = self.fetcher(url, query)
        except Exception:
            self.breaker.record_failure()
            raise
        self.breaker.record_success()
        return payload


class FileImportConnector:
    """Manual upload path: no network, always available as L1 degradation."""

    def load(self, path: str) -> bytes:
        with open(path, "rb") as handle:
            return handle.read()


def public_api_connector(hosts: list[str]) -> Connector:
    """Minimal public-API connector (httpx), restricted to the whitelist."""
    import httpx

    def fetch(url: str, params: dict[str, str]) -> dict[str, object]:
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        return {"status": response.status_code, "url": str(response.url)}

    return Connector(ConnectorConfig(allowed_hosts=frozenset(hosts)), fetch)


def configured_connector() -> Connector:
    """Connector built from the CONNECTOR_ALLOWED_HOSTS whitelist."""
    from app.settings import settings

    hosts = [host.strip() for host in settings.connector_allowed_hosts.split(",") if host.strip()]
    return public_api_connector(hosts)


def degraded_mode(connector_failed: bool) -> dict[str, object]:
    """L1 degradation message; already-ingested data is never affected."""
    if not connector_failed:
        return {"level": "L0", "manual_upload_only": False}
    return {
        "level": "L1",
        "manual_upload_only": True,
        "existing_data_affected": False,
        "message_zh": "连接器不可用，仅支持手动上传导入。",
        "message_en": "Connector unavailable: manual upload only.",
    }
