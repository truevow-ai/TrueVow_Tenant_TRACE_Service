"""Add signing_sent_at and sol_table_version to cases.

ADR-002 §13.3: signing_sent_at tracks when the DocuSeal package was
sent to the client (used by 24h/48h reminder job). sol_table_version
records which SOL lookup table version was used at case initialization
for attorney deposition traceability.

Revision ID: 0009_add_signing_sent_at_and_sol_version
Revises: 0008_trace_schema_migration
Create Date: 2026-07-09
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_add_signing_sent_at_and_sol_version"
down_revision: str | None = "0008_trace_schema_migration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("signing_sent_at", sa.TIMESTAMP(timezone=True), nullable=True), schema="trace")
    op.add_column("cases", sa.Column("sol_table_version", sa.String(20), nullable=True), schema="trace")


def downgrade() -> None:
    op.drop_column("cases", "sol_table_version", schema="trace")
    op.drop_column("cases", "signing_sent_at", schema="trace")
