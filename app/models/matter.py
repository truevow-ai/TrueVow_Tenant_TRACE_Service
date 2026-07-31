"""Claim, Incident, Damages — matter structure models (ENT-042, -043, -050, -051).

TRACE ontology alignment:
    ENT-042 Claim — demand for relief against an adverse party or insurer
    ENT-043 Incident — occurrence giving rise to potential claims
    ENT-050 DamagesCategory — structured category of claimed loss
    ENT-051 DamagesItem — specific claimed loss with amount and source

REL-009: Matter has Claims (1 -> many)
REL-010: Claim relates to Incident (many -> many)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

CLAIM_TYPES = (
    "BODILY_INJURY", "PROPERTY_DAMAGE", "UNINSURED_MOTORIST",
    "UNDERINSURED_MOTORIST", "MEDICAL_PAYMENTS", "PERSONAL_INJURY_PROTECTION",
    "WRONGFUL_DEATH", "LOSS_OF_CONSORTIUM", "BAD_FAITH", "OTHER",
)

CLAIM_STATUSES = (
    "OPEN", "DEMAND_SENT", "NEGOTIATION", "SETTLED", "DENIED",
    "LITIGATED", "CLOSED", "DORMANT",
)

INCIDENT_TYPES = (
    "MOTOR_VEHICLE_COLLISION", "SLIP_AND_FALL", "PREMISES_LIABILITY",
    "MEDICAL_MALPRACTICE", "PRODUCT_LIABILITY", "WORKPLACE_INJURY",
    "DOG_BITE", "ASSAULT", "PEDESTRIAN", "BICYCLE", "TRUCKING",
    "MOTORCYCLE", "RIDE_SHARE", "PUBLIC_TRANSIT", "OTHER",
)

DAMAGES_CATEGORIES = (
    "MEDICAL_EXPENSES", "FUTURE_MEDICAL", "LOST_WAGES",
    "LOST_EARNING_CAPACITY", "PAIN_AND_SUFFERING",
    "EMOTIONAL_DISTRESS", "LOSS_OF_CONSORTIUM",
    "LOSS_OF_ENJOYMENT", "PROPERTY_DAMAGE", "PUNITIVE",
    "OUT_OF_POCKET", "OTHER_ECONOMIC", "OTHER_NONECONOMIC",
)

DAMAGES_ITEM_STATUSES = ("CLAIMED", "SUPPORTED", "DISPUTED", "STIPULATED", "AWARDED")


class Incident(Base):
    """Occurrence or exposure giving rise to potential claims (ENT-043).

    Anchors time, location, parties, and mechanism. Source-linked to
    police reports, intake statements, and other evidence.
    """
    __tablename__ = "incidents"

    incident_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    incident_type: Mapped[str] = mapped_column(String(40), nullable=False, default="OTHER")
    incident_date: Mapped[date] = mapped_column(Date, nullable=False)
    incident_time: Mapped[str | None] = mapped_column(String(10), nullable=True)
    location_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location_state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    location_zip: Mapped[str | None] = mapped_column(String(10), nullable=True)
    mechanism: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    police_report_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    police_agency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    weather_conditions: Mapped[str | None] = mapped_column(String(100), nullable=True)
    road_conditions: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_fact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("evidence_facts.fact_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Claim(Base):
    """Demand for relief against an adverse party or insurer (ENT-042).

    A Matter may contain multiple Claims, each with its own status, value,
    and resolution. Claims may resolve independently.
    """
    __tablename__ = "claims"

    claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("incidents.incident_id"), nullable=True)
    claim_type: Mapped[str] = mapped_column(String(30), nullable=False, default="BODILY_INJURY")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    claimed_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    settled_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    adverse_party_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    adverse_party_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    incident = relationship("Incident", lazy="selectin", foreign_keys=[incident_id])


class DamagesCategory(Base):
    """Structured category of claimed loss (ENT-050)."""
    __tablename__ = "damages_categories"

    category_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("claims.claim_id"), nullable=True)
    category_type: Mapped[str] = mapped_column(String(30), nullable=False, default="MEDICAL_EXPENSES")
    total_claimed: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_supported: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class DamagesItem(Base):
    """Specific claimed loss with amount, source, certainty, and status (ENT-051)."""
    __tablename__ = "damages_items"

    item_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("damages_categories.category_id"), nullable=True)
    claim_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("claims.claim_id"), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_fact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("evidence_facts.fact_id"), nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("documents.document_id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="CLAIMED")
    date_incurred: Mapped[date | None] = mapped_column(Date, nullable=True)
    certainty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
