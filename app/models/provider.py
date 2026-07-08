"""Provider record (identified from the intake record, confirmed by the attorney)."""

from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Provider(Base):
    __tablename__ = "providers"

    provider_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True
    )
    npi_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    provider_name: Mapped[str] = mapped_column(String(255), nullable=False)
    facility_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fax_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    specialty: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confirmation_status: Mapped[str] = mapped_column(String(20), nullable=False, default="UNCONFIRMED")
    retrieval_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    follow_up_count: Mapped[int] = mapped_column(Integer, default=0)
    # Provider-extraction metadata (spec §5.1).
    extraction_confidence: Mapped[str | None] = mapped_column(String(10), nullable=True)  # HIGH/MEDIUM/LOW
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "confirmation_status IN ('UNCONFIRMED','CONFIRMED','REMOVED')", name="valid_confirmation"
        ),
        CheckConstraint(
            "retrieval_status IN ('PENDING','REQUESTED','PARTIAL','COMPLETE','UNRESPONSIVE')",
            name="valid_retrieval",
        ),
    )

    def to_summary(self) -> dict:
        return {
            "provider_id": str(self.provider_id),
            "provider_name": self.provider_name,
            "facility_name": self.facility_name,
            "npi_number": self.npi_number,
            "specialty": self.specialty,
            "fax_number": self.fax_number,
            "confirmation_status": self.confirmation_status,
            "extraction_confidence": self.extraction_confidence,
            "source_reference": self.source_reference,
        }
