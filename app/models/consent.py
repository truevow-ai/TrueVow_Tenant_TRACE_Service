"""ConsentRecord model — persistent storage for the Consent Ledger.

Each record is an immutable consent event in the append-only Consent Ledger.
Records are created, never modified or deleted. The current consent state is
derived from the most recent record for each (person_id, consent_type) pair.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Uuid, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

CONSENT_STATES = (
    "NOT_REQUESTED", "REQUESTED", "GRANTED", "DECLINED",
    "REVOKED", "EXPIRED", "SUPERSEDED",
)

CONSENT_TYPES = (
    "COMMUNICATION", "SMS", "RECORDING", "ELECTRONIC_DELIVERY",
    "ELECTRONIC_SIGNATURE", "DISCLOSURE_ACKNOWLEDGMENT",
    "DATA_SHARING", "HIPAA_AUTHORIZATION",
)


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    consent_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("cases.firm_id"), nullable=True)
    matter_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("cases.case_id"), nullable=True)
    consent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_REQUESTED")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    previous_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    granted_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    disclosure_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expiration_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
