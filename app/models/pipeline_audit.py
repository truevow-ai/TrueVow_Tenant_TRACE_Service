"""Pipeline audit log — SYSTEM-level events for HIPAA audit trail.

ADR-001 §9 extends audit coverage to internal pipeline stages:
OCR start/complete, de-ID success/failure, flag detection runs,
cloud OCR escalation.

Same append-only enforcement as ``audit_log``: INSERT-only for
``trace_app_role``. Immutable — no UPDATE or DELETE.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, JSON, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PipelineAuditLog(Base):
    __tablename__ = "pipeline_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False, default="SYSTEM")
    metadata_: Mapped[dict | None] = mapped_column("metadata_", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
