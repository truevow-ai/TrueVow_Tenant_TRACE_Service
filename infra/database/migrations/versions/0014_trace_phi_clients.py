"""Create trace_phi.clients — PHI store for encrypted client PII.

This is the HIPAA compliance foundation. All PII columns hold
AES-256-GCM ciphertext. The operational database only references
client_token — never the encrypted data itself.

Revision ID: 0014_trace_phi_clients
Revises: 0013_liens_and_billing_tables
Create Date: 2026-07-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014_trace_phi_clients"
down_revision: str | None = "0013_liens_and_billing_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS trace_phi;")

    op.create_table(
        "clients",
        sa.Column("client_token", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encrypted_name", sa.Text(), nullable=True),
        sa.Column("encrypted_dob", sa.Text(), nullable=True),
        sa.Column("encrypted_address", sa.Text(), nullable=True),
        sa.Column("encrypted_phone", sa.Text(), nullable=True),
        sa.Column("encrypted_email", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="trace_phi",
    )

    op.execute("ALTER TABLE trace_phi.clients ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE trace_phi.clients FORCE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY tenant_isolation ON trace_phi.clients USING "
        "(firm_id = COALESCE(current_setting('app.current_tenant_id', true), "
        "'00000000-0000-0000-0000-000000000000')::uuid);"
    )


def downgrade() -> None:
    op.drop_table("clients", schema="trace_phi")
