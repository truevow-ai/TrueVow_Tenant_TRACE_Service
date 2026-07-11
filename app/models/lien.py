"""Lien tracking model — attorney-managed, not auto-detected.

ADR-004 §3: TRACE tracks lien status — does not detect liens automatically.
Tier 3 (attorney judgment only). The Liens column surfaces what the
attorney sets so liens are not overlooked before demand.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

LIEN_TYPES = ("MEDICARE", "MEDICAID", "ERISA", "WORKERS_COMP", "HEALTH_INSURANCE", "OTHER")
LIEN_STATUSES = ("NOT_CHECKED", "REQUESTED", "RECEIVED", "REVIEWED")


class Lien(Base, TimestampMixin):
    __tablename__ = "liens"

    lien_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False)
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    lien_type: Mapped[str] = mapped_column(String(30), nullable=False)
    lienholder: Mapped[str | None] = mapped_column(Text, nullable=True)
    claimed_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_CHECKED")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
