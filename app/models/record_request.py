"""Record request — one per provider, tracking fax transmission state."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RecordRequest(Base):
    __tablename__ = "record_requests"

    request_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("providers.provider_id"), nullable=False
    )
    fax_number: Mapped[str] = mapped_column(String(20), nullable=False)
    fax_transmission_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    # PENDING / SENT / DELIVERED / FAILED
    transmitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cover_sheet_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_summary(self) -> dict:
        return {
            "request_id": str(self.request_id),
            "provider_id": str(self.provider_id),
            "status": self.status,
            "fax_transmission_id": self.fax_transmission_id,
            "transmitted_at": self.transmitted_at.isoformat() if self.transmitted_at else None,
            "confirmed_at": self.confirmed_at.isoformat() if self.confirmed_at else None,
        }
