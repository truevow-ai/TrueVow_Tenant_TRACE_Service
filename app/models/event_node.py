"""Event Node — flagged items in the extended flag registry.

Every chronology entry that triggers a flag (Tier 1 algorithmic,
Tier 2 NLP, or Tier 3 attorney judgment) has a corresponding
EventNode. Provenance metadata enables attorney deposition
traceability.

Matches the Alembic migration schema exactly. Do not modify the
schema without a corresponding migration.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

FLAG_TYPES = (
    "TREATMENT_GAP", "BILLING_DISCREPANCY", "ESCALATION_FLAG",
    "DELAYED_INITIAL_TREATMENT", "SUDDEN_TREATMENT_STOP",
    "FOLLOWUP_NO_RECORD", "NON_COMPLIANT_LANGUAGE",
    "BILL_NO_PROCEDURE_REPORT", "CREDIBILITY_LANGUAGE",
    "NEW_PROVIDER_NO_REFERRAL", "CHANGING_INCIDENT_DESCRIPTION",
    "CHANGING_SYMPTOM_COMPLAINTS", "PRE_EXISTING_CONDITION_SIGNAL",
    "FUNCTIONAL_IMPACT", "IMAGING_CROSS_REFERENCE",
)

FLAG_PRIORITIES = ("PRIORITY", "ADVISORY", "INFORMATIONAL")


class EventNode(Base):
    __tablename__ = "event_nodes"

    node_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False)
    flag_type: Mapped[str] = mapped_column(String(50), nullable=False)
    flag_priority: Mapped[str] = mapped_column(String(15), nullable=False, default="PRIORITY")
    flag_date_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    flag_date_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    gap_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    system_description: Mapped[str] = mapped_column(Text, nullable=False)
    cpt_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    cpt_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cpt_documentation_requirement: Mapped[str | None] = mapped_column(Text, nullable=True)
    clinical_note_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_doc_id_before: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    source_page_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_doc_id_after: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    source_page_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attorney_annotation: Mapped[str | None] = mapped_column(String(50), nullable=True)
    annotation_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    annotation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    annotation_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provenance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    match_confidence: Mapped[str | None] = mapped_column(String(30), nullable=True)

    case = relationship("Case", back_populates="event_nodes")

    __table_args__ = (
        CheckConstraint(
            "flag_type IN (" + ", ".join(f"'{t}'" for t in FLAG_TYPES) + ")",
            name="valid_flag_type",
        ),
        CheckConstraint(
            "flag_priority IN (" + ", ".join(f"'{p}'" for p in FLAG_PRIORITIES) + ")",
            name="valid_flag_priority",
        ),
        CheckConstraint(
            "attorney_annotation IN ("
            "'CONFIRMED_EXPLAINED','CONFIRMED_NEEDS_FOLLOWUP','DISMISSED','RESOLVED') "
            "OR attorney_annotation IS NULL",
            name="valid_annotation",
        ),
    )
