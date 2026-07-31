"""MissingEvidenceSignal — expected records that have not been received.

When a fact references a report, referral, or follow-up that should exist
but has no corresponding document in the case, TRACE generates a missing-
evidence signal. This surfaces gaps in the record before the attorney
finalizes the demand.

Signal types:
    MISSING_IMAGING_REPORT — imaging ordered but no report found
    MISSING_PROCEDURE_REPORT — CPT code billed but no op note
    MISSING_FOLLOWUP_RECORD — follow-up recommended but no visit
    MISSING_REFERRAL_RECORD — referral sent but no specialist note
    MISSING_DISCHARGE_SUMMARY — ER/hospital visit without discharge
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

SIGNAL_TYPES = (
    "MISSING_IMAGING_REPORT",
    "MISSING_PROCEDURE_REPORT",
    "MISSING_FOLLOWUP_RECORD",
    "MISSING_REFERRAL_RECORD",
    "MISSING_DISCHARGE_SUMMARY",
    "MISSING_BILLING_RECORD",
)


class MissingEvidenceSignal(Base):
    __tablename__ = "missing_evidence_signals"

    signal_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    signal_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_fact_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("evidence_facts.fact_id", ondelete="SET NULL"), nullable=True)
    expected_record_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expected_from_provider_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("providers.provider_id"), nullable=True)
    expected_date_range_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_date_range_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    days_overdue: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resolved: Mapped[bool] = mapped_column(default=False)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    source_fact = relationship("EvidenceFact", foreign_keys=[source_fact_id], lazy="selectin")
    expected_from_provider = relationship("Provider", lazy="selectin")
