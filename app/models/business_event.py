"""Business Event Model — implements the ontology Event Envelope spec.

EventEnvelope v1.0.1 — 18 required fields:
    event_id, event_type, occurred_at, recorded_at,
    tenant_id, aggregate_type, aggregate_id, aggregate_version,
    actor_type, actor_id, authority_class, authority_record_id,
    policy_version_id, correlation_id, causation_id,
    payload, sensitivity_class, schema_version

Optional fields: none at envelope root. Product extensions prohibited.
All 18 fields are non-nullable except actor_id, authority_record_id,
policy_version_id, correlation_id, causation_id, payload.

Rules:
    append_only — events are created, never modified or deleted
    idempotent_by_event_id — duplicate event_ids are rejected
    tenant_scoped — every event carries non-null tenant_id
    schema_versioned — each event records its schema version
    no_secrets_in_payload — payload must be free of secrets/tokens/keys

This model stores business events separately from diagnostic logs (INV-015).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

SENSITIVITY_CLASSES = ("PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED", "PHI")


class BusinessEvent(Base):
    __tablename__ = "business_events"

    event_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    aggregate_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    authority_class: Mapped[str] = mapped_column(String(30), nullable=False)
    authority_record_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    policy_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    causation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sensitivity_class: Mapped[str] = mapped_column(String(20), nullable=False, default="INTERNAL")
    schema_version: Mapped[str] = mapped_column(String(10), nullable=False, default="1.0.1")

    __table_args__ = (
        Index("ix_business_events_aggregate", "aggregate_type", "aggregate_id"),
        Index("ix_business_events_tenant_time", "tenant_id", "occurred_at"),
    )
