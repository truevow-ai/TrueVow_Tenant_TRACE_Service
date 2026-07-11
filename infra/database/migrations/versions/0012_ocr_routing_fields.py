"""Add OCR routing fields to documents table.

ADR-003 §12: schema prep for Phase 1D OCR pipeline. All fields nullable —
populated when Phase 1D builds the document processing pipeline.
Adding now avoids a retroactive migration that touches every existing
document record.

Fields:
- document_type_guess: deepdoctection/Docling classification result
- page_type_guess: per-page classification (typed/handwritten/mixed)
- ocr_route: which OCR backend should process this document
- ocr_backend: which backend actually processed it
- needs_escalation: whether Tier 2 cloud OCR is needed
- source_spans_available: whether OpenMed 1.7.x source spans are present

Revision ID: 0012_ocr_routing_fields
Revises: 0011_unique_docuseal_submission
Create Date: 2026-07-09
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_ocr_routing_fields"
down_revision: str | None = "0011_unique_docuseal_submission"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("document_type_guess", sa.String(30), nullable=True), schema="trace")
    op.add_column("documents", sa.Column("page_type_guess", sa.Text(), nullable=True), schema="trace")
    op.add_column("documents", sa.Column("ocr_route", sa.String(30), nullable=True), schema="trace")
    op.add_column("documents", sa.Column("ocr_backend", sa.String(30), nullable=True), schema="trace")
    op.add_column("documents", sa.Column("needs_escalation", sa.Boolean(), server_default=sa.text("FALSE")), schema="trace")
    op.add_column("documents", sa.Column("source_spans_available", sa.Boolean(), server_default=sa.text("FALSE")), schema="trace")


def downgrade() -> None:
    op.drop_column("documents", "source_spans_available", schema="trace")
    op.drop_column("documents", "needs_escalation", schema="trace")
    op.drop_column("documents", "ocr_backend", schema="trace")
    op.drop_column("documents", "ocr_route", schema="trace")
    op.drop_column("documents", "page_type_guess", schema="trace")
    op.drop_column("documents", "document_type_guess", schema="trace")
