"""Add DocuSeal signing fields and signed_documents table.

ADR-001 §23: DocuSeal self-hosted e-signature gateway. Case initialization
is now gated behind client signing. case_stage starts at PENDING_SIGNATURE
(the new default, replacing INITIALIZATION). hipaa_auth_status gains the
SENT state for tracking signing-link delivery.

New table signed_documents tracks each signing package submission with
embedded DocuSeal audit trail (signer identity, IP, timestamp, method).

Revision ID: 0006_docuseal_signing
Revises: 0005_extended_flags_and_review_columns
Create Date: 2026-07-09
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_docuseal_signing"
down_revision: str | None = "0005_extended_flags_and_review_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FIRM_SCOPED_TABLES = ("signed_documents",)


def upgrade() -> None:
    op.add_column("cases", sa.Column("docuseal_submission_id", sa.String(255), nullable=True), schema="trace")
    op.add_column("cases", sa.Column("signing_completed_at", sa.TIMESTAMP(timezone=True), nullable=True), schema="trace")

    op.drop_constraint("valid_hipaa_status", "cases", schema="trace")
    op.create_check_constraint(
        "valid_hipaa_status",
        "cases",
        "hipaa_auth_status IN ('PENDING','SENT','SIGNED','EXPIRED')",
        schema="trace",
    )

    op.drop_constraint("valid_stage", "cases", schema="trace")
    op.alter_column("cases", "case_stage", server_default="PENDING_SIGNATURE", schema="trace")
    op.create_check_constraint(
        "valid_stage",
        "cases",
        "case_stage IN ('PENDING_SIGNATURE','INITIALIZATION','RETRIEVAL','PROCESSING',"
        "'CHRONOLOGY_READY','ATTORNEY_REVIEW','DEMAND_READY')",
        schema="trace",
    )

    op.create_table(
        "signed_documents",
        sa.Column("signing_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trace.cases.case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("docuseal_submission_id", sa.String(255), nullable=False),
        sa.Column("document_type", sa.String(30), nullable=False),
        sa.Column("signing_status", sa.String(20), nullable=False, server_default="SENT"),
        sa.Column("client_signed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("attorney_template_applied_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("signed_pdf_storage_key", sa.String(1024), nullable=True),
        sa.Column("docuseal_audit_trail", postgresql.JSONB(), nullable=True),
        sa.Column("reminder_sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="trace",
    )
    op.create_index("ix_signed_documents_case_id", "signed_documents", ["case_id"], schema="trace")
    op.create_index("ix_signed_documents_firm_id", "signed_documents", ["firm_id"], schema="trace")

    for table in _FIRM_SCOPED_TABLES:
        op.execute(f"ALTER TABLE trace.{table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE trace.{table} FORCE ROW LEVEL SECURITY;")
        op.execute(
            f"CREATE POLICY tenant_isolation ON trace.{table} USING "
            f"(case_id IN (SELECT case_id FROM trace.cases WHERE "
            f"firm_id = current_setting('app.current_tenant_id', true)::uuid));"
        )


def downgrade() -> None:
    op.drop_table("signed_documents", schema="trace")

    op.drop_constraint("valid_stage", "cases", schema="trace")
    op.alter_column("cases", "case_stage", server_default="INITIALIZATION", schema="trace")
    op.create_check_constraint(
        "valid_stage",
        "cases",
        "case_stage IN ('INITIALIZATION','RETRIEVAL','PROCESSING',"
        "'CHRONOLOGY_READY','ATTORNEY_REVIEW','DEMAND_READY')",
        schema="trace",
    )

    op.drop_constraint("valid_hipaa_status", "cases", schema="trace")
    op.create_check_constraint(
        "valid_hipaa_status",
        "cases",
        "hipaa_auth_status IN ('PENDING','SIGNED','EXPIRED')",
        schema="trace",
    )

    op.drop_column("cases", "signing_completed_at", schema="trace")
    op.drop_column("cases", "docuseal_submission_id", schema="trace")
