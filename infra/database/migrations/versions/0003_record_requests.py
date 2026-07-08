"""Add record_requests table (fax transmission tracking).

Revision ID: 0003_record_requests
Revises: 0002_provider_extraction_fields
Create Date: 2026-07-08
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_record_requests"
down_revision: str | None = "0002_provider_extraction_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "record_requests",
        sa.Column("request_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("providers.provider_id"), nullable=False),
        sa.Column("fax_number", sa.String(20), nullable=False),
        sa.Column("fax_transmission_id", sa.String(128), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("transmitted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("cover_sheet_ref", sa.String(512), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
    )
    op.create_index("ix_record_requests_case_id", "record_requests", ["case_id"])

    # RLS: record_requests is firm-scoped via the case.
    op.execute(
        "CREATE POLICY tenant_isolation ON record_requests USING "
        "(case_id IN (SELECT case_id FROM cases WHERE "
        "firm_id = current_setting('app.current_tenant_id', true)::uuid));"
    )


def downgrade() -> None:
    op.drop_table("record_requests")
