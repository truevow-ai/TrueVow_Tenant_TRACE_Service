"""JurisdictionProfile and JurisdictionActivation — separate global from tenant.

Correction #3 from BP-00 Contract Normalization:

Global JurisdictionProfile:
    Immutable platform definition of a jurisdiction's ruleset.
    No tenant_id. Versioned. Represents the canonical rules for a state.
    Example: California v1.0.1 with rules, required disclosures, signature
    requirements, supported workflows.

Tenant JurisdictionActivation:
    Tenant-specific activation of a jurisdiction profile.
    Has tenant_id. References an approved profile version.
    Contains effective status, activation date, and configuration.
    A tenant activates a profile without modifying it.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class JurisdictionProfile(Base):
    """Global immutable platform definition of a jurisdiction's ruleset.

    No tenant_id — this is canonical platform reference data.
    Versioned with effective dates. Tenants activate specific versions
    via JurisdictionActivation records.
    """
    __tablename__ = "jurisdiction_profiles"

    profile_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    jurisdiction: Mapped[str] = mapped_column(String(2), nullable=False)
    version: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    ruleset: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    required_disclosures: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    signature_requirements: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    supported_workflows: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class JurisdictionActivation(Base):
    """Tenant-specific activation of a jurisdiction profile.

    Has tenant_id. References an approved JurisdictionProfile version.
    Contains effective status and activation configuration. A tenant
    activates a profile without modifying the global canonical record.
    """
    __tablename__ = "jurisdiction_activations"

    activation_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    profile_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("jurisdiction_profiles.profile_id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    activated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tenant_override_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    profile = relationship("JurisdictionProfile", lazy="selectin", foreign_keys=[profile_id])
