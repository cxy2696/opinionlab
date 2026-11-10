"""Shared test fixtures: isolation first, features second (PRD 12.4 / 13.1).

Every fixture keeps tests away from the working directory, from the developer
database and from global environment state.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from hypothesis import HealthCheck, settings

TEST_DATABASE_NAME = "opinionlab_test"
TEST_REDIS_URL = "redis://localhost:6379/15"


settings.register_profile(
    "ci", max_examples=200, deadline=None, suppress_health_check=[HealthCheck.too_slow]
)
settings.register_profile("default", max_examples=50, deadline=None)
settings.load_profile("ci" if os.environ.get("CI") else "default")


@pytest.fixture
def artifact_dir(tmp_path: Path) -> Path:
    """Injected output directory: nothing may be written to the CWD."""
    directory = tmp_path / "artifacts"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


@pytest.fixture
def test_db_name() -> str:
    """Tests never touch the dev database (PRD 12.4)."""
    return TEST_DATABASE_NAME


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Remove OPINIONLAB_* variables and restore the environment afterwards."""
    for key in list(os.environ):
        if key.startswith("OPINIONLAB_"):
            monkeypatch.delenv(key, raising=False)
    return monkeypatch


@pytest.fixture
def redis_test_client() -> Iterator[Any]:
    """Redis on db 15, flushed before and after; skipped when redis is absent."""
    redis = pytest.importorskip("redis")
    url = os.environ.get("TEST_REDIS_URL", TEST_REDIS_URL)
    client = redis.Redis.from_url(url, decode_responses=True)
    try:
        client.ping()
    except Exception:  # pragma: no cover - depends on local services
        pytest.skip(f"redis not reachable at {url}")
    client.flushdb()
    try:
        yield client
    finally:
        client.flushdb()
