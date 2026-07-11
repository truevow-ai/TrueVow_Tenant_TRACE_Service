"""Chronology engine — clinical event extraction from redacted OCR text.

Phase 1D Deliverable 3: runs OpenMed clinical NER on de-identified text.
Never processes raw PHI. Produces source-linked chronology entries with
deduplication flags and review status tracking.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date as date_type, datetime, timezone
from enum import Enum


# ── Date extraction patterns for clinical text ──
DATE_PATTERNS: list[tuple[str, str]] = [
    # "01/15/2025", "1/15/25", "01/15/25"
    (r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b", "%m/%d/%Y"),
    # "2025-01-15", "2025-1-15"
    (r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", "%Y-%m-%d"),
    # "January 15, 2025", "Jan 15 2025"
    (r"\b(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
     r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
     r"Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\b", "%B %d %Y"),
    # "15 January 2025", "15 Jan 2025"
    (r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|"
     r"Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|"
     r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?),?\s+(\d{4})\b", "%d %B %Y"),
]

MONTH_MAP: dict[str, int] = {
    "jan": 1, "january": 1, "feb": 2, "february": 2,
    "mar": 3, "march": 3, "apr": 4, "april": 4,
    "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def _extract_date(text: str) -> datetime | None:
    """Extract the first recognizable date from clinical text."""
    for pattern, fmt in DATE_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            try:
                if len(groups) == 3 and groups[0].isdigit() and groups[1].isdigit() and groups[2].isdigit():
                    month = int(groups[0])
                    day = int(groups[1])
                    year = int(groups[2])
                    if year < 100:
                        year += 2000
                elif len(groups) == 3 and not groups[0].isdigit():
                    month = MONTH_MAP.get(groups[0].lower()[:3], 1)
                    day = int(groups[1])
                    year = int(groups[2])
                elif len(groups) == 3:
                    day = int(groups[0])
                    month = MONTH_MAP.get(groups[1].lower()[:3], 1)
                    year = int(groups[2])
                else:
                    continue
                if 1 <= month <= 12 and 1 <= day <= 31:
                    return datetime(year, month, day, tzinfo=timezone.utc)
            except (ValueError, IndexError):
                continue
    return None


class EventType(str, Enum):
    VISIT = "VISIT"
    IMAGING = "IMAGING"
    PRESCRIPTION = "PRESCRIPTION"
    PROCEDURE = "PROCEDURE"
    DISCHARGE = "DISCHARGE"
    REFERRAL = "REFERRAL"


class ReviewStatus(str, Enum):
    UNREVIEWED = "UNREVIEWED"
    CONFIRMED = "CONFIRMED"
    EDITED = "EDITED"
    DISMISSED = "DISMISSED"
    NEEDS_MORE_RECORDS = "NEEDS_MORE_RECORDS"


@dataclass
class ChronologyEntry:
    entry_id: uuid.UUID
    case_id: uuid.UUID
    event_date: datetime
    provider_id: uuid.UUID | None
    facility_name: str | None
    event_type: EventType
    clinical_description: str
    source_document_id: uuid.UUID
    source_page_number: int
    flag_node_id: uuid.UUID | None = None
    attorney_annotation: str | None = None
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    functional_impact_tags: list[str] = field(default_factory=list)
    is_potential_duplicate: bool = False
    duplicate_from_entry: uuid.UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ChronologyResult:
    case_id: uuid.UUID
    entries: list[ChronologyEntry] = field(default_factory=list)
    total_entries: int = 0
    potential_duplicates: int = 0

    @property
    def entries_by_date(self) -> list[ChronologyEntry]:
        return sorted(self.entries, key=lambda e: e.event_date)

    def to_api_response(self) -> dict:
        return {
            "case_id": str(self.case_id),
            "total_entries": self.total_entries,
            "potential_duplicates": self.potential_duplicates,
            "entries": [
                {
                    "entry_id": str(e.entry_id),
                    "event_date": e.event_date.isoformat(),
                    "provider_id": str(e.provider_id) if e.provider_id else None,
                    "facility": e.facility_name,
                    "event_type": e.event_type.value,
                    "clinical_description": e.clinical_description[:200],
                    "source_document_id": str(e.source_document_id),
                    "source_page_number": e.source_page_number,
                    "flag_node_id": str(e.flag_node_id) if e.flag_node_id else None,
                    "review_status": e.review_status.value,
                    "functional_impact_tags": e.functional_impact_tags,
                    "is_potential_duplicate": e.is_potential_duplicate,
                }
                for e in self.entries_by_date
            ],
        }


async def build_chronology(
    case_id: uuid.UUID,
    redacted_pages: list[dict],
) -> ChronologyResult:
    """Build chronology from de-identified OCR text. Never touches raw PHI."""
    from app.services.nlp import create_openmed_service

    nlp = create_openmed_service()
    result = ChronologyResult(case_id=case_id)
    seen_events: set[tuple[datetime, str, EventType]] = set()

    for page in redacted_pages:
        text = page.get("redacted_text", "")
        if not text:
            continue

        ner_result = await nlp.extract_clinical_entities(text)
        for entity in ner_result.entities:
            event_date = _extract_date(text) or _extract_date(entity.text)
            quality_flags: list[str] = []
            if event_date is None:
                quality_flags.append("DATE_NOT_FOUND")
            provider_id = page.get("provider_id")
            event_type = _classify_event_type(entity.label)
            clinical = entity.text[:500]

            event_key = (event_date.replace(second=0, microsecond=0), entity.text[:100], event_type)
            entry = ChronologyEntry(
                entry_id=uuid.uuid4(),
                case_id=case_id,
                event_date=event_date,
                provider_id=uuid.UUID(provider_id) if provider_id else None,
                facility_name=page.get("facility_name"),
                event_type=event_type,
                clinical_description=clinical,
                source_document_id=uuid.UUID(page.get("document_id", str(uuid.uuid4()))),
                source_page_number=page.get("page_number", 1),
            )

            if event_key in seen_events:
                entry.is_potential_duplicate = True
                result.potential_duplicates += 1

            seen_events.add(event_key)
            result.entries.append(entry)

    result.total_entries = len(result.entries)
    return result


def _classify_event_type(entity_label: str) -> EventType:
    mapping = {
        "PROVIDER": EventType.VISIT,
        "DISEASE": EventType.VISIT,
        "DRUG": EventType.PRESCRIPTION,
        "MEDICATION": EventType.PRESCRIPTION,
        "PROCEDURE": EventType.PROCEDURE,
        "IMAGING": EventType.IMAGING,
        "ANATOMY": EventType.VISIT,
    }
    return mapping.get(entity_label.upper(), EventType.VISIT)
