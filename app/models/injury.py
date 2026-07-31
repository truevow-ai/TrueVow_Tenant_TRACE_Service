"""Injury — structured bodily or psychological harm allegation (ENT-052).

Anchors medical evidence to specific harm claims. Each injury tracks body area,
onset, mechanism, severity, and current status. Source-linked to facts and
medical records. Multiple injuries can stem from one incident.

Ontology alignment:
    ENT-052 Injury
    REL: belongs to client; referenced by treatment episodes; supports damages
    INV-007: Derived facts require provenance
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

INJURY_STATUSES = (
    "ACTIVE", "RESOLVED", "CHRONIC", "PERMANENT", "UNKNOWN",
)

BODY_REGIONS = (
    "HEAD", "NECK", "SHOULDER_RIGHT", "SHOULDER_LEFT",
    "BACK_UPPER", "BACK_LOWER", "SPINE_CERVICAL", "SPINE_THORACIC",
    "SPINE_LUMBAR", "ARM_RIGHT", "ARM_LEFT", "HIP_RIGHT", "HIP_LEFT",
    "LEG_RIGHT", "LEG_LEFT", "CHEST", "ABDOMEN", "PELVIS",
    "MULTIPLE", "OTHER",
)

INJURY_TYPES = (
    "STRAIN", "SPRAIN", "FRACTURE", "HERNIATION", "BULGING_DISC",
    "RADICULOPATHY", "CONCUSSION", "CONTUSION", "ABRASION", "LACERATION",
    "TEAR", "DISLOCATION", "NERVE_DAMAGE", "WHIPLASH", "SOFT_TISSUE",
    "TRAUMATIC_BRAIN_INJURY", "PSYCHOLOGICAL", "BURN", "AMPUTATION",
    "INTERNAL", "OTHER",
)


class Injury(Base):
    __tablename__ = "injuries"

    injury_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    body_region: Mapped[str] = mapped_column(String(30), nullable=False, default="OTHER")
    injury_type: Mapped[str] = mapped_column(String(30), nullable=False, default="OTHER")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    onset_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    mechanism: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    resolution_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_permanent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_fact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("evidence_facts.fact_id"), nullable=True)
    attorney_annotation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Symptom(Base):
    """Reported or documented manifestation over time (ENT-053).

    Source-attributed; not automatically a diagnosis. Tracks onset, frequency,
    severity, and associated body region. Links to injury and treatment.
    """
    __tablename__ = "symptoms"

    symptom_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    injury_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("injuries.injury_id"), nullable=True)
    body_region: Mapped[str | None] = mapped_column(String(30), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    onset_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(30), nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source_fact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("evidence_facts.fact_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class TreatmentEpisode(Base):
    """Course of care by provider/facility for a condition (ENT-055).

    Groups medical encounters into coherent treatment episodes. Links to
    injury, provider, and source facts. Tracks status from IDENTIFIED
    through DISCHARGED.
    """
    __tablename__ = "treatment_episodes"

    episode_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    injury_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("injuries.injury_id"), nullable=True)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("providers.provider_id"), nullable=True)
    episode_type: Mapped[str] = mapped_column(String(40), nullable=False, default="OTHER")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="IDENTIFIED")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    facility_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    treating_provider_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    provider = relationship("Provider", lazy="selectin", foreign_keys=[provider_id])
    injury = relationship("Injury", lazy="selectin", foreign_keys=[injury_id])


class Diagnosis(Base):
    """Provider-documented clinical diagnosis (ENT-054).

    Preserves source (provider, document, page) and code where available.
    Multiple diagnoses can be associated with one injury. Never overwrites -
    contradictory diagnoses from different providers are preserved.
    """
    __tablename__ = "diagnoses"

    diagnosis_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    injury_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("injuries.injury_id"), nullable=True)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("providers.provider_id"), nullable=True)
    diagnosis_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    diagnosis_code_system: Mapped[str | None] = mapped_column(String(20), nullable=True)
    diagnosis_text: Mapped[str] = mapped_column(Text, nullable=False)
    diagnosis_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_fact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("evidence_facts.fact_id"), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    provider = relationship("Provider", lazy="selectin", foreign_keys=[provider_id])
