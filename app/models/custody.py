"""Chain of Custody, Witness, WitnessStatement — evidence integrity models.

Ontology alignment:
    ENT-069 ChainOfCustodyEvent — documents possession, transfer, transformation
    ENT-070 Witness — person with potentially relevant knowledge
    ENT-071 WitnessStatement — recorded or documented account

INV-007: Every derived fact requires provenance
INV-008: Contradictions are preserved
Chain of custody is append-only — events are never modified or deleted.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

CUSTODY_EVENT_TYPES = (
    "RECEIVED", "TRANSFERRED", "COPIED", "TRANSFORMED",
    "VERIFIED", "CLASSIFIED", "REDACTED", "EXTRACTED",
    "DESTROYED", "EXPORTED",
)

WITNESS_TYPES = (
    "CLIENT", "EYEWITNESS", "EXPERT", "TREATING_PROVIDER",
    "ADVERSE_PARTY", "INVESTIGATING_OFFICER", "FACT_WITNESS",
    "CHARACTER_WITNESS", "OTHER",
)

WITNESS_STATEMENT_TYPES = (
    "RECORDED", "WRITTEN", "AFFIDAVIT", "DECLARATION",
    "DEPOSITION", "INTERVIEW_NOTE", "OTHER",
)


class ChainOfCustodyEvent(Base):
    """Immutable event documenting possession, transfer, or transformation (ENT-069).

    Append-only: records are created but never modified or deleted.
    Each event captures who held the evidence, what happened to it,
    and when — creating an unbroken chain for deposition readiness.
    """
    __tablename__ = "chain_of_custody_events"

    event_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    from_custodian: Mapped[str | None] = mapped_column(String(200), nullable=True)
    to_custodian: Mapped[str | None] = mapped_column(String(200), nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    integrity_hash_before: Mapped[str | None] = mapped_column(String(64), nullable=True)
    integrity_hash_after: Mapped[str | None] = mapped_column(String(64), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Witness(Base):
    """Person with potentially relevant knowledge (ENT-070).

    Links contact information, credibility notes, and role in the matter.
    Statements are linked separately via WitnessStatement.
    """
    __tablename__ = "witnesses"

    witness_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    witness_type: Mapped[str] = mapped_column(String(30), nullable=False, default="FACT_WITNESS")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    relationship_to_client: Mapped[str | None] = mapped_column(String(100), nullable=True)
    credibility_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deposed: Mapped[bool] = mapped_column(default=False)
    deposition_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class WitnessStatement(Base):
    """Recorded or documented account with source and conditions (ENT-071).

    Never silently rewritten as fact. Source-linked to the statement document.
    Contradictory statements from same or different witnesses are preserved.
    """
    __tablename__ = "witness_statements"

    statement_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    witness_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("witnesses.witness_id"), nullable=False)
    statement_type: Mapped[str] = mapped_column(String(30), nullable=False, default="OTHER")
    statement_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_document_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("documents.document_id"), nullable=True)
    source_page_number: Mapped[int | None] = mapped_column(nullable=True)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    under_oath: Mapped[bool] = mapped_column(default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    witness = relationship("Witness", lazy="selectin", foreign_keys=[witness_id])
