"""US-017: auth, RBAC, tenant isolation, optimistic locking and idempotency."""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from app.db import SessionFactory
from app.main import app
from app.models import (
    AuditLog,
    Dataset,
    Membership,
    Org,
    Run,
    RunShare,
    Scenario,
    User,
    utcnow,
)
from app.security import hash_password
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL not configured")

PASSWORD = "Secret123!"


def _alembic() -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "DATABASE_URL": DATABASE_URL or ""},
        check=True,
        capture_output=True,
    )


@pytest.fixture(scope="module", autouse=True)
def schema() -> None:
    _alembic()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http


async def _seed(role: str = "researcher") -> dict[str, Any]:
    suffix = uuid.uuid4().hex[:8]
    async with SessionFactory() as session:
        org = Org(name=f"org-{suffix}", region="cn")
        user = User(
            email=f"{role}-{suffix}@example.com",
            password_hash=hash_password(PASSWORD),
            display_name=role,
        )
        session.add_all([org, user])
        await session.flush()
        session.add(Membership(org_id=org.id, user_id=user.id, role=role))
        dataset = Dataset(org_id=org.id, name="ds", source_type="upload_csv")
        session.add(dataset)
        await session.flush()
        scenario = Scenario(
            org_id=org.id,
            name=f"scenario-{suffix}",
            spec={"q": 1.5},
            created_by=user.id,
        )
        session.add(scenario)
        await session.flush()
        run = Run(
            org_id=org.id,
            scenario_id=scenario.id,
            run_id_external=f"run-{suffix}",
            spec_sha256="sha",
            manifest={},
            repeats=2,
            created_by=user.id,
            created_at=utcnow(),
        )
        session.add(run)
        await session.commit()
        return {
            "org": org.id,
            "user": user.id,
            "dataset": dataset.id,
            "scenario": scenario.id,
            "run": run.id,
            "email": user.email,
        }


async def _token(client: AsyncClient, email: str, password: str = PASSWORD) -> str:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return str(response.json()["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_login_and_lockout_after_five_failures(client: AsyncClient) -> None:
    seeded = await _seed("analyst")
    token = await _token(client, seeded["email"])
    assert token

    for _ in range(5):
        bad = await client.post(
            "/api/v1/auth/login", json={"email": seeded["email"], "password": "wrong"}
        )
    assert bad.status_code == 401
    locked = await client.post(
        "/api/v1/auth/login", json={"email": seeded["email"], "password": PASSWORD}
    )
    assert locked.status_code == 423
    assert locked.json()["error"]["code"] == "LOCKED"


async def test_refresh_rotation_and_logout(client: AsyncClient) -> None:
    seeded = await _seed()
    login = await client.post(
        "/api/v1/auth/login", json={"email": seeded["email"], "password": PASSWORD}
    )
    first_refresh = login.json()["refresh_token"]
    rotated = await client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert rotated.status_code == 200
    reused = await client.post("/api/v1/auth/refresh", json={"refresh_token": first_refresh})
    assert reused.status_code == 401

    second_refresh = rotated.json()["refresh_token"]
    logged_out = await client.post("/api/v1/auth/logout", json={"refresh_token": second_refresh})
    assert logged_out.status_code == 200
    after = await client.post("/api/v1/auth/refresh", json={"refresh_token": second_refresh})
    assert after.status_code == 401


async def test_cross_org_access_returns_403(client: AsyncClient) -> None:
    org_a = await _seed()
    org_b = await _seed()
    token_a = await _token(client, org_a["email"])
    token_b = await _token(client, org_b["email"])

    denied = await client.get(f"/api/v1/runs/{org_b['run']}", headers=_auth(token_a))
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "FORBIDDEN"

    allowed = await client.get(f"/api/v1/runs/{org_b['run']}", headers=_auth(token_b))
    assert allowed.status_code == 200


async def test_reviewer_only_sees_shared_runs(client: AsyncClient) -> None:
    seeded = await _seed("reviewer")
    token = await _token(client, seeded["email"])

    hidden = await client.get(f"/api/v1/runs/{seeded['run']}", headers=_auth(token))
    assert hidden.status_code == 403

    async with SessionFactory() as session:
        run = await session.get(Run, seeded["run"])
        assert run is not None
        session.add(
            RunShare(
                run_id=run.id,
                run_created_at=run.created_at,
                user_id=seeded["user"],
                org_id=seeded["org"],
            )
        )
        await session.commit()

    visible = await client.get(f"/api/v1/runs/{seeded['run']}", headers=_auth(token))
    assert visible.status_code == 200
    listing = await client.get("/api/v1/runs", headers=_auth(token))
    assert [item["id"] for item in listing.json()["data"]] == [str(seeded["run"])]

    detail = await client.post(
        f"/api/v1/reports/{seeded['run']}/export?detail=true", headers=_auth(token)
    )
    assert detail.status_code == 403
    assert detail.json()["error"]["code"] == "DETAIL_FORBIDDEN"
    summary = await client.post(
        f"/api/v1/reports/{seeded['run']}/export?detail=false", headers=_auth(token)
    )
    assert summary.status_code == 200


async def test_node_trace_is_forbidden(client: AsyncClient) -> None:
    seeded = await _seed()
    token = await _token(client, seeded["email"])
    response = await client.get(
        f"/api/v1/runs/{seeded['run']}/nodes/3/trace", headers=_auth(token)
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NODE_TRACE_FORBIDDEN"


async def test_optimistic_lock_conflict(client: AsyncClient) -> None:
    seeded = await _seed()
    token = await _token(client, seeded["email"])
    created = await client.post(
        "/api/v1/scenarios",
        headers=_auth(token),
        json={"name": "locked", "spec": {"q": 1.5}},
    )
    assert created.status_code == 201
    scenario_id = created.json()["data"]["id"]

    first = await client.patch(
        f"/api/v1/scenarios/{scenario_id}",
        headers={**_auth(token), "If-Match": '"1"'},
        json={"name": "renamed"},
    )
    assert first.status_code == 200
    assert first.json()["data"]["version"] == 2

    conflict = await client.patch(
        f"/api/v1/scenarios/{scenario_id}",
        headers={**_auth(token), "If-Match": '"1"'},
        json={"name": "again"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "VERSION_CONFLICT"


async def test_idempotency_key_prevents_duplicates(client: AsyncClient) -> None:
    seeded = await _seed()
    token = await _token(client, seeded["email"])
    headers = {**_auth(token), "X-Idempotency-Key": f"key-{uuid.uuid4()}"}
    payload = {"name": "once", "spec": {"q": 1.2}}
    first = await client.post("/api/v1/scenarios", headers=headers, json=payload)
    second = await client.post("/api/v1/scenarios", headers=headers, json=payload)
    assert first.status_code == second.status_code == 201
    assert first.json()["data"]["id"] == second.json()["data"]["id"]

    async with SessionFactory() as session:
        count = await session.scalar(
            select(func.count()).select_from(Scenario).where(Scenario.org_id == seeded["org"])
        )
    assert count == 2  # seeded scenario + the one created here


async def test_audit_log_covers_required_actions(client: AsyncClient) -> None:
    seeded = await _seed()
    token = await _token(client, seeded["email"])

    run = await client.post(
        "/api/v1/runs",
        headers={**_auth(token), "X-Idempotency-Key": f"run-{uuid.uuid4()}"},
        json={"scenario_id": str(seeded["scenario"]), "repeats": 2},
    )
    assert run.status_code == 201
    run_id = run.json()["data"]["id"]

    await client.post(f"/api/v1/reports/{run_id}/export", headers=_auth(token))

    admin = await _seed("org_admin")
    admin_token = await _token(client, admin["email"])
    assert (
        await client.delete(f"/api/v1/datasets/{admin['dataset']}", headers=_auth(admin_token))
    ).status_code == 204
    assert (
        await client.post("/api/v1/admin/settings", headers=_auth(admin_token))
    ).status_code == 200

    async with SessionFactory() as session:
        actions = {
            row.action
            for row in (
                await session.scalars(
                    select(AuditLog).where(AuditLog.org_id.in_([seeded["org"], admin["org"]]))
                )
            ).all()
        }
    assert {"dataset.delete", "run.create", "report.export", "settings.change"} <= actions


def test_rbac_matrix_covers_six_roles_and_all_features() -> None:
    from app.rbac import FEATURES, MATRIX, Scope

    assert set(MATRIX) == {
        "analyst",
        "researcher",
        "scenario_owner",
        "org_admin",
        "reviewer",
        "platform_admin",
    }
    for role, row in MATRIX.items():
        assert set(row) == set(FEATURES), role
    assert MATRIX["reviewer"]["view_runs"] is Scope.SHARED
    assert MATRIX["reviewer"]["export_parquet"] is Scope.DENIED
    assert MATRIX["reviewer"]["export_html"] is Scope.SUMMARY
    assert MATRIX["analyst"]["export_parquet"] is Scope.DENIED
    assert MATRIX["org_admin"]["use_case_review"] is Scope.ORG
