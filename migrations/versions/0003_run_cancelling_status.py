"""add the cancelling intermediate run status

Revision ID: 0003
Revises: 0002
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TABLE runs DROP CONSTRAINT IF EXISTS runs_status_check"))
    op.execute(
        sa.text(
            "ALTER TABLE runs ADD CONSTRAINT runs_status_check CHECK (status IN "
            "('draft','queued','running','cancelling','succeeded','failed','cancelled','partial'))"
        )
    )


def downgrade() -> None:
    # cancelling is not representable in the old constraint; map to cancelled
    op.execute(sa.text("UPDATE runs SET status='cancelled' WHERE status='cancelling'"))
    op.execute(sa.text("ALTER TABLE runs DROP CONSTRAINT IF EXISTS runs_status_check"))
    op.execute(
        sa.text(
            "ALTER TABLE runs ADD CONSTRAINT runs_status_check CHECK (status IN "
            "('draft','queued','running','succeeded','failed','cancelled','partial'))"
        )
    )
