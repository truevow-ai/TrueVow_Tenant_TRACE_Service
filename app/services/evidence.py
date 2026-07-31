"""Evidence Service — source-linked fact extraction, contradiction detection, missing-evidence signals.

This is the core engine that implements the TRACE pipeline:
    Activated Matter → Providers → Record Requests → Records Received
    → Facts Extracted → Contradictions Preserved → Chronology
    → Missing-Evidence Signals → Attorney-Reviewable Demand Readiness

Every fact is source-linked via SourceLocation. Contradicting facts from
different sources are preserved, not overwritten. Missing-evidence signals
surface gaps before the attorney finalizes the demand.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.logging import get_logger
from app.models.contradiction import ContradictionPair
from app.models.document import Document
from app.models.evidence_fact import EvidenceFact
from app.models.missing_evidence import MissingEvidenceSignal
from app.models.source_location import SourceLocation

logger = get_logger("trace.evidence")


@dataclass
class ExtractedFact:
    fact_type: str
    fact_date: date | None
    fact_text: str
    provider_id: uuid.UUID | None
    document_id: uuid.UUID
    page_number: int
    text_snippet: str | None = None
    extraction_method: str = "regex"
    extraction_confidence: float | None = None
    extraction_model_version: str | None = None


@dataclass
class ExtractionResult:
    facts_created: int = 0
    contradictions_found: int = 0
    missing_evidence_signals: int = 0
    errors: list[str] = field(default_factory=list)


class EvidenceService:
    """Central service for source-linked fact management."""

    async def extract_facts_from_pages(
        self,
        case_id: uuid.UUID,
        redacted_pages: list[dict[str, Any]],
    ) -> ExtractionResult:
        """Extract facts from de-identified OCR pages and persist with source locations.

        Args:
            case_id: The case UUID
            redacted_pages: List of dicts with keys: document_id, page_number,
                           redacted_text, provider_id, facility_name
        """
        from app.services.nlp import create_openmed_service

        nlp = create_openmed_service()
        result = ExtractionResult()

        for page in redacted_pages:
            text = page.get("redacted_text", "")
            if not text:
                continue

            document_id = page.get("document_id")
            page_number = page.get("page_number", 1)
            provider_id = page.get("provider_id")

            if not document_id:
                continue

            try:
                doc_uuid = uuid.UUID(document_id) if isinstance(document_id, str) else document_id
            except (ValueError, TypeError):
                result.errors.append(f"Invalid document_id: {document_id}")
                continue

            ner_result = await nlp.extract_clinical_entities(text)

            for entity in ner_result.entities:
                event_date = self._extract_date(entity.text) or self._extract_date(text)
                if event_date is None:
                    continue

                fact_type = self._classify_fact_type(entity.label)
                clinical_text = entity.text[:500]

                extracted = ExtractedFact(
                    fact_type=fact_type,
                    fact_date=event_date,
                    fact_text=clinical_text,
                    provider_id=uuid.UUID(provider_id) if provider_id else None,
                    document_id=doc_uuid,
                    page_number=page_number,
                    text_snippet=entity.text[:300] if entity.text else None,
                    extraction_method="openmed" if nlp._use_openmed else "regex",
                    extraction_confidence=entity.confidence if hasattr(entity, 'confidence') else None,
                    extraction_model_version="1.7.0" if nlp._use_openmed else "regex-v1",
                )

                await self.persist_fact(case_id, extracted)
                result.facts_created += 1

        return result

    async def persist_fact(
        self,
        case_id: uuid.UUID,
        extracted: ExtractedFact,
    ) -> EvidenceFact:
        """Create a SourceLocation and EvidenceFact in a single transaction."""

        async with async_session_maker() as session:
            location = SourceLocation(
                document_id=extracted.document_id,
                page_number=extracted.page_number,
                text_snippet=extracted.text_snippet,
                extraction_method=extracted.extraction_method,
                extraction_confidence=extracted.extraction_confidence,
                extraction_model_version=extracted.extraction_model_version,
            )
            session.add(location)
            await session.flush()

            fact = EvidenceFact(
                case_id=case_id,
                fact_type=extracted.fact_type,
                fact_date=extracted.fact_date,
                fact_text=extracted.fact_text,
                provider_id=extracted.provider_id,
                source_location_id=location.location_id,
                review_status="UNREVIEWED",
                version=1,
            )
            session.add(fact)
            await session.commit()
            await session.refresh(fact)
            return fact

    async def get_facts_for_case(
        self,
        case_id: uuid.UUID,
        session: AsyncSession | None = None,
    ) -> list[EvidenceFact]:
        """Get all facts for a case with full source provenance loaded."""

        async def _query(s: AsyncSession) -> list[EvidenceFact]:
            result = await s.execute(
                select(EvidenceFact)
                .where(EvidenceFact.case_id == case_id)
                .order_by(EvidenceFact.fact_date)
            )
            return list(result.scalars().all())

        if session:
            return await _query(session)
        async with async_session_maker() as s:
            return await _query(s)

    async def detect_contradictions(
        self,
        case_id: uuid.UUID,
    ) -> int:
        """Detect contradictions among facts in a case. Preserves, doesn't overwrite.

        Returns number of new contradiction pairs found.
        """
        facts = await self.get_facts_for_case(case_id)
        if len(facts) < 2:
            return 0

        new_contradictions = 0

        async with async_session_maker() as session:
            existing_pairs = await session.execute(
                select(ContradictionPair).where(ContradictionPair.case_id == case_id)
            )
            existing_set: set[tuple[uuid.UUID, uuid.UUID]] = set()
            for pair in existing_pairs.scalars().all():
                existing_set.add((pair.fact_a_id, pair.fact_b_id))
                existing_set.add((pair.fact_b_id, pair.fact_a_id))

            for i, fact_a in enumerate(facts):
                for fact_b in facts[i + 1:]:
                    if (fact_a.fact_id, fact_b.fact_id) in existing_set:
                        continue

                    contradiction = self._compare_facts(fact_a, fact_b)
                    if contradiction:
                        pair = ContradictionPair(
                            case_id=case_id,
                            fact_a_id=fact_a.fact_id,
                            fact_b_id=fact_b.fact_id,
                            contradiction_type=contradiction["type"],
                            resolution_status="UNRESOLVED",
                        )
                        session.add(pair)
                        fact_a.is_contradicted = True
                        fact_b.is_contradicted = True
                        session.add(fact_a)
                        session.add(fact_b)
                        new_contradictions += 1

            await session.commit()

        return new_contradictions

    def _compare_facts(self, a: EvidenceFact, b: EvidenceFact) -> dict[str, str] | None:
        """Compare two facts for contradiction. Returns contradiction info or None."""

        if a.source_location_id == b.source_location_id:
            return None

        if a.provider_id and b.provider_id and a.provider_id == b.provider_id:
            return None

        if a.fact_type != b.fact_type:
            return None

        if a.fact_date and b.fact_date:
            date_diff = abs((a.fact_date - b.fact_date).days)
            if date_diff > 30:
                return None

        text_a = (a.fact_text or "").lower()
        text_b = (b.fact_text or "").lower()

        if a.fact_type == "DIAGNOSIS":
            if not self._texts_overlap(text_a, text_b, threshold=0.35):
                return {"type": "DIAGNOSIS_CONFLICT"}

        if a.fact_type in ("MEDICATION", "PRESCRIPTION"):
            if not self._texts_overlap(text_a, text_b, threshold=0.5):
                return {"type": "MEDICATION_CONFLICT"}

        if a.fact_type == "IMAGING":
            if not self._texts_overlap(text_a, text_b, threshold=0.5):
                return {"type": "IMAGING_DISCREPANCY"}

        if a.fact_type in ("DISCHARGE", "REFERRAL"):
            if not self._texts_overlap(text_a, text_b, threshold=0.4):
                return {"type": "PROVIDER_DISAGREEMENT"}

        if a.fact_date and b.fact_date:
            date_diff = abs((a.fact_date - b.fact_date).days)
            if date_diff <= 2 and text_a == text_b:
                return None

        return None

    @staticmethod
    def _texts_overlap(a: str, b: str, threshold: float = 0.5) -> bool:
        """Check if two texts share enough content to be considered overlapping."""
        words_a = set(a.split())
        words_b = set(b.split())
        if not words_a or not words_b:
            return False
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) >= threshold

    async def generate_missing_evidence_signals(
        self,
        case_id: uuid.UUID,
    ) -> int:
        """Generate signals for expected records that are missing.

        Returns number of new signals generated.
        """
        facts = await self.get_facts_for_case(case_id)
        new_signals = 0

        async with async_session_maker() as session:
            document_ids: set[uuid.UUID] = set()
            doc_result = await session.execute(
                select(Document.document_id).where(Document.case_id == case_id)
            )
            for row in doc_result.scalars().all():
                document_ids.add(row)

            existing_signals = await session.execute(
                select(MissingEvidenceSignal.signal_type, MissingEvidenceSignal.source_fact_id)
                .where(MissingEvidenceSignal.case_id == case_id)
            )
            existing_combos: set[tuple[str, uuid.UUID | None]] = set(
                (row[0], row[1]) for row in existing_signals.all()
            )

            for fact in facts:
                signal = self._check_missing_evidence(fact, document_ids)
                if signal and (signal["type"], signal.get("source_fact_id")) not in existing_combos:
                    ms = MissingEvidenceSignal(
                        case_id=case_id,
                        signal_type=signal["type"],
                        source_fact_id=signal.get("source_fact_id"),
                        expected_record_type=signal.get("expected_record_type"),
                        expected_from_provider_id=fact.provider_id,
                        expected_date_range_start=signal.get("date_start"),
                        expected_date_range_end=signal.get("date_end"),
                        days_overdue=signal.get("days_overdue", 0),
                    )
                    session.add(ms)
                    new_signals += 1

            await session.commit()

        return new_signals

    def _check_missing_evidence(
        self,
        fact: EvidenceFact,
        existing_document_ids: set[uuid.UUID],
    ) -> dict[str, Any] | None:
        """Check if a fact implies a missing record."""
        text = (fact.fact_text or "").lower()

        imaging_keywords = ["mri ordered", "ct ordered", "x-ray ordered", "imaging ordered", "ultrasound ordered"]
        if any(kw in text for kw in imaging_keywords):
            return {
                "type": "MISSING_IMAGING_REPORT",
                "source_fact_id": fact.fact_id,
                "expected_record_type": "IMAGING_REPORT",
                "date_start": fact.fact_date,
                "date_end": fact.fact_date,
                "days_overdue": self._days_since(fact.fact_date),
            }

        procedure_keywords = ["surgery scheduled", "procedure scheduled", "injection scheduled"]
        if any(kw in text for kw in procedure_keywords):
            return {
                "type": "MISSING_PROCEDURE_REPORT",
                "source_fact_id": fact.fact_id,
                "expected_record_type": "PROCEDURE_REPORT",
                "date_start": fact.fact_date,
                "date_end": fact.fact_date,
                "days_overdue": self._days_since(fact.fact_date),
            }

        followup_patterns = ["follow up in", "follow-up in", "return in", "return to clinic"]
        if any(pattern in text for pattern in followup_patterns):
            return {
                "type": "MISSING_FOLLOWUP_RECORD",
                "source_fact_id": fact.fact_id,
                "expected_record_type": "FOLLOWUP_VISIT",
                "date_start": fact.fact_date,
                "date_end": fact.fact_date,
                "days_overdue": self._days_since(fact.fact_date),
            }

        referral_patterns = ["referred to", "refer to", "consult with"]
        if any(pattern in text for pattern in referral_patterns):
            return {
                "type": "MISSING_REFERRAL_RECORD",
                "source_fact_id": fact.fact_id,
                "expected_record_type": "SPECIALIST_NOTE",
                "date_start": fact.fact_date,
                "date_end": fact.fact_date,
                "days_overdue": self._days_since(fact.fact_date),
            }

        if fact.fact_type == "DISCHARGE":
            if not existing_document_ids:
                return None

        return None

    @staticmethod
    def _days_since(d: date | None) -> int:
        if d is None:
            return 0
        return (date.today() - d).days

    @staticmethod
    def _extract_date(text: str) -> date | None:
        import re

        patterns = [
            (r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", None),
            (r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", None),
            (r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
             r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
             r"Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", None),
        ]

        month_map = {
            "jan": 1, "january": 1, "feb": 2, "february": 2,
            "mar": 3, "march": 3, "apr": 4, "april": 4,
            "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
            "aug": 8, "august": 8, "sep": 9, "september": 9,
            "oct": 10, "october": 10, "nov": 11, "november": 11,
            "dec": 12, "december": 12,
        }

        for pattern, _ in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                try:
                    if len(groups) == 3 and groups[0].isdigit() and groups[1].isdigit() and groups[2].isdigit():
                        month = int(groups[0])
                        day = int(groups[1])
                        year = int(groups[2])
                    elif len(groups) == 3 and not groups[0].isdigit():
                        month = month_map.get(groups[0].lower()[:3], 1)
                        day = int(groups[1])
                        year = int(groups[2])
                    else:
                        continue
                    if year < 100:
                        year += 2000
                    if 1 <= month <= 12 and 1 <= day <= 31:
                        return date(year, month, day)
                except (ValueError, IndexError):
                    continue
        return None

    @staticmethod
    def _classify_fact_type(entity_label: str) -> str:
        mapping = {
            "PROVIDER": "VISIT",
            "DISEASE": "DIAGNOSIS",
            "DRUG": "MEDICATION",
            "MEDICATION": "MEDICATION",
            "PROCEDURE": "PROCEDURE",
            "IMAGING": "IMAGING",
            "ANATOMY": "ANATOMY",
            "DISCHARGE": "DISCHARGE",
            "REFERRAL": "REFERRAL",
        }
        return mapping.get(entity_label.upper(), "VISIT")

    async def build_chronology_from_facts(
        self,
        case_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Build a source-linked chronology from persisted EvidenceFacts.

        Returns a dict suitable for the QA/export API, with every entry
        carrying full provenance: source document, page, extraction method,
        confidence, review status, and contradictions.
        """
        facts = await self.get_facts_for_case(case_id)

        entries: list[dict[str, Any]] = []
        for fact in facts:
            source = fact.source_location if fact.source_location else None
            entries.append({
                "entry_id": str(fact.fact_id),
                "fact_type": fact.fact_type,
                "event_date": fact.fact_date.isoformat() if fact.fact_date else None,
                "clinical_description": fact.fact_text[:200],
                "provider_id": str(fact.provider_id) if fact.provider_id else None,
                "source_document_id": str(source.document_id) if source else None,
                "source_page_number": source.page_number if source else None,
                "extraction_method": source.extraction_method if source else "unknown",
                "extraction_confidence": source.extraction_confidence,
                "extraction_model_version": source.extraction_model_version,
                "review_status": fact.review_status,
                "reviewed_by": str(fact.reviewed_by) if fact.reviewed_by else None,
                "reviewed_at": fact.reviewed_at.isoformat() if fact.reviewed_at else None,
                "review_note": fact.review_note,
                "version": fact.version,
                "is_contradicted": fact.is_contradicted,
                "is_duplicate": fact.is_duplicate,
                "duplicate_of_fact_id": str(fact.duplicate_of_fact_id) if fact.duplicate_of_fact_id else None,
            })

        entries.sort(key=lambda e: e.get("event_date") or "")

        return {
            "case_id": str(case_id),
            "total_entries": len(entries),
            "entries": entries,
        }

    async def get_contradictions_for_case(
        self,
        case_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Get all contradiction pairs for a case with full fact details."""

        async with async_session_maker() as session:
            result = await session.execute(
                select(ContradictionPair).where(ContradictionPair.case_id == case_id)
            )
            pairs = result.scalars().all()

            return [
                {
                    "contradiction_id": str(p.contradiction_id),
                    "contradiction_type": p.contradiction_type,
                    "resolution_status": p.resolution_status,
                    "resolved_by": str(p.resolved_by) if p.resolved_by else None,
                    "resolved_at": p.resolved_at.isoformat() if p.resolved_at else None,
                    "attorney_note": p.attorney_note,
                    "fact_a": {
                        "fact_id": str(p.fact_a.fact_id) if p.fact_a else None,
                        "fact_type": p.fact_a.fact_type if p.fact_a else None,
                        "fact_date": p.fact_a.fact_date.isoformat() if p.fact_a and p.fact_a.fact_date else None,
                        "fact_text": p.fact_a.fact_text[:200] if p.fact_a else None,
                        "source_document_id": str(p.fact_a.source_location.document_id) if p.fact_a and p.fact_a.source_location else None,
                        "source_page_number": p.fact_a.source_location.page_number if p.fact_a and p.fact_a.source_location else None,
                        "provider_id": str(p.fact_a.provider_id) if p.fact_a and p.fact_a.provider_id else None,
                    } if p.fact_a else None,
                    "fact_b": {
                        "fact_id": str(p.fact_b.fact_id) if p.fact_b else None,
                        "fact_type": p.fact_b.fact_type if p.fact_b else None,
                        "fact_date": p.fact_b.fact_date.isoformat() if p.fact_b and p.fact_b.fact_date else None,
                        "fact_text": p.fact_b.fact_text[:200] if p.fact_b else None,
                        "source_document_id": str(p.fact_b.source_location.document_id) if p.fact_b and p.fact_b.source_location else None,
                        "source_page_number": p.fact_b.source_location.page_number if p.fact_b and p.fact_b.source_location else None,
                        "provider_id": str(p.fact_b.provider_id) if p.fact_b and p.fact_b.provider_id else None,
                    } if p.fact_b else None,
                }
                for p in pairs
            ]

    async def get_missing_evidence_for_case(
        self,
        case_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Get all missing-evidence signals for a case."""

        async with async_session_maker() as session:
            result = await session.execute(
                select(MissingEvidenceSignal)
                .where(MissingEvidenceSignal.case_id == case_id)
                .order_by(MissingEvidenceSignal.days_overdue.desc())
            )
            signals = result.scalars().all()

            return [
                {
                    "signal_id": str(s.signal_id),
                    "signal_type": s.signal_type,
                    "source_fact_id": str(s.source_fact_id) if s.source_fact_id else None,
                    "expected_record_type": s.expected_record_type,
                    "expected_from_provider_id": str(s.expected_from_provider_id) if s.expected_from_provider_id else None,
                    "expected_date_range_start": s.expected_date_range_start.isoformat() if s.expected_date_range_start else None,
                    "expected_date_range_end": s.expected_date_range_end.isoformat() if s.expected_date_range_end else None,
                    "days_overdue": s.days_overdue,
                    "resolved": s.resolved,
                }
                for s in signals
            ]

    async def rescan_case(
        self,
        case_id: uuid.UUID,
        redacted_pages: list[dict[str, Any]],
    ) -> ExtractionResult:
        """Full rescan: extract facts, detect contradictions, generate missing-evidence signals.

        This is the main entry point called after new documents arrive or OCR completes.
        """
        result = await self.extract_facts_from_pages(case_id, redacted_pages)
        result.contradictions_found = await self.detect_contradictions(case_id)
        result.missing_evidence_signals = await self.generate_missing_evidence_signals(case_id)
        return result


_evidence_service: EvidenceService | None = None


def get_evidence_service() -> EvidenceService:
    global _evidence_service
    if _evidence_service is None:
        _evidence_service = EvidenceService()
    return _evidence_service
