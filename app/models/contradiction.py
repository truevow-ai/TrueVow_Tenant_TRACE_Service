"""ContradictionPair — preserved conflicting facts between sources.

When two facts from different sources disagree (e.g., Dr. A says whiplash,
Dr. B says pre-existing degeneration), TRACE preserves both rather than
overwriting one. ContradictionPair records the conflict for attorney review.

Resolution is the attorney's judgment — both may be valid, or one may be
preferred based on the full record.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

CONTRADICTION_TYPES = (
    "DATE_CONFLICT",
    "DIAGNOSIS_CONFLICT",
    "MECHANISM_CONFLICT",
    "PROVIDER_DISAGREEMENT",
    "IMAGING_DISCREPANCY",
    "MEDICATION_CONFLICT",
)

RESOLUTION_STATUSES = (
    "UNRESOLVED",
    "RESOLVED_IN_FAVOR_OF_A",
    "RESOLVED_IN_FAVOR_OF_B",
    "BOTH_VALID",
    "DISMISSED",
)


class ContradictionPair(Base):
    __tablename__ = "contradiction_pairs"

    contradiction_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    fact_a_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("evidence_facts.fact_id", ondelete="CASCADE"), nullable=False)
    fact_b_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("evidence_facts.fact_id", ondelete="CASCADE"), nullable=False)
    contradiction_type: Mapped[str] = mapped_column(String(30), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(30), nullable=False, default="UNRESOLVED")
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attorney_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    fact_a = relationship("EvidenceFact", foreign_keys=[fact_a_id], lazy="selectin")
    fact_b = relationship("EvidenceFact", foreign_keys=[fact_b_id], lazy="selectin")

    __table_args__ = (
        UniqueConstraint("fact_a_id", "fact_b_id", name="uq_contradiction_pair"),
    )
