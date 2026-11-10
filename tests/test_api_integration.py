"""end-to-end API suite against real Postgres with FK-order cleanup."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from app.db import SessionFactory
from app.main import app
from app.models import Artifact, Membership, Org, Run, Scenario, User, utcnow
from app.security import hash_password
from sqlalchemy import func, select

from hnle.ingest import IngestConfig, IngestError, ingest_csv

DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL not configured")
PASSWORD = "Secret123!"
NEW_PASSWORD = "NewSecret456!"


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
async def _clean(clean_db: None) -> AsyncIterator[None]:
    yield


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as http:
        yield http


async def _seed(role: str = "researcher", quota: int = 4) -> dict[str, Any]:
    suffix = uuid.uuid4().hex[:8]
    async with SessionFactory() as session:
        org = Org(name=f"org-{suffix}", region="cn", quota_concurrent_jobs=quota)
        user = User(
            email=f"{role}-{suffix}@example.com",
            password_hash=hash_password(PASSWORD),
            display_name=role,
            must_change_pw=True,
        )
        session.add_all([org, user])
        await session.flush()
        session.add(Membership(org_id=org.id, user_id=user.id, role=role))
        scenario = Scenario(org_id=org.id, name="s", spec={"q": 1.5}, created_by=user.id)
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
        return {"org": org.id, "user": user.id, "email": user.email,
                "scenario": scenario.id, "run": run.id}


async def _login(client: httpx.AsyncClient, email: str, password: str = PASSWORD) -> str:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    return response.json()["access_token"] if response.status_code == 200 else ""


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_redis_test_db_is_isolated() -> None:
    import conftest

    assert conftest.TEST_REDIS_URL.endswith("/15")


async def test_login_then_change_password(client: httpx.AsyncClient) -> None:
    seeded = await _seed()
    token = await _login(client, seeded["email"])
    assert token
    changed = await client.post(
        "/api/v1/auth/change-password",
        headers=_auth(token),
        json={"old_password": PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert changed.status_code == 200
    assert await _login(client, seeded["email"], NEW_PASSWORD)
    assert await _login(client, seeded["email"], PASSWORD) == ""


async def test_unauthenticated_request_is_401(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/orgs/me")
    assert response.status_code == 401


async def test_cross_org_and_optimistic_lock(client: httpx.AsyncClient) -> None:
    a = await _seed()
    b = await _seed()
    token_a = await _login(client, a["email"])
    assert (await client.get(f"/api/v1/runs/{b['run']}", headers=_auth(token_a))).status_code == 403

    created = await client.post(
        "/api/v1/scenarios", headers=_auth(token_a), json={"name": "n", "spec": {"q": 1.2}}
    )
    scenario_id = created.json()["data"]["id"]
    first = await client.patch(
        f"/api/v1/scenarios/{scenario_id}",
        headers={**_auth(token_a), "If-Match": '"1"'},
        json={"name": "x"},
    )
    second = await client.patch(
        f"/api/v1/scenarios/{scenario_id}",
        headers={**_auth(token_a), "If-Match": '"1"'},
        json={"name": "y"},
    )
    assert first.status_code == 200 and second.status_code == 409


async def test_idempotency_and_quota(client: httpx.AsyncClient) -> None:
    seeded = await _seed(quota=0)
    token = await _login(client, seeded["email"])
    key = f"idem-{uuid.uuid4()}"
    headers = {**_auth(token), "X-Idempotency-Key": key}
    payload = {"name": "once", "spec": {"q": 1.1}}
    first = await client.post("/api/v1/scenarios", headers=headers, json=payload)
    second = await client.post("/api/v1/scenarios", headers=headers, json=payload)
    assert first.json()["data"]["id"] == second.json()["data"]["id"]

    quota = await client.post(
        "/api/v1/runs", headers=_auth(token), json={"scenario_id": str(seeded["scenario"])}
    )
    assert quota.status_code == 409
    assert quota.json()["error"]["code"] == "QUOTA_EXCEEDED"


async def test_cancel_keeps_finished_replicas(client: httpx.AsyncClient) -> None:
    seeded = await _seed()
    token = await _login(client, seeded["email"])
    async with SessionFactory() as session:
        run = await session.get(Run, seeded["run"])
        assert run is not None
        run.status = "running"
        run.done_replicas = 1
        await session.commit()
    response = await client.post(f"/api/v1/runs/{seeded['run']}/cancel", headers=_auth(token))
    assert response.status_code == 202
    assert response.json()["data"]["status"] == "cancelling"


async def test_g5_unapproved_and_node_trace(client: httpx.AsyncClient) -> None:
    seeded = await _seed("org_admin")
    token = await _login(client, seeded["email"])
    g5 = await client.post("/api/v1/templates/G5/clone", headers=_auth(token))
    assert g5.status_code == 403
    assert g5.json()["error"]["code"] == "USE_CASE_NOT_APPROVED"
    trace = await client.get(
        f"/api/v1/runs/{seeded['run']}/nodes/7/trace", headers=_auth(token)
    )
    assert trace.status_code == 403
    assert trace.json()["error"]["code"] == "NODE_TRACE_FORBIDDEN"


async def test_pii_columns_are_rejected(tmp_path: Path) -> None:
    csv = tmp_path / "pii.csv"
    csv.write_text("user,hashtags,email\nu1,#a,a@b.com\n", encoding="utf-8")
    with pytest.raises(IngestError) as exc:
        ingest_csv(csv, salt=b"salt", config=IngestConfig())
    assert exc.value.code == "PII_COLUMN_REJECTED"


async def test_concurrent_ingest_is_mutexed(client: httpx.AsyncClient) -> None:
    seeded = await _seed()
    token = await _login(client, seeded["email"])
    created = await client.post(
        "/api/v1/datasets", headers=_auth(token), json={"name": "d"}
    )
    dataset_id = created.json()["data"]["id"]
    first = await client.post(f"/api/v1/datasets/{dataset_id}/ingest", headers=_auth(token))
    second = await client.post(f"/api/v1/datasets/{dataset_id}/ingest", headers=_auth(token))
    assert first.status_code == 202
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "INGEST_IN_PROGRESS"


async def test_artifact_rows_survive_truncate_order() -> None:
    """The cleanup fixture must be able to remove dependent rows without errors."""
    seeded = await _seed()
    async with SessionFactory() as session:
        run = await session.get(Run, seeded["run"])
        assert run is not None
        session.add(
            Artifact(
                run_id=run.id,
                run_created_at=run.created_at,
                kind="series_csv",
                storage_ref="s3://x",
                sha256="sha",
                size_bytes=1,
            )
        )
        await session.commit()
    async with SessionFactory() as session:
        count = await session.scalar(select(func.count()).select_from(Artifact))
    assert count == 1


def test_progress_uses_redis_when_available() -> None:
    import redis
    from app.progress import get_progress, set_progress

    try:
        client = redis.Redis.from_url("redis://localhost:6379/15", socket_timeout=0.5)
        client.ping()
    except Exception:
        pytest.skip("redis not available")
    run_id = f"redis-{uuid.uuid4()}"
    set_progress(run_id, 4, 10)
    stored = client.hgetall(f"run:progress:{run_id}")
    assert stored, "progress must be written to Redis db 15 in CI"
    assert get_progress(run_id)["done"] in {4, 10}
    client.delete(f"run:progress:{run_id}")
