"""Rename approval_attorney_id → approved_by on cases table.

Law firm operations involve attorneys AND staff (paralegals, assistants).
The field should track WHO approved — not assume it's always the attorney.
The audit_log.actor_type preserves the distinction (ATTORNEY/STAFF).

Revision ID: 0010_rename_approval_attorney_id
Revises: 0009_add_signing_sent_at_and_sol_version
Create Date: 2026-07-09
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0010_rename_approval_attorney_id"
down_revision: str | None = "0009_add_signing_sent_at_and_sol_version"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("cases", "approval_attorney_id", new_column_name="approved_by", schema="trace")


def downgrade() -> None:
    op.alter_column("cases", "approved_by", new_column_name="approval_attorney_id", schema="trace")
