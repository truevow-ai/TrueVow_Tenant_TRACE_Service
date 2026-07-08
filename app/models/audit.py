"""Audit log — append-only record of every PHI-relevant action.

HIPAA §7.1: every access logged with actor, timestamp, action, and the resource
touched. This table is append-only at the database level: ``trace_app_role`` is
granted INSERT only (no SELECT/UPDATE/DELETE) — see ``infra/database/roles.sql``.
Entries must never contain PII — only opaque identifiers.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False)  # ATTORNEY/SYSTEM/SUPPORT
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    case_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    firm_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
