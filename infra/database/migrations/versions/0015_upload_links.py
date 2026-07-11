"""Create trace.upload_links — tokenized client-facing upload pages.

ADR-003 §7: token-scoped upload links with no authentication.
Expiry and revocation enforced server-side. Token never logged.

Revision ID: 0015_upload_links
Revises: 0014_trace_phi_clients
Create Date: 2026-07-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0015_upload_links"
down_revision: str | None = "0014_trace_phi_clients"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FIRM_SCOPED_TABLES = ("upload_links",)


def upgrade() -> None:
    op.create_table(
        "upload_links",
        sa.Column("token", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trace.cases.case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("upload_count", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="trace",
    )

    for table in _FIRM_SCOPED_TABLES:
        op.execute(f"ALTER TABLE trace.{table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE trace.{table} FORCE ROW LEVEL SECURITY;")
        op.execute(
            f"CREATE POLICY tenant_isolation ON trace.{table} USING "
            f"(firm_id = COALESCE(current_setting('app.current_tenant_id', true), "
            f"'00000000-0000-0000-0000-000000000000')::uuid);"
        )


def downgrade() -> None:
    op.drop_table("upload_links", schema="trace")
