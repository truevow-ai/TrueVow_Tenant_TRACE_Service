"""Billing reconciliation model — medical_bill_line table.

ADR-004 §5: TRACE owns its billing data (ADR-001 Decision #17).
Extracted from faxed billing statements via regex + lookup table.
Match confidence tiers from ADR-001 §24.7.
"""

from __future__ import annotations

import uuid
from datetime import date as date_type

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

MATCH_CONFIDENCE_VALUES = (
    "STRONG_MATCH",
    "LIKELY_MATCH",
    "POSSIBLE_MATCH",
    "NO_MATCHING_TREATMENT",
    "TREATMENT_WITH_NO_BILL",
    "NEEDS_REVIEW",
)


class MedicalBillLine(Base, TimestampMixin):
    __tablename__ = "medical_bill_line"

    bill_line_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False)
    firm_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documents.document_id"), nullable=False)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("providers.provider_id"), nullable=True)
    date_of_service: Mapped[date_type | None] = mapped_column(Date, nullable=True)
    cpt_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    icd10_codes: Mapped[str | None] = mapped_column(Text, nullable=True)
    billed_amount: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    match_confidence: Mapped[str | None] = mapped_column(String(30), nullable=True)
    matched_entry_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    attorney_note: Mapped[str | None] = mapped_column(Text, nullable=True)
