"""Case Manifest — the master operational record for a TRACE case.

Contains NO direct PII: the client is referenced only by the opaque
``client_token`` (which resolves to the separate encrypted PHI store).
Firm isolation is enforced by RLS (``app.current_tenant_id``) in Postgres and
by application-level filtering everywhere.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

HIPAA_STATUSES = ("PENDING", "SIGNED", "EXPIRED")
PROVIDER_LIST_STATUSES = ("DRAFT", "CONFIRMED", "LOCKED")
CASE_STAGES = (
    "INITIALIZATION",
    "RETRIEVAL",
    "PROCESSING",
    "CHRONOLOGY_READY",
    "ATTORNEY_REVIEW",
    "DEMAND_READY",
)


class Case(Base, TimestampMixin):
    __tablename__ = "cases"

    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    client_token: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    intake_record_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, unique=True)

    incident_date: Mapped[date] = mapped_column(Date, nullable=False)
    jurisdiction_state: Mapped[str] = mapped_column(String(2), nullable=False)

    sol_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    sol_urgency: Mapped[str | None] = mapped_column(String(10), nullable=True)

    hipaa_auth_status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    provider_list_status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    case_stage: Mapped[str] = mapped_column(String(30), nullable=False, default="INITIALIZATION")

    approval_attorney_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    approval_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approval_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "hipaa_auth_status IN ('PENDING','SIGNED','EXPIRED')", name="valid_hipaa_status"
        ),
        CheckConstraint(
            "provider_list_status IN ('DRAFT','CONFIRMED','LOCKED')", name="valid_provider_status"
        ),
        CheckConstraint(
            "case_stage IN ('INITIALIZATION','RETRIEVAL','PROCESSING',"
            "'CHRONOLOGY_READY','ATTORNEY_REVIEW','DEMAND_READY')",
            name="valid_stage",
        ),
    )

    def to_summary(self) -> dict:
        """Firm-safe summary. Contains no PII (client is a token only)."""
        return {
            "case_id": str(self.case_id),
            "client_token": str(self.client_token),
            "incident_date": self.incident_date.isoformat() if self.incident_date else None,
            "jurisdiction_state": self.jurisdiction_state,
            "sol_deadline": self.sol_deadline.isoformat() if self.sol_deadline else None,
            "sol_urgency": self.sol_urgency,
            "hipaa_auth_status": self.hipaa_auth_status,
            "provider_list_status": self.provider_list_status,
            "case_stage": self.case_stage,
        }
