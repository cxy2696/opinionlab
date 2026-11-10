"""the 24-endpoint surface, state machine, quota, rate limit, queue."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator
from datetime import UTC
from pathlib import Path
from typing import Any

import pytest
from app.celery_app import celery_app
from app.db import SessionFactory
from app.main import app
from app.models import Membership, Org, Run, Scenario, User, utcnow
from app.progress import get_progress, set_progress
from app.quota import check_quota, estimate_seconds
from app.ratelimit import reset as reset_rate_limit
from app.reconcile import stuck_running
from app.security import hash_password
from app.settings import settings
from app.state import (
    InvalidTransition,
    finalize_cancel,
    reconcile_status,
    request_cancel,
    transition,
)
from httpx import ASGITransport, AsyncClient

DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL not configured")
PASSWORD = "Secret123!"

EXPECTED_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/logout",
    "/api/v1/orgs/me",
    "/api/v1/datasets",
    "/api/v1/datasets/{dataset_id}",
    "/api/v1/datasets/{dataset_id}/ingest",
    "/api/v1/scenarios",
    "/api/v1/scenarios/{scenario_id}",
    "/api/v1/templates",
    "/api/v1/templates/{key}/clone",
    "/api/v1/runs",
    "/api/v1/runs/{run_id}",
    "/api/v1/runs/{run_id}/metrics",
    "/api/v1/runs/{run_id}/artifacts",
    "/api/v1/runs/{run_id}/cancel",
    "/api/v1/compare",
    "/api/v1/reports/{run_id}/export",
}


@pytest.fixture(scope="module", autouse=True)
def schema() -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "DATABASE_URL": DATABASE_URL or ""},
        check=True,
        capture_output=True,
    )


@pytest.fixture(autouse=True)
def _fresh_rate_limit() -> None:
    reset_rate_limit()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as http:
        yield http


async def _seed(quota: int = 4, role: str = "researcher") -> dict[str, Any]:
    suffix = uuid.uuid4().hex[:8]
    async with SessionFactory() as session:
        org = Org(name=f"org-{suffix}", region="cn", quota_concurrent_jobs=quota)
        user = User(
            email=f"u-{suffix}@example.com",
            password_hash=hash_password(PASSWORD),
            display_name=role,
        )
        session.add_all([org, user])
        await session.flush()
        session.add(Membership(org_id=org.id, user_id=user.id, role=role))
        scenario = Scenario(
            org_id=org.id, name="s", spec={"q": 1.5, "n_steps": 20}, created_by=user.id
        )
        session.add(scenario)
        await session.flush()
        run = Run(
            org_id=org.id,
            scenario_id=scenario.id,
            run_id_external=f"r-{suffix}",
            spec_sha256="sha",
            manifest={},
            repeats=2,
            created_by=user.id,
            created_at=utcnow(),
        )
        session.add(run)
        await session.commit()
        return {"org": org.id, "user": user.id, "scenario": scenario.id, "run": run.id,
                "email": user.email}


async def _token(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return str(response.json()["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_openapi_contains_the_24_endpoints() -> None:
    schema = app.openapi()
    paths = set(schema["paths"])
    assert paths >= EXPECTED_PATHS, EXPECTED_PATHS - paths
    methods = {
        (path, verb)
        for path, operations in schema["paths"].items()
        for verb in operations
        if verb in {"get", "post", "patch", "delete"}
    }
    assert len(methods) >= 24
    for path in ("/api/v1/auth/login", "/api/v1/runs", "/api/v1/scenarios", "/api/v1/compare"):
        assert path in schema["paths"]


def test_four_core_endpoints_carry_json_examples() -> None:
    schema = app.openapi()
    components = schema["components"]["schemas"]
    assert "example" in components["LoginRequest"]
    assert "example" in components["RunCreate"]
    assert "example" in components["CompareRequest"]
    metrics = schema["paths"]["/api/v1/runs/{run_id}/metrics"]["get"]["responses"]["200"]
    assert "example" in metrics["content"]["application/json"]
    login_responses = schema["paths"]["/api/v1/auth/login"]["post"]["responses"]["200"]
    assert "example" in login_responses["content"]["application/json"]


def test_state_machine_forbids_skipping_cancelled() -> None:
    assert transition("queued", "running") == "running"
    with pytest.raises(InvalidTransition):
        transition("queued", "cancelled")
    status, accepted = request_cancel("queued", 0, 4)
    assert accepted and status == "cancelling"
    assert finalize_cancel("cancelling") == "cancelled"
    with pytest.raises(InvalidTransition):
        finalize_cancel("running")


def test_cancel_preserves_finished_replicas() -> None:
    status, accepted = request_cancel("running", done_replicas=2, repeats=5)
    assert accepted and status == "cancelling"
    assert reconcile_status(5, 5, "running") == "succeeded"
    assert reconcile_status(2, 5, "succeeded") == "partial"


def test_stuck_running_detection() -> None:
    from datetime import datetime, timedelta

    assert stuck_running(datetime.now(UTC) - timedelta(minutes=25))
    assert not stuck_running(datetime.now(UTC))


def test_quota_and_confirmation() -> None:
    with pytest.raises(Exception) as exc:
        check_quota(4, 4, 10.0)
    assert getattr(exc.value, "code", "") == "QUOTA_EXCEEDED"
    assert check_quota(0, 4, 10.0).estimated_seconds == 10.0
    with pytest.raises(Exception) as exc:
        check_quota(0, 4, 3600.0)
    assert getattr(exc.value, "code", "") == "CONFIRM_REQUIRED"
    assert check_quota(0, 4, 3600.0, confirmed=True).estimated_seconds == 3600.0
    assert estimate_seconds(1000, 100, 2) > 0


def test_progress_fallback_roundtrip() -> None:
    run_id = f"run-{uuid.uuid4()}"
    set_progress(run_id, 3, 10)
    assert get_progress(run_id) == {"done": 3, "total": 10}


def test_celery_queue_configuration() -> None:
    conf = celery_app.conf
    assert {queue.name for queue in conf.task_queues} == {"q_normal", "q_batch", "q_ingest"}
    assert conf.task_routes["app.tasks.run_simulation"]["queue"] == "q_normal"
    assert conf.task_routes["app.tasks.run_batch"]["queue"] == "q_batch"
    assert conf.task_annotations["app.tasks.run_simulation"]["time_limit"] == 900
    assert conf.task_annotations["app.tasks.run_batch"]["time_limit"] == 3900
    assert conf.beat_schedule["reconcile-runs"]["schedule"] == 600.0


async def test_extended_endpoints_work(client: AsyncClient) -> None:
    seeded = await _seed()
    token = await _token(client, seeded["email"])

    dataset = await client.post(
        "/api/v1/datasets",
        headers={**_auth(token), "X-Idempotency-Key": f"ds-{uuid.uuid4()}"},
        json={"name": "d1", "source_type": "upload_csv"},
    )
    assert dataset.status_code == 201
    dataset_id = dataset.json()["data"]["id"]
    assert (await client.get("/api/v1/datasets", headers=_auth(token))).status_code == 200
    assert (
        await client.get(f"/api/v1/datasets/{dataset_id}", headers=_auth(token))
    ).status_code == 200
    assert (
        await client.post(f"/api/v1/datasets/{dataset_id}/ingest", headers=_auth(token))
    ).status_code == 202

    templates = await client.get("/api/v1/templates", headers=_auth(token))
    assert templates.status_code == 200
    assert any(item["key"] == "S2" for item in templates.json()["data"])
    clone = await client.post("/api/v1/templates/S2/clone", headers=_auth(token))
    assert clone.status_code == 201

    metrics = await client.get(
        f"/api/v1/runs/{seeded['run']}/metrics", headers=_auth(token)
    )
    assert metrics.status_code == 200
    artifacts = await client.get(
        f"/api/v1/runs/{seeded['run']}/artifacts", headers=_auth(token)
    )
    assert artifacts.status_code == 200

    compare = await client.post(
        "/api/v1/compare",
        headers=_auth(token),
        json={"run_ids": [str(seeded["run"]), str(seeded["run"])]},
    )
    assert compare.status_code == 202


async def test_cancel_enters_cancelling_and_keeps_replicas(client: AsyncClient) -> None:
    seeded = await _seed()
    token = await _token(client, seeded["email"])
    async with SessionFactory() as session:
        run = await session.get(Run, seeded["run"])
        assert run is not None
        run.status = "running"
        run.done_replicas = 1
        await session.commit()

    response = await client.post(f"/api/v1/runs/{seeded['run']}/cancel", headers=_auth(token))
    assert response.status_code == 202
    assert response.json()["data"]["status"] == "cancelling"

    async with SessionFactory() as session:
        run = await session.get(Run, seeded["run"])
        assert run is not None
        assert run.status == "cancelling"
        assert run.done_replicas == 1


async def test_quota_via_api_returns_409(client: AsyncClient) -> None:
    seeded = await _seed(quota=0)
    token = await _token(client, seeded["email"])
    response = await client.post(
        "/api/v1/runs", headers=_auth(token), json={"scenario_id": str(seeded["scenario"])}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "QUOTA_EXCEEDED"
    assert "position" in response.json()["error"]["details"]


async def test_long_run_requires_confirmation(client: AsyncClient) -> None:
    seeded = await _seed()
    token = await _token(client, seeded["email"])
    async with SessionFactory() as session:
        scenario = await session.get(Scenario, seeded["scenario"])
        assert scenario is not None
        scenario.spec = {"q": 1.5, "n_steps": 200000}
        await session.commit()
    response = await client.post(
        "/api/v1/runs",
        headers=_auth(token),
        json={"scenario_id": str(seeded["scenario"]), "repeats": 500},
    )
    assert response.status_code == 428
    assert response.json()["error"]["code"] == "CONFIRM_REQUIRED"


async def test_rate_limit_returns_429(client: AsyncClient) -> None:
    seeded = await _seed()
    token = await _token(client, seeded["email"])
    original = settings.rate_limit_user_rps
    settings.rate_limit_user_rps = 1
    try:
        reset_rate_limit()
        first = await client.get("/api/v1/orgs/me", headers=_auth(token))
        second = await client.get("/api/v1/orgs/me", headers=_auth(token))
    finally:
        settings.rate_limit_user_rps = original
        reset_rate_limit()
    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers.get("Retry-After") == "1"
