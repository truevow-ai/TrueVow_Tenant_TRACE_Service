"""FactVersion — immutable audit trail of every fact modification.

When an attorney edits a fact (corrects a date, refines text, changes
review status), the previous state is preserved as a FactVersion record.
This creates a complete, deposition-ready audit trail of every change
to every fact.

FactVersion records are append-only — they are never modified or deleted.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class FactVersion(Base):
    __tablename__ = "fact_versions"

    version_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    fact_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("evidence_facts.fact_id", ondelete="CASCADE"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_fact_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_fact_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    previous_fact_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    previous_review_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    previous_provider_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    fact = relationship("EvidenceFact", back_populates="versions", foreign_keys=[fact_id])
