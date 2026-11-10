"""initial schema: orgs/users/datasets/scenarios/runs/artifacts/audit

Revision ID: 0001
Revises:
Create Date: 2026-11-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

UPGRADE: list[str] = [
    "CREATE EXTENSION IF NOT EXISTS citext",
    """
    CREATE TABLE orgs (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      name TEXT NOT NULL,
      region TEXT NOT NULL CHECK (region IN ('cn','global')),
      deployment TEXT NOT NULL DEFAULT 'saas' CHECK (deployment IN ('saas','private')),
      quota_concurrent_jobs INT NOT NULL DEFAULT 4,
      data_retention_days INT NOT NULL DEFAULT 180,
      use_case_declaration TEXT,
      status TEXT NOT NULL DEFAULT 'active',
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE users (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      email CITEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      display_name TEXT NOT NULL,
      is_active BOOLEAN NOT NULL DEFAULT TRUE,
      must_change_pw BOOLEAN NOT NULL DEFAULT TRUE,
      failed_login_count INT NOT NULL DEFAULT 0,
      locked_until TIMESTAMPTZ,
      last_login_at TIMESTAMPTZ,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE memberships (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
      user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
      role TEXT NOT NULL CHECK (role IN
        ('platform_admin','org_admin','scenario_owner','researcher','analyst','reviewer')),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (org_id, user_id)
    )
    """,
    """
    CREATE TABLE datasets (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
      name TEXT NOT NULL,
      source_type TEXT NOT NULL CHECK (source_type IN
        ('upload_csv','upload_parquet','upload_json','connector_weibo_topic',
         'connector_douyin_topic','connector_x_hashtag','connector_discord','connector_gdelt')),
      pseudonym_algo TEXT NOT NULL DEFAULT 'hmac-sha256',
      row_count INT,
      node_count INT,
      edge_count INT,
      stats JSONB,
      consent_basis TEXT,
      expires_at TIMESTAMPTZ,
      created_by UUID REFERENCES users(id),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE graph_snapshots (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      dataset_id UUID NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
      graph_sha256 TEXT NOT NULL,
      nnz INT NOT NULL,
      storage_ref TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (dataset_id, graph_sha256)
    )
    """,
    """
    CREATE TABLE scenarios (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
      template_key TEXT,
      name TEXT NOT NULL,
      description TEXT,
      spec JSONB NOT NULL,
      dataset_id UUID REFERENCES datasets(id) ON DELETE SET NULL,
      visibility TEXT NOT NULL DEFAULT 'org' CHECK (visibility IN
        ('org','private','published_template')),
      version INT NOT NULL DEFAULT 1,
      is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
      created_by UUID REFERENCES users(id),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # runs/run_replicas are range-partitioned by created_at (PRD 6.3 / 6.5).
    # Partitioned uniqueness must include the partition key, so the external
    # run key is unique per (org_id, run_id_external, created_at).
    """
    CREATE TABLE runs (
      id UUID NOT NULL DEFAULT gen_random_uuid(),
      org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
      scenario_id UUID NOT NULL REFERENCES scenarios(id) ON DELETE RESTRICT,
      run_id_external TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN
        ('draft','queued','running','succeeded','failed','cancelled','partial')),
      spec_sha256 TEXT NOT NULL,
      manifest JSONB NOT NULL,
      repeats INT NOT NULL,
      done_replicas INT NOT NULL DEFAULT 0,
      aggregate JSONB,
      disclaimer_key TEXT NOT NULL DEFAULT 'simulation_not_prediction',
      error_code TEXT,
      queued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      started_at TIMESTAMPTZ,
      finished_at TIMESTAMPTZ,
      created_by UUID REFERENCES users(id),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY (id, created_at),
      UNIQUE (org_id, run_id_external, created_at)
    ) PARTITION BY RANGE (created_at)
    """,
    """
    CREATE TABLE run_replicas (
      run_id UUID NOT NULL,
      run_created_at TIMESTAMPTZ NOT NULL,
      replica_no INT NOT NULL,
      seed BIGINT NOT NULL,
      status TEXT NOT NULL,
      metrics JSONB,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY (run_id, replica_no, created_at),
      FOREIGN KEY (run_id, run_created_at) REFERENCES runs (id, created_at) ON DELETE CASCADE
    ) PARTITION BY RANGE (created_at)
    """,
    """
    CREATE TABLE artifacts (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      run_id UUID NOT NULL,
      run_created_at TIMESTAMPTZ NOT NULL,
      kind TEXT NOT NULL CHECK (kind IN
        ('report_html','metrics_parquet','series_csv','figure_png','manifest_json')),
      storage_ref TEXT NOT NULL,
      sha256 TEXT NOT NULL,
      size_bytes INT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (run_id, kind, sha256),
      FOREIGN KEY (run_id, run_created_at) REFERENCES runs (id, created_at) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE audit_logs (
      id BIGSERIAL PRIMARY KEY,
      org_id UUID,
      user_id UUID,
      action TEXT NOT NULL,
      target TEXT NOT NULL,
      detail JSONB,
      ip INET,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # monthly partitions + a default catch-all so inserts never fail
    "CREATE TABLE runs_2026_11 PARTITION OF runs FOR VALUES FROM ('2026-11-01') TO ('2026-12-01')",
    "CREATE TABLE runs_2026_12 PARTITION OF runs FOR VALUES FROM ('2026-12-01') TO ('2027-01-01')",
    "CREATE TABLE runs_default PARTITION OF runs DEFAULT",
    "CREATE TABLE run_replicas_2026_11 PARTITION OF run_replicas "
    "FOR VALUES FROM ('2026-11-01') TO ('2026-12-01')",
    "CREATE TABLE run_replicas_2026_12 PARTITION OF run_replicas "
    "FOR VALUES FROM ('2026-12-01') TO ('2027-01-01')",
    "CREATE TABLE run_replicas_default PARTITION OF run_replicas DEFAULT",
    # indexes (PRD 6.3)
    "CREATE INDEX idx_runs_org_status ON runs (org_id, status, queued_at DESC)",
    "CREATE INDEX idx_runs_scenario ON runs (scenario_id, queued_at DESC)",
    "CREATE INDEX idx_scenarios_org ON scenarios (org_id, updated_at DESC)",
    "CREATE INDEX idx_audit_org_time ON audit_logs (org_id, created_at DESC)",
    "CREATE INDEX idx_datasets_org ON datasets (org_id, created_at DESC)",
    "CREATE INDEX idx_specs_jsonb_q ON scenarios USING gin ((spec->'q'))",
    "CREATE INDEX idx_scenarios_active ON scenarios (org_id, is_deleted)",
    # row-level security: cross-org reads must return zero rows
    "ALTER TABLE datasets ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE datasets FORCE ROW LEVEL SECURITY",
    "CREATE POLICY org_isolation_datasets ON datasets USING "
    "(org_id = current_setting('app.org_id', true)::uuid) "
    "WITH CHECK (org_id = current_setting('app.org_id', true)::uuid)",
    "ALTER TABLE scenarios ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE scenarios FORCE ROW LEVEL SECURITY",
    "CREATE POLICY org_isolation_scenarios ON scenarios USING "
    "(org_id = current_setting('app.org_id', true)::uuid) "
    "WITH CHECK (org_id = current_setting('app.org_id', true)::uuid)",
    "ALTER TABLE runs ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE runs FORCE ROW LEVEL SECURITY",
    "CREATE POLICY org_isolation_runs ON runs USING "
    "(org_id = current_setting('app.org_id', true)::uuid) "
    "WITH CHECK (org_id = current_setting('app.org_id', true)::uuid)",
    "ALTER TABLE memberships ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE memberships FORCE ROW LEVEL SECURITY",
    "CREATE POLICY org_isolation_memberships ON memberships USING "
    "(org_id = current_setting('app.org_id', true)::uuid) "
    "WITH CHECK (org_id = current_setting('app.org_id', true)::uuid)",
    "ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE audit_logs FORCE ROW LEVEL SECURITY",
    "CREATE POLICY org_isolation_audit_logs ON audit_logs USING "
    "(org_id IS NULL OR org_id = current_setting('app.org_id', true)::uuid)",
    "ALTER TABLE graph_snapshots ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE graph_snapshots FORCE ROW LEVEL SECURITY",
    "CREATE POLICY org_isolation_graph_snapshots ON graph_snapshots USING "
    "(EXISTS (SELECT 1 FROM datasets d WHERE d.id = dataset_id "
    "AND d.org_id = current_setting('app.org_id', true)::uuid))",
    "ALTER TABLE run_replicas ENABLE ROW LEVEL SECURITY",
    "ALTER TABLE run_replicas FORCE ROW LEVEL SECURITY",
    "CREATE POLICY org_isolation_run_replicas ON run_replicas USING "
    "(EXISTS (SELECT 1 FROM runs r WHERE r.id = run_id "
    "AND r.org_id = current_setting('app.org_id', true)::uuid))",
]

DOWNGRADE: list[str] = [
    "DROP TABLE IF EXISTS run_replicas",
    "DROP TABLE IF EXISTS artifacts",
    "DROP TABLE IF EXISTS runs",
    "DROP TABLE IF EXISTS audit_logs",
    "DROP TABLE IF EXISTS scenarios",
    "DROP TABLE IF EXISTS graph_snapshots",
    "DROP TABLE IF EXISTS datasets",
    "DROP TABLE IF EXISTS memberships",
    "DROP TABLE IF EXISTS users",
    "DROP TABLE IF EXISTS orgs",
]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(sa.text(statement))


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(sa.text(statement))
