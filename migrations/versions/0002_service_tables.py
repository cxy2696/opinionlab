"""auth refresh rotation, idempotency keys and run sharing

Revision ID: 0002
Revises: 0001
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

UPGRADE = [
    """
    CREATE TABLE refresh_tokens (
      jti UUID PRIMARY KEY,
      user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      org_id UUID NOT NULL,
      expires_at TIMESTAMPTZ NOT NULL,
      revoked BOOLEAN NOT NULL DEFAULT FALSE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX idx_refresh_user ON refresh_tokens (user_id, expires_at DESC)",
    """
    CREATE TABLE idempotency_keys (
      id UUID PRIMARY KEY,
      org_id UUID NOT NULL,
      key TEXT NOT NULL,
      method TEXT NOT NULL,
      path TEXT NOT NULL,
      status_code INT NOT NULL,
      response JSONB NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (org_id, key, method, path)
    )
    """,
    """
    CREATE TABLE run_shares (
      run_id UUID NOT NULL,
      run_created_at TIMESTAMPTZ NOT NULL,
      user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      org_id UUID NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      PRIMARY KEY (run_id, user_id),
      FOREIGN KEY (run_id, run_created_at) REFERENCES runs (id, created_at) ON DELETE CASCADE
    )
    """,
    "CREATE INDEX idx_run_shares_user ON run_shares (user_id, org_id)",
]

DOWNGRADE = ["DROP TABLE IF EXISTS run_shares", "DROP TABLE IF EXISTS idempotency_keys",
             "DROP TABLE IF EXISTS refresh_tokens"]


def upgrade() -> None:
    for statement in UPGRADE:
        op.execute(sa.text(statement))


def downgrade() -> None:
    for statement in DOWNGRADE:
        op.execute(sa.text(statement))
