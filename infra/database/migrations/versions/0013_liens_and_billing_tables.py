"""Add Liens and MedicalBillLine tables.

ADR-004 §3: trace.liens — attorney-managed lien tracking.
ADR-004 §5: trace.medical_bill_line — billing reconciliation data.

Revision ID: 0013_liens_and_billing_tables
Revises: 0012_ocr_routing_fields
Create Date: 2026-07-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_liens_and_billing_tables"
down_revision: str | None = "0012_ocr_routing_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.create_table(
        "liens",
        sa.Column("lien_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trace.cases.case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lien_type", sa.String(30), nullable=False),
        sa.Column("lienholder", sa.Text(), nullable=True),
        sa.Column("claimed_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="NOT_CHECKED"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="trace",
    )
    op.create_index("ix_liens_case_id", "liens", ["case_id"], schema="trace")
    op.create_index("ix_liens_firm_id", "liens", ["firm_id"], schema="trace")

    op.create_table(
        "medical_bill_line",
        sa.Column("bill_line_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trace.cases.case_id", ondelete="CASCADE"), nullable=False),
        sa.Column("firm_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trace.documents.document_id"), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("trace.providers.provider_id"), nullable=True),
        sa.Column("date_of_service", sa.Date(), nullable=True),
        sa.Column("cpt_code", sa.String(10), nullable=True),
        sa.Column("icd10_codes", sa.Text(), nullable=True),
        sa.Column("billed_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("match_confidence", sa.String(30), nullable=True),
        sa.Column("matched_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("needs_review", sa.Boolean(), server_default=sa.text("FALSE")),
        sa.Column("attorney_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()")),
        schema="trace",
    )
    op.create_index("ix_bill_line_case_id", "medical_bill_line", ["case_id"], schema="trace")
    op.create_index("ix_bill_line_firm_id", "medical_bill_line", ["firm_id"], schema="trace")

def downgrade() -> None:
    op.drop_table("medical_bill_line", schema="trace")
    op.drop_table("liens", schema="trace")
