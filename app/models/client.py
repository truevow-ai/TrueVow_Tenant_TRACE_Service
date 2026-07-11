"""PHI store model — trace_phi.clients.

Lives in the trace_phi schema of the same Supabase project. The operational
database only ever references ``client_token`` — never the PII itself. All
PII columns hold base64-encoded AES-256-GCM ciphertext (see ``app.core.crypto``).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Text, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class PHIBase(DeclarativeBase):
    """Separate metadata so PHI tables are created only in the PHI engine."""


class Client(PHIBase):
    __tablename__ = "clients"

    client_token: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    encrypted_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_dob: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_phone: Mapped[str | None] = mapped_column(Text, nullable=True)
    encrypted_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
