"""PHI store model.

Lives in a SEPARATE encrypted database instance. The operational database only
ever references ``client_token`` — never the PII itself. All PII columns hold
AES-256-GCM ciphertext (see ``app.core.crypto``).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, LargeBinary, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class PHIBase(DeclarativeBase):
    """Separate metadata so PHI tables are created only in the PHI instance."""


class Client(PHIBase):
    __tablename__ = "clients"

    client_token: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    encrypted_name: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encrypted_dob: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encrypted_address: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encrypted_phone: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
