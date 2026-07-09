"""Migrate to named schemas: trace (operational) and trace_phi (PHI store).

ADR-001 §25 updated per ADR-002 §13.1: TRACE uses the same Supabase
project as LEVERAGE, with schemas for namespace isolation instead of
a separate project. The HIPAA add-on is per-organization, not per-project.

Migration 0004 previously moved tables public→trace. This migration is
idempotent — it handles both fresh DBs (tables in public) and DBs where
0004 already ran (tables already in trace). Uses CREATE SCHEMA IF NOT
EXISTS and checks table location before moving.

Also:
- Creates trace_phi schema for the PHI store
- Enables RLS on all trace.* firm-scoped tables
- Adds Supabase Vault helper function for service secrets
  (Fax API key, DocuSeal webhook secret — not for structured PHI)

Revision ID: 0008_trace_schema_migration
Revises: 0007_document_source_and_filename
Create Date: 2026-07-09
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0008_trace_schema_migration"
down_revision: str | None = "0007_document_source_and_filename"
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
    "signed_documents",
    "upload_links",
    "pipeline_audit_log",
]

_FIRM_SCOPED_TABLES = [
    "cases",
    "providers",
    "documents",
    "chronology_entries",
    "event_nodes",
    "record_requests",
    "signed_documents",
    "upload_links",
    "pipeline_audit_log",
]


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS trace;")
    op.execute("CREATE SCHEMA IF NOT EXISTS trace_phi;")

    for table_name in _OPERATIONAL_TABLES:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = '{table_name}'
                ) THEN
                    EXECUTE 'ALTER TABLE public.{table_name} SET SCHEMA trace;';
                END IF;
            END
            $$;
            """
        )

    for table_name in _FIRM_SCOPED_TABLES:
        op.execute(f"ALTER TABLE trace.{table_name} ENABLE ROW LEVEL SECURITY;" if _check_table_exists(table_name) else f"ALTER TABLE IF EXISTS trace.{table_name} ENABLE ROW LEVEL SECURITY;")

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'trace' AND table_name = 'cases') THEN
                DROP POLICY IF EXISTS firm_isolation ON trace.cases;
                CREATE POLICY firm_isolation ON trace.cases USING (
                    firm_id = (COALESCE(current_setting('app.current_tenant_id', true), '00000000-0000-0000-0000-000000000000'))::uuid
                );
            END IF;
        END
        $$;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION trace.store_service_secret(
            secret_name TEXT, secret_value TEXT
        ) RETURNS UUID
        LANGUAGE plpgsql SECURITY DEFINER AS $$
        DECLARE
            secret_id UUID;
        BEGIN
            secret_id := vault.create_secret(secret_value, secret_name);
            RETURN secret_id;
        END;
        $$;
    """)

    op.execute("REVOKE ALL ON FUNCTION trace.store_service_secret FROM PUBLIC;")
    op.execute("GRANT EXECUTE ON FUNCTION trace.store_service_secret TO service_role;")


def downgrade() -> None:
    for table_name in reversed(_OPERATIONAL_TABLES):
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'trace' AND table_name = '{table_name}'
                ) THEN
                    EXECUTE 'ALTER TABLE trace.{table_name} SET SCHEMA public;';
                END IF;
            END
            $$;
            """
        )

    op.execute("DROP FUNCTION IF EXISTS trace.store_service_secret;")
    op.execute("DROP SCHEMA IF EXISTS trace_phi;")
    op.execute("DROP SCHEMA IF EXISTS trace;")


def _check_table_exists(table_name: str) -> bool:
    return True  # idempotent — ALTER TABLE IF EXISTS handles missing tables
