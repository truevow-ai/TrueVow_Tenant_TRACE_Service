"""Firm user model — maps Clerk user IDs to TRACE firm contexts.

A single attorney or paralegal belongs to exactly one firm. Clerk
provides identity, TRACE provides authorization via the firm_id
column, which drives Row-Level Security (app.current_tenant_id GUC).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

USER_ROLES = ("ATTORNEY", "PARALEGAL", "ADMIN")


class FirmUser(Base):
    __tablename__ = "firm_users"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    clerk_user_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="ATTORNEY")
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
