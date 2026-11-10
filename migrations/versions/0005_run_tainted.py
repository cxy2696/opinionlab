"""mark runs produced by a defective engine version

Revision ID: 0005
Revises: 0004
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text("ALTER TABLE runs ADD COLUMN IF NOT EXISTS tainted BOOLEAN NOT NULL DEFAULT FALSE")
    )


def downgrade() -> None:
    op.execute(sa.text("ALTER TABLE runs DROP COLUMN IF EXISTS tainted"))
