"""Add provenance, review_status, quality_flags, and related columns.

ADR-001 §11: ``provenance`` JSONB on event_nodes — every flag carries
rule_name, rule_version, detection_method, model info, and confidence.

ADR-001 §24.5: ``review_status`` on chronology_entries — UNREVIEWED,
CONFIRMED, EDITED, DISMISSED, NEEDS_MORE_RECORDS.

ADR-001 §24.4: ``quality_flags`` JSONB array on documents — zero or more
transparency indicators from deepdoctection output.

ADR-001 §24.7: ``match_confidence`` on billing-discrepancy event_nodes.

ADR-001 §7.4: ``review_status`` on cases — tracks attorney sign-off.

All tables in the ``trace`` schema (ADR-001 §25).

Revision ID: 0005_extended_flags_and_review_columns
Revises: 0004_trace_schema_and_pipeline_audit_log
Create Date: 2026-07-09
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_extended_flags_and_review_columns"
down_revision: str | None = "0004_trace_schema_and_pipeline_audit_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("event_nodes", sa.Column("provenance", postgresql.JSONB(), nullable=True), schema="trace")

    op.add_column(
        "chronology_entries",
        sa.Column("review_status", sa.String(30), nullable=False, server_default="UNREVIEWED"),
        schema="trace",
    )

    op.add_column("documents", sa.Column("quality_flags", postgresql.JSONB(), nullable=True), schema="trace")

    op.add_column(
        "event_nodes",
        sa.Column("match_confidence", sa.String(30), nullable=True),
        schema="trace",
    )

    op.add_column(
        "cases",
        sa.Column("review_status", sa.String(30), nullable=False, server_default="PENDING"),
        schema="trace",
    )

    op.create_check_constraint(
        "valid_review_status",
        "chronology_entries",
        "review_status IN ('UNREVIEWED','CONFIRMED','EDITED','DISMISSED','NEEDS_MORE_RECORDS')",
        schema="trace",
    )

    op.create_check_constraint(
        "valid_match_confidence",
        "event_nodes",
        "match_confidence IN ('STRONG_MATCH','LIKELY_MATCH','POSSIBLE_MATCH',"
        "'NO_MATCHING_TREATMENT_NOTE','TREATMENT_NOTE_WITH_NO_BILL','NEEDS_REVIEW')",
        schema="trace",
    )

    op.create_check_constraint(
        "valid_case_review_status",
        "cases",
        "review_status IN ('PENDING','REVIEWING','READY','SIGNED_OFF')",
        schema="trace",
    )


def downgrade() -> None:
    op.drop_constraint("valid_case_review_status", "cases", schema="trace")
    op.drop_constraint("valid_match_confidence", "event_nodes", schema="trace")
    op.drop_constraint("valid_review_status", "chronology_entries", schema="trace")

    op.drop_column("cases", "review_status", schema="trace")
    op.drop_column("event_nodes", "match_confidence", schema="trace")
    op.drop_column("documents", "quality_flags", schema="trace")
    op.drop_column("chronology_entries", "review_status", schema="trace")
    op.drop_column("event_nodes", "provenance", schema="trace")
