"""Signed document tracking — DocuSeal integration.

ADR-001 §23: DocuSeal handles client signing of the retainer, HIPAA
authorization, and fee agreement before case initialization begins.
Each signing package produces one or more signed PDFs stored in the
``signed-documents`` Supabase Storage bucket with embedded audit trail.

This model tracks the signing metadata — the actual signed PDF bytes
are stored in Supabase Storage, not in the database.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

SIGNING_STATUSES = (
    "DRAFT",
    "SENT",
    "CLIENT_SIGNED",
    "COMPLETED",
    "EXPIRED",
    "REVOKED",
)

DOCUMENT_TYPES = (
    "RETAINER",
    "HIPAA_AUTHORIZATION",
    "FEE_AGREEMENT",
    "LIEN_ACKNOWLEDGMENT",
    "SETTLEMENT_AUTHORIZATION",
)


class SignedDocument(Base, TimestampMixin):
    __tablename__ = "signed_documents"

    signing_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False)
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    docuseal_submission_id: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[str] = mapped_column(String(30), nullable=False)
    signing_status: Mapped[str] = mapped_column(String(20), nullable=False, default="SENT")
    client_signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attorney_template_applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_pdf_storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    docuseal_audit_trail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
