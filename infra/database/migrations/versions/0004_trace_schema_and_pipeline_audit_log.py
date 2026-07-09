"""Move operational tables into the ``trace`` schema and add ``pipeline_audit_log``.

ADR-001 §25 established TRACE as a separate Supabase project with named schemas
(``trace`` for operational tables, ``trace_phi`` for the encrypted PHI store).
This migration performs the rename and adds the pipeline-event audit extension
required by ADR-001 §9 for HIPAA pipeline audit logging.

Tables moved:   ``public`` → ``trace``  (cases, providers, documents,
                chronology_entries, event_nodes, audit_log, record_requests).

Table added:    ``trace.pipeline_audit_log`` — extends audit_log for SYSTEM
                actor pipeline events (OCR start/complete, de-ID, flag
                detection runs, cloud OCR escalation).

Revision ID: 0004_trace_schema_and_pipeline_audit_log
Revises: 0003_record_requests
Create Date: 2026-07-09
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_trace_schema_and_pipeline_audit_log"
down_revision: str | None = "0003_record_requests"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OPERATIONAL_TABLES = [
    "cases",
    "providers",
    "documents",
    "chronology_entries",
    "event_nodes",
    "audit_log",
    "record_requests",
]


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS trace;")

    for table_name in _OPERATIONAL_TABLES:
        op.execute(f"ALTER TABLE public.{table_name} SET SCHEMA trace;")

    op.create_table(
        "pipeline_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("actor_type", sa.String(20), nullable=False, server_default="SYSTEM"),
        sa.Column("metadata_", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="trace",
    )

    op.execute("REVOKE UPDATE, DELETE ON trace.pipeline_audit_log FROM trace_app_role;")
    op.execute("GRANT INSERT ON trace.pipeline_audit_log TO trace_app_role;")

    op.execute("""
        ALTER TABLE trace.pipeline_audit_log ENABLE ROW LEVEL SECURITY;
        ALTER TABLE trace.pipeline_audit_log FORCE ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON trace.pipeline_audit_log USING (
            case_id IN (SELECT case_id FROM trace.cases WHERE
            firm_id = current_setting('app.current_tenant_id', true)::uuid)
        );
    """)


def downgrade() -> None:
    op.drop_table("pipeline_audit_log", schema="trace")

    for table_name in reversed(_OPERATIONAL_TABLES):
        op.execute(f"ALTER TABLE trace.{table_name} SET SCHEMA public;")

    op.execute("DROP SCHEMA IF EXISTS trace;")
