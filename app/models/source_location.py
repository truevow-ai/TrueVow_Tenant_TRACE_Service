"""SourceLocation — links every extracted fact to its exact origin in a document.

Every derived assertion in TRACE must be traceable back to its source.
This model captures page, bounding box, text snippet, extraction method,
and confidence — the full provenance chain for deposition readiness.

SourceLocation is the atomic unit of provenance. One SourceLocation per
fact, one document per SourceLocation. Never shared across facts because
each fact may be extracted from a different passage on the same page.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

EXTRACTION_METHODS = (
    "openmed", "regex", "ocr", "llm", "manual", "mistral_ocr",
)


class SourceLocation(Base):
    __tablename__ = "source_locations"

    location_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documents.document_id"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    bbox_x1: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y1: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_x2: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y2: Mapped[float | None] = mapped_column(Float, nullable=True)
    text_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_method: Mapped[str] = mapped_column(String(30), nullable=False, default="regex")
    extraction_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    extraction_model_version: Mapped[str | None] = mapped_column(String(30), nullable=True)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    document = relationship("Document", lazy="selectin")
