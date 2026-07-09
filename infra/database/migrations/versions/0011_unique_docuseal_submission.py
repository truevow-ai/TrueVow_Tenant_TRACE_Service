"""Add unique constraint on signed_documents.docuseal_submission_id.

ADR-002 §6: replay protection for DocuSeal webhooks. A replayed webhook
carrying the same submission ID must be a no-op, not a duplicate state
advance. The DB-level constraint ensures correctness under concurrent
webhook deliveries — an application-layer check alone has a race condition.

Revision ID: 0011_unique_docuseal_submission
Revises: 0010_rename_approval_attorney_id
Create Date: 2026-07-09
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0011_unique_docuseal_submission"
down_revision: str | None = "0010_rename_approval_attorney_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "unique_docuseal_submission",
        "signed_documents",
        ["docuseal_submission_id"],
        schema="trace",
    )


def downgrade() -> None:
    op.drop_constraint("unique_docuseal_submission", "signed_documents", schema="trace")
