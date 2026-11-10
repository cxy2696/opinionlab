"""US-020: whitelist, token bucket, circuit breaker and L1 degradation."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.connectors import (
    CircuitOpenError,
    CircuitState,
    Connector,
    ConnectorConfig,
    FileImportConnector,
    PolicyViolation,
    RateLimitedError,
    TokenBucket,
    degraded_mode,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _connector(
    fetcher: object | None = None, clock: FakeClock | None = None
) -> tuple[Connector, FakeClock]:
    fake_clock = clock or FakeClock()
    calls: list[str] = []

    def default_fetcher(url: str, params: dict[str, str]) -> dict[str, object]:
        calls.append(url)
        return {"ok": True}

    connector = Connector(
        ConnectorConfig(allowed_hosts=frozenset({"api.example.com"}), requests_per_second=2.0),
        fetcher or default_fetcher,  # type: ignore[arg-type]
        clock=fake_clock,
    )
    return connector, fake_clock


def test_whitelist_rejects_unknown_host() -> None:
    connector, _ = _connector()
    with pytest.raises(PolicyViolation):
        connector.fetch("https://evil.example.org/data")


def test_token_bucket_allows_two_requests_per_second() -> None:
    clock = FakeClock()
    bucket = TokenBucket(2.0, clock)
    assert bucket.acquire()
    assert bucket.acquire()
    assert not bucket.acquire()
    clock.advance(1.0)
    assert bucket.acquire()


def test_rate_limit_applies_per_site() -> None:
    connector, clock = _connector()
    assert connector.fetch("https://api.example.com/a")["ok"] is True
    assert connector.fetch("https://api.example.com/b")["ok"] is True
    with pytest.raises(RateLimitedError):
        connector.fetch("https://api.example.com/c")
    clock.advance(1.0)
    assert connector.fetch("https://api.example.com/d")["ok"] is True


def test_five_failures_open_then_half_open_closes() -> None:
    clock = FakeClock()
    calls = {"count": 0, "failing": True}

    def fetcher(url: str, params: dict[str, str]) -> dict[str, object]:
        calls["count"] += 1
        if calls["failing"]:
            raise RuntimeError("upstream down")
        return {"ok": True}

    connector, _ = _connector(fetcher, clock)
    for _ in range(5):
        clock.advance(1.0)
        with pytest.raises(RuntimeError):
            connector.fetch("https://api.example.com/x")
    assert connector.breaker.state is CircuitState.OPEN

    clock.advance(60)
    with pytest.raises(CircuitOpenError):
        connector.fetch("https://api.example.com/y")

    clock.advance(1800)
    calls["failing"] = False
    assert connector.fetch("https://api.example.com/z")["ok"] is True
    assert connector.breaker.state is CircuitState.CLOSED
    assert connector.breaker.failures == 0


def test_login_wall_violation_trips_breaker() -> None:
    connector, _ = _connector()
    with pytest.raises(PolicyViolation):
        connector.fetch("https://api.example.com/login")
    assert connector.breaker.state is CircuitState.OPEN


def test_credential_parameter_is_rejected() -> None:
    connector, _ = _connector()
    with pytest.raises(PolicyViolation):
        connector.fetch("https://api.example.com/data", {"cookie": "session=abc"})
    assert connector.breaker.state is CircuitState.OPEN


def test_file_import_and_l1_degradation(tmp_path: Path) -> None:
    path = tmp_path / "export.csv"
    path.write_bytes(b"user,hashtags\nu1,#a\n")
    assert FileImportConnector().load(str(path)).startswith(b"user")

    normal = degraded_mode(False)
    assert normal["level"] == "L0"
    degraded = degraded_mode(True)
    assert degraded["level"] == "L1"
    assert degraded["manual_upload_only"] is True
    assert degraded["existing_data_affected"] is False
    assert "手动上传" in str(degraded["message_zh"])
