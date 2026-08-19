"""FND-001A-R1 (blocker 2): enforce the event_nodes.flag_priority ORM contract.

Migration 0020 added the column nullable with a server default; the
authoritative ORM contract is:

    flag_priority: nullable=False, Python default "PRIORITY",
    values limited to PRIORITY / ADVISORY / INFORMATIONAL
    (check constraint valid_flag_priority).

This forward migration aligns the physical schema: backfill NULLs, set
NOT NULL, drop the server default (the ORM supplies the Python-side default),
and add the three-value check constraint. 0020 itself is not rewritten —
it is already applied to the designated Supabase project.

Revision ID: 0021_flag_priority_guard
Revises: 0020_event_node_flag_priority
Create Date: 2026-08-19
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0021_flag_priority_guard"
down_revision: str | None = "0020_event_node_flag_priority"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINT_NAME = "valid_flag_priority"


def upgrade() -> None:
    op.execute(
        "UPDATE trace.event_nodes SET flag_priority = 'PRIORITY' "
        "WHERE flag_priority IS NULL;"
    )
    op.execute(
        "ALTER TABLE trace.event_nodes ALTER COLUMN flag_priority SET NOT NULL;"
    )
    op.execute(
        "ALTER TABLE trace.event_nodes ALTER COLUMN flag_priority DROP DEFAULT;"
    )
    op.create_check_constraint(
        _CONSTRAINT_NAME,
        "event_nodes",
        "flag_priority IN ('PRIORITY','ADVISORY','INFORMATIONAL')",
        schema="trace",
    )


def downgrade() -> None:
    op.drop_constraint(_CONSTRAINT_NAME, "event_nodes", schema="trace")
    op.execute(
        "ALTER TABLE trace.event_nodes ALTER COLUMN flag_priority DROP NOT NULL;"
    )
    op.execute(
        "ALTER TABLE trace.event_nodes "
        "ALTER COLUMN flag_priority SET DEFAULT 'PRIORITY';"
    )
