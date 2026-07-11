"""Create trace.firm_users — Clerk-to-firm identity mapping.

Maps Clerk user IDs to TRACE firm contexts for Row-Level Security
(app.current_tenant_id GUC). One user belongs to exactly one firm.

Revision ID: 0016_firm_users
Revises: 0015_upload_links
Create Date: 2026-07-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_firm_users"
down_revision: str | None = "0015_upload_links"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FIRM_SCOPED_TABLES = ("firm_users",)


def upgrade() -> None:
    op.create_table(
        "firm_users",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("clerk_user_id", sa.String(255), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(30), nullable=False, server_default="ATTORNEY"),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.CheckConstraint("role IN ('ATTORNEY','PARALEGAL','ADMIN')", name="valid_role"),
        schema="trace",
    )
    op.create_index("ix_firm_users_clerk_user_id", "firm_users", ["clerk_user_id"], unique=True, schema="trace")
    op.create_index("ix_firm_users_firm_id", "firm_users", ["firm_id"], schema="trace")

    for table in _FIRM_SCOPED_TABLES:
        op.execute(f"ALTER TABLE trace.{table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE trace.{table} FORCE ROW LEVEL SECURITY;")
        op.execute(
            f"CREATE POLICY tenant_isolation ON trace.{table} USING "
            f"(firm_id = COALESCE(current_setting('app.current_tenant_id', true), "
            f"'00000000-0000-0000-0000-000000000000')::uuid);"
        )


def downgrade() -> None:
    op.drop_table("firm_users", schema="trace")
