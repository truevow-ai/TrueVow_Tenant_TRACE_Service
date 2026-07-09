"""Document metadata — references to stored medical record bytes.

Documents are stored in Supabase Storage (``trace-medical-records`` bucket).
This model tracks metadata only — the actual PDF/JPEG bytes are never in
the database. Every document carries its provenance (source) for
deduplication: provider fax records are more authoritative than client
uploads, and the dedup engine flags duplicates across sources.

Object key normalization: ``{case_id}/{document_id}.{extension}``
No PHI in keys — case_id and document_id are opaque UUIDs.
The ``source`` field tracks provenance for dedup and audit.

IMPORTANT: ``original_filename`` may contain PHI (client names,
DOBs in filenames like "John_Smith_records.pdf"). Store in DB
only. Never write to any log statement, notification, or error
message. Log ``document_id``, not the filename.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

DOCUMENT_TYPES = ("ER", "IMAGING", "PT", "SPECIALIST", "PRIMARY_CARE", "BILLING", "PHARMACY", "OTHER")
OCR_STATUSES = ("PENDING", "IN_PROGRESS", "COMPLETE", "FAILED")
DOCUMENT_SOURCES = ("PROVIDER_FAX", "ATTORNEY_UPLOAD", "CLIENT_UPLOAD", "SCAN", "UNKNOWN")


class Document(Base):
    __tablename__ = "documents"

    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("providers.provider_id"), nullable=True)
    s3_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    document_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    ocr_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    is_misfiled: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN")
    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    original_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    quality_flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)
