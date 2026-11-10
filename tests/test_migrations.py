"""US-010: schema, partitioning, RLS and cascade behaviour on a real Postgres.

Skipped unless TEST_DATABASE_URL (or DATABASE_URL) points at a disposable
database; CI provides a postgres:16 service.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid

import asyncpg
import pytest

DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="TEST_DATABASE_URL not configured")

TABLES = {
    "orgs",
    "users",
    "memberships",
    "datasets",
    "graph_snapshots",
    "scenarios",
    "runs",
    "run_replicas",
    "artifacts",
    "audit_logs",
}


def _dsn() -> str:
    assert DATABASE_URL is not None
    return DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")


def _alembic(*args: str) -> None:
    env = {**os.environ, "DATABASE_URL": DATABASE_URL or ""}
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="module", autouse=True)
def migrated_schema() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")


async def _connect() -> asyncpg.Connection:
    return await asyncpg.connect(_dsn())


def test_upgrade_creates_every_table_and_partitions() -> None:
    import asyncio

    async def check() -> None:
        conn = await _connect()
        try:
            rows = await conn.fetch(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
            )
            names = {row["table_name"] for row in rows}
            assert names >= TABLES, TABLES - names
            partitions = await conn.fetch(
                "SELECT inhrelid::regclass::text AS name FROM pg_inherits "
                "WHERE inhparent = 'runs'::regclass"
            )
            assert {row["name"] for row in partitions} >= {"runs_2026_11", "runs_default"}
        finally:
            await conn.close()

    asyncio.run(check())


def test_downgrade_is_reversible() -> None:
    _alembic("downgrade", "base")
    _alembic("upgrade", "head")


def test_rls_hides_other_orgs() -> None:
    import asyncio

    async def check() -> None:
        conn = await _connect()
        try:
            async with conn.transaction():
                await conn.execute(
                    "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles "
                    "WHERE rolname='opinionlab_rls_test') THEN "
                    "CREATE ROLE opinionlab_rls_test NOLOGIN; END IF; END $$"
                )
                await conn.execute("GRANT USAGE ON SCHEMA public TO opinionlab_rls_test")
                await conn.execute(
                    "GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO opinionlab_rls_test"
                )
                org_a, org_b = uuid.uuid4(), uuid.uuid4()
                await conn.execute(
                    "INSERT INTO orgs (id, name, region) VALUES ($1,'a','cn'),($2,'b','cn')",
                    org_a,
                    org_b,
                )
                await conn.execute(
                    "INSERT INTO datasets (org_id, name, source_type) VALUES "
                    "($1,'da','upload_csv'),($2,'db','upload_csv')",
                    org_a,
                    org_b,
                )
                await conn.execute("SET ROLE opinionlab_rls_test")
                await conn.execute("SELECT set_config('app.org_id', $1, true)", str(org_a))
                visible = await conn.fetch("SELECT name FROM datasets")
                assert [row["name"] for row in visible] == ["da"]
                await conn.execute("SELECT set_config('app.org_id', $1, true)", str(uuid.uuid4()))
                assert await conn.fetch("SELECT name FROM datasets") == []
        finally:
            await conn.close()

    asyncio.run(check())


def test_foreign_key_cascade_and_restrict() -> None:
    import asyncio

    async def check() -> None:
        conn = await _connect()
        try:
            async with conn.transaction():
                org = uuid.uuid4()
                await conn.execute(
                    "INSERT INTO orgs (id, name, region) VALUES ($1,'c','global')", org
                )
                dataset = await conn.fetchval(
                    "INSERT INTO datasets (org_id, name, source_type) "
                    "VALUES ($1,'x','upload_csv') RETURNING id",
                    org,
                )
                scenario = await conn.fetchval(
                    "INSERT INTO scenarios (org_id, name, spec, dataset_id) "
                    "VALUES ($1,'s','{}'::jsonb,$2) RETURNING id",
                    org,
                    dataset,
                )
                run = await conn.fetchval(
                    "INSERT INTO runs (org_id, scenario_id, run_id_external, spec_sha256, "
                    "manifest, repeats) VALUES ($1,$2,'k','sha','{}'::jsonb,2) RETURNING id",
                    org,
                    scenario,
                )
                await conn.execute(
                    "INSERT INTO run_replicas (run_id, run_created_at, replica_no, seed, status) "
                    "SELECT $1, created_at, 1, 7, 'succeeded' FROM runs WHERE id=$1",
                    run,
                )
                await conn.execute("DELETE FROM datasets WHERE id=$1", dataset)
                assert await conn.fetchval(
                    "SELECT dataset_id FROM scenarios WHERE id=$1", scenario
                ) is None
                with pytest.raises(asyncpg.ForeignKeyViolationError):
                    async with conn.transaction():
                        await conn.execute("DELETE FROM scenarios WHERE id=$1", scenario)
                await conn.execute("DELETE FROM runs WHERE id=$1", run)
                assert await conn.fetchval(
                    "SELECT count(*) FROM run_replicas WHERE run_id=$1", run
                ) == 0
        finally:
            await conn.close()

    asyncio.run(check())
