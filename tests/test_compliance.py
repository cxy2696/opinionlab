"""region isolation, G5 approval, deletion cascade and report red lines."""

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
    Artifact,
    Dataset,
    GraphSnapshot,
    Membership,
    Org,
    Run,
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


@pytest.fixture(scope="module", autouse=True)
def schema() -> None:
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).parents[1],
        env={**os.environ, "DATABASE_URL": DATABASE_URL or ""},
        check=True,
        capture_output=True,
    )


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as http:
        yield http


async def _seed(role: str = "org_admin", region: str = "cn") -> dict[str, Any]:
    suffix = uuid.uuid4().hex[:8]
    async with SessionFactory() as session:
        org = Org(name=f"org-{suffix}", region=region)
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
            org_id=org.id, name="s", spec={"q": 1.5}, dataset_id=dataset.id, created_by=user.id
        )
        session.add(scenario)
        await session.flush()
        run = Run(
            org_id=org.id,
            scenario_id=scenario.id,
            run_id_external=f"r-{suffix}",
            spec_sha256="sha",
            manifest={},
            repeats=1,
            created_by=user.id,
            created_at=utcnow(),
        )
        session.add(run)
        await session.flush()
        session.add(
            Artifact(
                run_id=run.id,
                run_created_at=run.created_at,
                kind="series_csv",
                storage_ref="s3://bucket/series.csv",
                sha256="abc",
                size_bytes=10,
            )
        )
        session.add(
            GraphSnapshot(
                dataset_id=dataset.id, graph_sha256="g", nnz=10, storage_ref="s3://bucket/g"
            )
        )
        await session.commit()
        return {
            "org": org.id,
            "user": user.id,
            "email": user.email,
            "dataset": dataset.id,
            "scenario": scenario.id,
            "run": run.id,
        }


async def _token(client: AsyncClient, email: str) -> str:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return str(response.json()["access_token"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_cross_region_access_returns_403(client: AsyncClient) -> None:
    seeded = await _seed(region="global")  # deployment default REGION=cn
    token = await _token(client, seeded["email"])
    response = await client.get("/api/v1/orgs/me", headers=_auth(token))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "REGION_MISMATCH"


async def test_g5_template_requires_use_case_approval(client: AsyncClient) -> None:
    seeded = await _seed("org_admin")
    token = await _token(client, seeded["email"])

    blocked = await client.post("/api/v1/templates/G5/clone", headers=_auth(token))
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "USE_CASE_NOT_APPROVED"

    requested = await client.post(
        "/api/v1/orgs/use-case",
        headers=_auth(token),
        json={"template_key": "G5", "declaration": "academic election-dynamics study only"},
    )
    assert requested.status_code == 201
    approval_id = requested.json()["data"]["approval_id"]

    platform = await _seed("platform_admin")
    platform_token = await _token(client, platform["email"])
    approved = await client.post(
        f"/api/v1/platform/use-cases/{approval_id}/approve", headers=_auth(platform_token)
    )
    assert approved.status_code == 200

    cloned = await client.post("/api/v1/templates/G5/clone", headers=_auth(token))
    assert cloned.status_code == 201
    assert cloned.json()["data"]["template_key"] == "G5"


async def test_dataset_deletion_cascades_artifacts_and_snapshots(client: AsyncClient) -> None:
    seeded = await _seed("org_admin")
    token = await _token(client, seeded["email"])
    response = await client.delete(
        f"/api/v1/datasets/{seeded['dataset']}", headers=_auth(token)
    )
    assert response.status_code == 204

    async with SessionFactory() as session:
        artifacts = await session.scalar(
            select(func.count()).select_from(Artifact).where(Artifact.run_id == seeded["run"])
        )
        snapshots = await session.scalar(
            select(func.count()).select_from(GraphSnapshot).where(
                GraphSnapshot.dataset_id == seeded["dataset"]
            )
        )
        scenario = await session.get(Scenario, seeded["scenario"])
    assert artifacts == 0
    assert snapshots == 0
    assert scenario is not None and scenario.dataset_id is None


def test_docs_cover_model_card_and_compliance() -> None:
    root = Path(__file__).parents[1]
    model_card = (root / "docs" / "MODEL_CARD.md").read_text(encoding="utf-8")
    compliance = (root / "docs" / "COMPLIANCE.md").read_text(encoding="utf-8")
    assert "Prohibited uses" in model_card
    assert "retention" in compliance.lower()
    assert "NODE_TRACE_FORBIDDEN" in compliance
    assert "does not call generative models" in model_card


def test_report_has_ai_label_and_no_node_traces(tmp_path: Path) -> None:
    from hnle.core.sparse import run_sparse
    from hnle.graph import random_hypergraph
    from hnle.io.export import export_run
    from hnle.spec import ModelSpec

    spec = ModelSpec(n_steps=5, seed=1)
    graph = random_hypergraph(20, 30, __import__("numpy").random.default_rng(1), spec.hyperedge)
    result = run_sparse(spec, graph, seed=1)
    paths = export_run(spec, graph, result, tmp_path)
    html = paths["report"].read_text(encoding="utf-8")
    assert "确定性仿真引擎" in html
    assert "deterministic simulation engine" in html
    assert "node_trace" not in html.lower()
