"""compliance: dataset DPIA/consent, use-case approvals, soft delete

Revision ID: 0004
Revises: 0003
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

UPGRADE = [
    "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS dpia JSONB",
    "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
    """
    CREATE TABLE use_case_approvals (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      org_id UUID NOT NULL REFERENCES orgs(id) ON DELETE CASCADE,
      template_key TEXT NOT NULL,
      declaration TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','approved','rejected')),
      requested_by UUID REFERENCES users(id),
      approved_by UUID REFERENCES users(id),
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      decided_at TIMESTAMPTZ,
      UNIQUE (org_id, template_key)
    )
    """,
    "CREATE INDEX idx_use_case_status ON use_case_approvals (status, created_at DESC)",
]

DOWNGRADE = ["DROP TABLE IF EXISTS use_case_approvals",
             "ALTER TABLE datasets DROP COLUMN IF EXISTS deleted_at",
             "ALTER TABLE datasets DROP COLUMN IF EXISTS dpia"]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(sa.text(statement))


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(sa.text(statement))
