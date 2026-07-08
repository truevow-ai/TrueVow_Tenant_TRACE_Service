"""Add provider extraction metadata fields.

Revision ID: 0002_provider_extraction_fields
Revises: 0001_initial_schema
Create Date: 2026-07-08
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_provider_extraction_fields"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("providers", sa.Column("extraction_confidence", sa.String(10), nullable=True))
    op.add_column("providers", sa.Column("source_reference", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("providers", "source_reference")
    op.drop_column("providers", "extraction_confidence")
