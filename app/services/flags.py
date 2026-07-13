"""Extended Flag Registry — Tier 1 algorithmic flags.

Phase 1D Deliverable 4: six algorithmic flags using string match + date math.
All run on REDACTED text — never raw PHI. Every flag carries provenance
JSONB metadata for attorney deposition traceability.

Flag priority:
    PRIORITY — blocks demand-ready gate (attorney annotation required)
    ADVISORY — surfaced, does not block demand-ready
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum


class FlagPriority(str, Enum):
    PRIORITY = "PRIORITY"
    ADVISORY = "ADVISORY"


@dataclass
class FlagResult:
    flag_id: uuid.UUID
    case_id: uuid.UUID
    flag_type: str
    priority: FlagPriority
    description: str
    rule_name: str
    rule_version: str = "1.0"
    matched_string: str | None = None
    matched_in_entry_id: uuid.UUID | None = None
    source_doc_before: uuid.UUID | None = None
    source_doc_after: uuid.UUID | None = None
    provenance: dict = field(default_factory=dict)

    def to_event_node(self) -> dict:
        return {
            "node_id": str(self.flag_id),
            "case_id": str(self.case_id),
            "flag_type": self.flag_type,
            "system_description": self.description,
            "provenance": self.provenance,
            "attorney_annotation": None,
        }


# ── Non-compliant language lexicon ──
NON_COMPLIANT_PATTERNS: list[str] = [
    "non-compliant", "non compliant", "noncompliant",
    "missed appointment", "did not attend", "no show",
    "against medical advice", "AMA",
    "refused treatment", "declined treatment",
    "patient did not follow", "did not complete",
    "unable to comply", "non-adherent",
]

# ── Clinician credibility language lexicon ──
CREDIBILITY_PATTERNS: list[str] = [
    "exaggerating", "exaggeration",
    "malingering", "malinger",
    "secondary gain",
    "subjective complaint", "subjective only",
    "drug seeking", "drug-seeking",
    "inconsistent history", "inconsistent with",
    "symptoms out of proportion",
    "functional overlay",
    "symptom magnification",
    "pain behavior", "pain behaviours",
]


def _build_provenance(rule_name: str, matched: str | None = None, entry_id: uuid.UUID | None = None) -> dict:
    return {
        "rule_name": rule_name,
        "rule_version": "1.0",
        "detection_method": "string_match",
        "matched_string": matched,
        "matched_in_entry_id": str(entry_id) if entry_id else None,
        "threshold_applied": None,
        "model_name": None,
        "model_version": None,
        "confidence": None,
    }


def detect_delayed_initial_treatment(
    case_id: uuid.UUID,
    incident_date: date,
    first_event_date: date | None,
) -> FlagResult | None:
    """T1-01: Gap between incident date and first clinical encounter."""
    if first_event_date is None:
        return None
    gap_days = (first_event_date.date() - incident_date).days if hasattr(first_event_date, 'date') else (first_event_date - incident_date).days
    if gap_days < 4:
        return None
    priority = FlagPriority.PRIORITY if gap_days >= 8 else FlagPriority.ADVISORY
    return FlagResult(
        flag_id=uuid.uuid4(), case_id=case_id, flag_type="DELAYED_INITIAL_TREATMENT",
        priority=priority, rule_name="delayed_initial_treatment",
        description=f"Incident date {incident_date}. First recorded treatment: {first_event_date}. Gap: {gap_days} days.",
        provenance=_build_provenance("delayed_initial_treatment"),
    )


def detect_sudden_treatment_stop(
    case_id: uuid.UUID,
    last_entry_text: str,
    entry_id: uuid.UUID,
) -> FlagResult | None:
    """T1-02: Last entry for a provider with no discharge/MMI/referral notation."""
    stop_patterns = r"\b(?:discharg|MMI|maximum medical|released|referred to|follow.up with)"
    if re.search(stop_patterns, last_entry_text, re.IGNORECASE):
        return None
    return FlagResult(
        flag_id=uuid.uuid4(), case_id=case_id, flag_type="SUDDEN_TREATMENT_STOP",
        priority=FlagPriority.PRIORITY, rule_name="sudden_treatment_stop",
        description=f"Treatment ends with no discharge note, MMI notation, or referral documented.",
        matched_string=last_entry_text[:200],
        matched_in_entry_id=entry_id,
        provenance=_build_provenance("sudden_treatment_stop", last_entry_text[:200], entry_id),
    )


def detect_follow_up_not_found(
    case_id: uuid.UUID,
    entry_text: str,
    entry_id: uuid.UUID,
    subsequent_dates: list[date],
) -> FlagResult | None:
    """T1-03: Follow-up recommended but no corresponding entry found within 60 days."""
    fu_match = re.search(
        r"\b(?:follow.up\s+(?:in|within)\s+(\d+)\s+(?:day|week)|"
        r"refer(?:red)?\s+to\s+(?:orthopedic|physical\s+therapy|specialist|"
        r"surgery|neurology|cardiology|imaging)|"
        r"MRI\s+ordered|CT\s+ordered|X-ray\s+ordered|"
        r"return\s+(?:to\s+clinic|in\s+\d+\s+(?:day|week)))",
        entry_text, re.IGNORECASE,
    )
    if not fu_match:
        return None

    if not subsequent_dates:
        is_imaging = bool(re.search(r"MRI|CT|X-ray|imaging", fu_match.group(0), re.IGNORECASE))
        priority = FlagPriority.PRIORITY if is_imaging else FlagPriority.ADVISORY
        return FlagResult(
            flag_id=uuid.uuid4(), case_id=case_id, flag_type="FOLLOW_UP_NOT_FOUND",
            priority=priority, rule_name="follow_up_not_found",
            description=f"Follow-up recommended: '{fu_match.group(0)[:100]}'. No corresponding entry found.",
            matched_string=fu_match.group(0)[:100],
            matched_in_entry_id=entry_id,
            provenance=_build_provenance("follow_up_not_found", fu_match.group(0)[:100], entry_id),
        )
    return None


def detect_non_compliant_language(
    case_id: uuid.UUID,
    entry_text: str,
    entry_id: uuid.UUID,
) -> list[FlagResult]:
    """T1-04: Non-compliant patient language — every instance is PRIORITY."""
    flags: list[FlagResult] = []
    for pattern in NON_COMPLIANT_PATTERNS:
        if pattern.lower() in entry_text.lower():
            flags.append(FlagResult(
                flag_id=uuid.uuid4(), case_id=case_id, flag_type="NON_COMPLIANT_LANGUAGE",
                priority=FlagPriority.PRIORITY, rule_name="non_compliant_language",
                description=f"Clinical note contains: '{pattern}'. Attorney review required.",
                matched_string=pattern, matched_in_entry_id=entry_id,
                provenance=_build_provenance("non_compliant_language", pattern, entry_id),
            ))
    return flags


def detect_bill_without_procedure_report(
    case_id: uuid.UUID,
    cpt_code: str,
    service_date: date,
    documents_in_set: list[dict],
) -> FlagResult | None:
    """T1-05: CPT code billed with no corresponding procedure/imaging report."""
    proc_match = re.match(r"^(\d{5})$", cpt_code)
    if not proc_match:
        return None
    code = int(cpt_code)
    is_procedure = 10000 <= code <= 69999 or 70000 <= code <= 79999 or 90000 <= code <= 99099
    if not is_procedure:
        return None

    for doc in documents_in_set:
        doc_date = doc.get("date")
        if doc_date and abs((service_date - doc_date).days) <= 7:
            return None  # Found matching report

    return FlagResult(
        flag_id=uuid.uuid4(), case_id=case_id, flag_type="BILL_WITHOUT_REPORT",
        priority=FlagPriority.PRIORITY, rule_name="bill_without_report",
        description=f"CPT {cpt_code} billed on {service_date}. No corresponding procedure or imaging report found within 7 days.",
        provenance=_build_provenance("bill_without_report", cpt_code),
    )


def detect_clinician_credibility_language(
    case_id: uuid.UUID,
    entry_text: str,
    entry_id: uuid.UUID,
) -> list[FlagResult]:
    """T1-06: Clinician credibility language — every instance is PRIORITY."""
    flags: list[FlagResult] = []
    for pattern in CREDIBILITY_PATTERNS:
        if pattern.lower() in entry_text.lower():
            flags.append(FlagResult(
                flag_id=uuid.uuid4(), case_id=case_id, flag_type="CLINICIAN_CREDIBILITY_LANGUAGE",
                priority=FlagPriority.PRIORITY, rule_name="clinician_credibility_language",
                description=f"Clinical note contains: '{pattern}'. Attorney review required.",
                matched_string=pattern, matched_in_entry_id=entry_id,
                provenance=_build_provenance("clinician_credibility_language", pattern, entry_id),
            ))
    return flags


def run_all_tier1_flags(
    case_id: uuid.UUID,
    incident_date: date,
    chronology_entries: list[dict],
    billing_records: list[dict] | None = None,
) -> list[FlagResult]:
    """Run all Tier 1 flag detectors against a completed chronology.

    Returns list of FlagResult objects ready for event_node creation.
    """
    all_flags: list[FlagResult] = []

    if chronology_entries:
        first_date = min(
            (e.get("event_date") for e in chronology_entries if e.get("event_date")),
            default=None,
        )
        d1 = detect_delayed_initial_treatment(case_id, incident_date, first_date)
        if d1:
            all_flags.append(d1)

    for entry in chronology_entries:
        entry_id = entry.get("entry_id")
        entry_date = entry.get("event_date")
        text = entry.get("clinical_description", "")

        d2 = detect_sudden_treatment_stop(case_id, text, entry_id)
        if d2:
            all_flags.append(d2)

        # Compute subsequent dates for T1-03 follow-up check
        subsequent_dates = [
            e.get("event_date")
            for e in chronology_entries
            if e.get("event_date") and entry_date and e.get("event_date") > entry_date
        ]
        d3 = detect_follow_up_not_found(case_id, text, entry_id, subsequent_dates)
        if d3:
            all_flags.append(d3)

        all_flags.extend(detect_non_compliant_language(case_id, text, entry_id))
        all_flags.extend(detect_clinician_credibility_language(case_id, text, entry_id))

    if billing_records:
        # Build document set for T1-05 cross-check
        documents_in_set = [
            {"document_id": e.get("source_document_id"), "date": e.get("event_date")}
            for e in chronology_entries if e.get("source_document_id")
        ]
        for bill in billing_records:
            d5 = detect_bill_without_procedure_report(
                case_id, bill.get("cpt_code", ""), bill.get("service_date", date.today()),
                documents_in_set,
            )
            if d5:
                all_flags.append(d5)

    return all_flags
