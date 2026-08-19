"""FND-001A (root 3): add event_nodes.flag_priority.

Discovered during the baseline reconciliation run: the EventNode model maps
``flag_priority`` (used by the QA demand-ready gate), but no historical
migration ever created the column — on either the fresh chain or the
designated Supabase project. Existing rows receive the server default
PRIORITY.

Revision ID: 0020_event_node_flag_priority
Revises: 0019_baseline_reconcile
Create Date: 2026-08-19
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_event_node_flag_priority"
down_revision: str | None = "0019_baseline_reconcile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "event_nodes",
        sa.Column("flag_priority", sa.String(15), nullable=True, server_default="PRIORITY"),
        schema="trace",
    )


def downgrade() -> None:
    op.drop_column("event_nodes", "flag_priority", schema="trace")
