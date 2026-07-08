"""Initial TRACE operational schema (Section 3.1).

Creates the operational tables with Postgres-native types (UUID/JSONB/INET/
DATERANGE), the cross-table flag FK, and enables Row-Level Security with
firm-isolation policies keyed on the ``app.current_tenant_id`` GUC.

NOTE: the ``clients`` PHI table lives in a SEPARATE encrypted Postgres instance
(pgcrypto AES-256) and is created by that instance's own migration — it is not
part of the operational database.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-07-08
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FIRM_SCOPED_TABLES = ("cases", "providers", "documents", "chronology_entries", "event_nodes")


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("case_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("client_token", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("intake_record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_date", sa.Date(), nullable=False),
        sa.Column("jurisdiction_state", sa.CHAR(2), nullable=False),
        sa.Column("sol_deadline", sa.Date(), nullable=True),
        sa.Column("sol_urgency", sa.String(10), nullable=True),
        sa.Column("hipaa_auth_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("provider_list_status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("case_stage", sa.String(30), nullable=False, server_default="INITIALIZATION"),
        sa.Column("approval_attorney_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approval_timestamp", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("approval_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.CheckConstraint("hipaa_auth_status IN ('PENDING','SIGNED','EXPIRED')", name="valid_hipaa_status"),
        sa.CheckConstraint("provider_list_status IN ('DRAFT','CONFIRMED','LOCKED')", name="valid_provider_status"),
        sa.CheckConstraint(
            "case_stage IN ('INITIALIZATION','RETRIEVAL','PROCESSING','CHRONOLOGY_READY','ATTORNEY_REVIEW','DEMAND_READY')",
            name="valid_stage",
        ),
        sa.UniqueConstraint("intake_record_id", name="uq_cases_intake_record"),
    )
    op.create_index("ix_cases_firm_id", "cases", ["firm_id"])

    op.create_table(
        "providers",
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("npi_number", sa.String(10), nullable=True),
        sa.Column("provider_name", sa.String(255), nullable=False),
        sa.Column("facility_name", sa.String(255), nullable=True),
        sa.Column("fax_number", sa.String(20), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("specialty", sa.String(100), nullable=True),
        sa.Column("dates_of_service", postgresql.DATERANGE(), nullable=True),
        sa.Column("confirmation_status", sa.String(20), nullable=False, server_default="UNCONFIRMED"),
        sa.Column("confirmed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("confirmed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("retrieval_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("last_request_sent", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("follow_up_count", sa.Integer(), server_default="0"),
        sa.CheckConstraint("confirmation_status IN ('UNCONFIRMED','CONFIRMED','REMOVED')", name="valid_confirmation"),
        sa.CheckConstraint(
            "retrieval_status IN ('PENDING','REQUESTED','PARTIAL','COMPLETE','UNRESPONSIVE')", name="valid_retrieval"
        ),
    )
    op.create_index("ix_providers_case_id", "providers", ["case_id"])

    op.create_table(
        "documents",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("providers.provider_id"), nullable=True),
        sa.Column("s3_bucket", sa.String(255), nullable=False),
        sa.Column("s3_key", sa.String(1024), nullable=False),
        sa.Column("document_type", sa.String(50), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("received_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("ocr_status", sa.String(20), server_default="PENDING"),
        sa.Column("ocr_confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column("is_duplicate", sa.Boolean(), server_default=sa.text("FALSE")),
        sa.Column("is_misfiled", sa.Boolean(), server_default=sa.text("FALSE")),
    )
    op.create_index("ix_documents_case_id", "documents", ["case_id"])

    op.create_table(
        "chronology_entries",
        sa.Column("entry_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_date", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("providers.provider_id"), nullable=True),
        sa.Column("facility_name", sa.String(255), nullable=True),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("clinical_description", sa.Text(), nullable=False),
        sa.Column("source_document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.document_id"), nullable=False),
        sa.Column("source_page_number", sa.Integer(), nullable=False),
        sa.Column("flag_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("attorney_annotation", sa.Text(), nullable=True),
        sa.Column("verify_flag", sa.Boolean(), server_default=sa.text("FALSE")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "event_type IN ('VISIT','IMAGING','PRESCRIPTION','PROCEDURE','DISCHARGE','REFERRAL')",
            name="valid_event_type",
        ),
    )
    op.create_index("ix_chronology_case_id", "chronology_entries", ["case_id"])

    op.create_table(
        "event_nodes",
        sa.Column("node_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("flag_type", sa.String(30), nullable=False),
        sa.Column("flag_date_start", sa.Date(), nullable=True),
        sa.Column("flag_date_end", sa.Date(), nullable=True),
        sa.Column("gap_duration_days", sa.Integer(), nullable=True),
        sa.Column("system_description", sa.Text(), nullable=False),
        sa.Column("cpt_code", sa.String(10), nullable=True),
        sa.Column("cpt_description", sa.Text(), nullable=True),
        sa.Column("cpt_documentation_requirement", sa.Text(), nullable=True),
        sa.Column("clinical_note_summary", sa.Text(), nullable=True),
        sa.Column("source_doc_id_before", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.document_id"), nullable=True),
        sa.Column("source_page_before", sa.Integer(), nullable=True),
        sa.Column("source_doc_id_after", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.document_id"), nullable=True),
        sa.Column("source_page_after", sa.Integer(), nullable=True),
        sa.Column("attorney_annotation", sa.String(50), nullable=True),
        sa.Column("annotation_text", sa.Text(), nullable=True),
        sa.Column("annotation_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("annotation_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "flag_type IN ('TREATMENT_GAP','BILLING_DISCREPANCY','ESCALATION_FLAG')", name="valid_flag_type"
        ),
        sa.CheckConstraint(
            "attorney_annotation IN ('CONFIRMED_EXPLAINED','CONFIRMED_NEEDS_FOLLOWUP','DISMISSED','RESOLVED') "
            "OR attorney_annotation IS NULL",
            name="valid_annotation",
        ),
    )
    op.create_index("ix_event_nodes_case_id", "event_nodes", ["case_id"])

    # Deferred FK: chronology entry -> its flag node.
    op.create_foreign_key(
        "fk_flag_node", "chronology_entries", "event_nodes", ["flag_node_id"], ["node_id"]
    )

    op.create_table(
        "audit_log",
        sa.Column("log_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", sa.String(20), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(64), nullable=True),
        sa.Column("timestamp", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("details", postgresql.JSONB(), nullable=True),
    )

    # Row-Level Security: firm isolation via the app.current_tenant_id GUC.
    for table in _FIRM_SCOPED_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
    # cases isolates directly on firm_id; child tables isolate via their case.
    op.execute(
        "CREATE POLICY tenant_isolation ON cases USING "
        "(firm_id = current_setting('app.current_tenant_id', true)::uuid);"
    )
    for table in ("providers", "documents", "chronology_entries", "event_nodes"):
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} USING "
            f"(case_id IN (SELECT case_id FROM cases WHERE "
            f"firm_id = current_setting('app.current_tenant_id', true)::uuid));"
        )


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_constraint("fk_flag_node", "chronology_entries", type_="foreignkey")
    op.drop_table("event_nodes")
    op.drop_table("chronology_entries")
    op.drop_table("documents")
    op.drop_table("providers")
    op.drop_table("cases")
