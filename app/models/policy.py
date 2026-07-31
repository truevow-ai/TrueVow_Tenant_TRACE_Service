"""PolicyRegistry model — versioned tenant policies for the Policy Registry.

Stores firm-approved rules, jurisdiction configurations, and template
governance records. Every FIRM_POLICY action must reference an approved
policy version. Policies are immutable once approved; changes create new
versions.

Ontology alignment:
    ENT-005 Jurisdiction Profile — versioned package of rules and constraints
    ENT-006 Firm Policy — tenant-approved rule governing execution
    INV-010 Policy-at-execution — exact effective version stored at action time
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, Uuid, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

POLICY_CATEGORIES = (
    "JURISDICTION", "ENGAGEMENT", "COMMUNICATION", "DOCUMENT",
    "SIGNATURE", "RETENTION", "CONSENT", "ESCALATION",
    "RECORDS", "DEMAND", "SETTLEMENT", "AUTOMATION", "OTHER",
)


class PolicyRecord(Base):
    __tablename__ = "policy_records"

    policy_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="OTHER")
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    previous_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    jurisdiction: Mapped[str | None] = mapped_column(String(2), nullable=True)
    effective_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiration_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    policy_content: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
