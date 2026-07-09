"""Add source and original_filename columns to documents table.

ADR-001 §24.4 requires document provenance tracking for deduplication.
- ``source``: where the document came from (PROVIDER_FAX, ATTORNEY_UPLOAD,
  CLIENT_UPLOAD, SCAN, UNKNOWN). Provider fax records are more authoritative
  than client uploads for legal purposes.
- ``original_filename``: the raw filename as received, preserved for audit.
  The object key in storage uses the normalized pattern
  ``{case_id}/{document_id}.{extension}`` — never the original filename
  (which may contain client name or PHI in the filename itself).

Revision ID: 0007_document_source_and_filename
Revises: 0006_docuseal_signing
Create Date: 2026-07-09
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_document_source_and_filename"
down_revision: str | None = "0006_docuseal_signing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("source", sa.String(30), nullable=False, server_default="UNKNOWN"), schema="trace")
    op.add_column("documents", sa.Column("sha256_hash", sa.String(64), nullable=True), schema="trace")
    op.add_column("documents", sa.Column("original_filename", sa.Text(), nullable=True), schema="trace")

    op.create_check_constraint(
        "valid_source",
        "documents",
        "source IN ('PROVIDER_FAX','ATTORNEY_UPLOAD','CLIENT_UPLOAD','SCAN','DOCUSEAL_SIGNED','UNKNOWN')",
        schema="trace",
    )

    op.execute("""
        CREATE INDEX idx_documents_case_hash
        ON trace.documents(case_id, sha256_hash)
        WHERE sha256_hash IS NOT NULL;
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS trace.idx_documents_case_hash;")
    op.drop_constraint("valid_source", "documents", schema="trace")
    op.drop_column("documents", "original_filename", schema="trace")
    op.drop_column("documents", "sha256_hash", schema="trace")
    op.drop_column("documents", "source", schema="trace")
