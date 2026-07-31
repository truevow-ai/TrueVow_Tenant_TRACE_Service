"""EvidenceFact — every derived clinical assertion with full provenance.

This is the core atomic unit of TRACE. Every fact extracted from medical
records retains:
- Source document and page (via SourceLocation)
- Extraction method and confidence
- Review status (UNREVIEWED → CONFIRMED / DISPUTED / EXCLUDED)
- Version chain (when a fact is edited, the previous version is linked)
- Contradiction flag (set by the contradiction engine)
- Duplicate detection (duplicate_of_fact_id)

Nothing in TRACE claims a fact without a source location. All generated
summaries are assembled from these source-linked facts.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

FACT_TYPES = (
    "VISIT", "IMAGING", "PRESCRIPTION", "PROCEDURE", "DIAGNOSIS",
    "DISCHARGE", "REFERRAL", "BILLING", "FUNCTIONAL_IMPACT",
    "ANATOMY", "MEDICATION", "LAB_RESULT",
)

REVIEW_STATUSES = (
    "UNREVIEWED", "CONFIRMED", "DISPUTED", "EXCLUDED",
)


class EvidenceFact(Base):
    __tablename__ = "evidence_facts"

    fact_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    fact_type: Mapped[str] = mapped_column(String(30), nullable=False, default="VISIT")
    fact_date: Mapped[date] = mapped_column(Date, nullable=True)
    fact_text: Mapped[str] = mapped_column(Text, nullable=False)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("providers.provider_id"), nullable=True)

    source_location_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("source_locations.location_id"), nullable=False)

    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="UNREVIEWED")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    previous_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("evidence_facts.fact_id"), nullable=True)

    is_contradicted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    duplicate_of_fact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("evidence_facts.fact_id"), nullable=True)

    quality_flags: Mapped[list | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    source_location = relationship("SourceLocation", lazy="selectin", foreign_keys=[source_location_id])
    case = relationship("Case", back_populates="evidence_facts")
    provider = relationship("Provider", lazy="selectin", foreign_keys=[provider_id])
    versions = relationship("FactVersion", back_populates="fact", cascade="all, delete-orphan", foreign_keys="FactVersion.fact_id")
