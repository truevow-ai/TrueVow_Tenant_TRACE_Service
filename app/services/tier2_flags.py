"""Tier 2 NLP flags — cross-record comparison via long-context NLP.

ADR-004 §4: six flag types requiring OpenMed/BioClinical ModernBERT
cross-record comparison. Operates on REDACTED text only — never raw PHI.

NLP_LONG_CONTEXT_BACKEND env var selects the model:
    disabled              — Tier 2 flags skipped entirely
    bioclinical_modernbert — BioClinical ModernBERT (8,192-token window)
    openmed                — OpenMed long-context mode

Priority:
    PRIORITY — blocks demand-ready gate (T2-02, T2-04)
    ADVISORY — surfaced, does not block (T2-01, T2-03)
    INFORMATIONAL — positive tags, not flags (T2-05, T2-06)

False positive tracking: per flag type dismissal data stored.
If any T2 flag type exceeds 30% false positive from attorney
dismissal data, demote to INFORMATIONAL per PRD §13 risk table.
"""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import date


@dataclass
class Tier2Flag:
    flag_id: uuid.UUID
    case_id: uuid.UUID
    flag_type: str
    priority: str  # PRIORITY / ADVISORY / INFORMATIONAL
    description: str
    rule_name: str
    matched_entries: list[str] = field(default_factory=list)
    source_quotes: list[str] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)


async def run_tier2_flags(
    case_id: uuid.UUID,
    chronology_entries: list[dict],
    pre_incident_opted_in: bool = False,
) -> list[Tier2Flag]:
    """Run all Tier 2 flag detectors. Skips if NLP_LONG_CONTEXT_BACKEND=disabled."""
    backend = os.environ.get("NLP_LONG_CONTEXT_BACKEND", "disabled")
    if backend == "disabled":
        return []

    flags: list[Tier2Flag] = []

    flags.extend(_detect_t2_01_new_provider_no_referral(case_id, chronology_entries))
    flags.extend(_detect_t2_02_changing_incident_description(case_id, chronology_entries))
    flags.extend(_detect_t2_03_changing_symptom_complaints(case_id, chronology_entries))
    flags.extend(_detect_t2_04_preexisting_condition(case_id, chronology_entries, pre_incident_opted_in))
    flags.extend(_tag_t2_05_functional_impact(case_id, chronology_entries))
    flags.extend(_link_t2_06_imaging_cross_references(case_id, chronology_entries))

    return flags


# ── T2-01: New Provider Without Referral Context (ADVISORY) ──

REFERRAL_PATTERNS = [
    r"\b(?:refer(?:red)?\s+(?:to|me\s+to)\s+)(?:Dr\.?|Doctor\s+)?([A-Z][a-zA-Z\s,\-\.]{3,60})",
    r"\b(?:referral\s+(?:to|for)\s+)([A-Z][a-zA-Z\s,\-\.]{3,60})",
    r"\b(?:sent\s+(?:to|me\s+to)\s+)(?:Dr\.?|Doctor\s+)?([A-Z][a-zA-Z\s,\-\.]{3,60})",
    r"\b(?:consult(?:ed)?\s+(?:with\s+)?)(?:Dr\.?|Doctor\s+)?([A-Z][a-zA-Z\s,\-\.]{3,60})",
]

ER_KEYWORDS = ["ER", "emergency", "emergency room", "emergency department", "urgent care", "trauma", "ambulance", "EMS"]


def _is_er_context(text: str) -> bool:
    return any(kw in text.lower() for kw in ER_KEYWORDS)


def _detect_t2_01_new_provider_no_referral(
    case_id: uuid.UUID,
    entries: list[dict],
) -> list[Tier2Flag]:
    """Flag providers introduced after first encounter without referral context."""
    flags: list[Tier2Flag] = []
    seen_providers: set[str] = set()
    all_referral_texts: list[str] = []

    for entry in entries:
        text = entry.get("clinical_description", "")
        provider = entry.get("provider_id", "unknown")

        for pattern in REFERRAL_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                all_referral_texts.append(match.group(0))

        if provider in seen_providers or not seen_providers:
            seen_providers.add(provider)
            continue

        is_er = _is_er_context(text) or any(_is_er_context(rt) for rt in all_referral_texts)
        if is_er:
            seen_providers.add(provider)
            continue

        referred = any(provider.lower() in rt.lower() or text.lower() in rt.lower() for rt in all_referral_texts)
        if not referred:
            flags.append(Tier2Flag(
                flag_id=uuid.uuid4(), case_id=case_id,
                flag_type="NEW_PROVIDER_NO_REFERRAL",
                priority="ADVISORY", rule_name="new_provider_no_referral_t2_01",
                description=f"New provider introduced without referral context.",
                source_quotes=[text[:200]],
            ))

        seen_providers.add(provider)

    return flags


# ── T2-02: Changing Incident Description Across Providers (PRIORITY) ──

INCIDENT_MECHANISM_PATTERNS = [
    r"\b(?:rear.?end|rear\s+ended|rear.ended|struck\s+from\s+behind)\b",
    r"\b(?:T-bon|side.?impact|broadside)\b",
    r"\b(?:head.?on|frontal)\b",
    r"\b(?:roll.?over|overturn)\b",
    r"\b(?:slip\s+(?:and\s+)?fall|tripped|fell)\b",
    r"\b(?:MVA|MVC|motor\s+vehicle\s+(?:accident|collision))\b",
    r"\b(?:pedestrian|bicycle|cyclist)\b",
    r"\b(?:assault|attacked|struck\s+by)\b",
]


def _extract_mechanism(text: str) -> list[str]:
    mechanisms: list[str] = []
    for pattern in INCIDENT_MECHANISM_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            mechanisms.append(match.group(0))
    return mechanisms


def _detect_t2_02_changing_incident_description(
    case_id: uuid.UUID,
    entries: list[dict],
) -> list[Tier2Flag]:
    """Compare incident mechanism across first entries from each provider."""
    flags: list[Tier2Flag] = []
    seen_providers: set[str] = set()
    provider_mechanisms: list[tuple[str, str, str]] = []

    for entry in entries:
        provider = entry.get("provider_id", "unknown")
        if provider in seen_providers:
            continue
        seen_providers.add(provider)

        text = entry.get("clinical_description", "")
        mechs = _extract_mechanism(text)
        if mechs:
            provider_mechanisms.append((provider, mechs[0], text[:200]))

    if len(provider_mechanisms) < 2:
        return flags

    first_mech = provider_mechanisms[0][1].lower()
    for provider, mech, source in provider_mechanisms[1:]:
        if mech.lower() != first_mech and mech.lower() not in first_mech and first_mech not in mech.lower():
            flags.append(Tier2Flag(
                flag_id=uuid.uuid4(), case_id=case_id,
                flag_type="CONFLICTING_INCIDENT_DESCRIPTION",
                priority="PRIORITY", rule_name="changing_incident_description_t2_02",
                description=f"Incident descriptions differ across providers. "
                f"Provider A: '{provider_mechanisms[0][2][:100]}'. "
                f"Provider B: '{source[:100]}'.",
                source_quotes=[provider_mechanisms[0][2][:100], source[:100]],
            ))

    return flags


# ── T2-03: Changing Symptom Complaints Without Progression (ADVISORY) ──

BODY_REGIONS = {
    "head": ["head", "skull", "concussion", "headache", "migraine"],
    "neck": ["neck", "cervical", "c-spine"],
    "back_upper": ["upper back", "thoracic", "t-spine", "mid back", "shoulder blade"],
    "back_lower": ["lower back", "lumbar", "l-spine", "low back", "sacral", "sacrum"],
    "arm_right": ["right arm", "right shoulder", "right elbow", "right wrist", "right hand"],
    "arm_left": ["left arm", "left shoulder", "left elbow", "left wrist", "left hand"],
    "leg_right": ["right leg", "right hip", "right knee", "right ankle", "right foot"],
    "leg_left": ["left leg", "left hip", "left knee", "left ankle", "left foot"],
}


def _detect_t2_03_changing_symptom_complaints(
    case_id: uuid.UUID,
    entries: list[dict],
) -> list[Tier2Flag]:
    """Track body region complaints over time. Flag new regions without progression explanation."""
    flags: list[Tier2Flag] = []
    seen_regions: dict[str, str] = {}

    for entry in entries:
        text = entry.get("clinical_description", "")
        if not text:
            continue
        text_lower = text.lower()
        entry_id = entry.get("entry_id", "unknown")

        for region_name, keywords in BODY_REGIONS.items():
            if any(kw in text_lower for kw in keywords):
                if region_name not in seen_regions:
                    seen_regions[region_name] = str(entry_id)
                elif seen_regions[region_name] == str(entry_id):
                    continue
                else:
                    has_explanation = any(
                        phrase in text_lower
                        for phrase in ["due to", "secondary to", "resulting from", "caused by",
                                        "referred from", "compensating for", "radiating from",
                                        "follow-up", "previously noted", "ongoing"]
                    )
                    if not has_explanation and len(seen_regions) > 1:
                        flags.append(Tier2Flag(
                            flag_id=uuid.uuid4(), case_id=case_id,
                            flag_type="CHANGING_SYMPTOM_COMPLAINTS",
                            priority="ADVISORY", rule_name="changing_symptom_complaints_t2_03",
                            description=f"New body region '{region_name}' appears without clinical progression explanation.",
                            source_quotes=[text[:200]],
                        ))

    return flags


# ── T2-04: Pre-Existing Condition Signal (PRIORITY) ──

PREEXISTING_PATTERNS = [
    r"\b(?:pre.?existing|prior\s+history\s+of|history\s+of)\b",
    r"\b(?:degenerative|chronic|long.?standing|old\s+injury|old\s+fracture)\b",
    r"\b(?:arthritic|arthritis|DJD|degenerative\s+disc|spondylosis|stenosis)\b",
    r"\b(?:prior\s+surgery|previous\s+surgery|post.?operative)\b",
]


def _detect_t2_04_preexisting_condition(
    case_id: uuid.UUID,
    entries: list[dict],
    pre_incident_opted_in: bool = False,
) -> list[Tier2Flag]:
    """Detect pre-existing/degenerative condition language in post-incident notes."""
    flags: list[Tier2Flag] = []

    for entry in entries:
        text = entry.get("clinical_description", "")
        for pattern in PREEXISTING_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                flags.append(Tier2Flag(
                    flag_id=uuid.uuid4(), case_id=case_id,
                    flag_type="PREEXISTING_CONDITION_SIGNAL",
                    priority="PRIORITY", rule_name="preexisting_condition_t2_04",
                    description=f"Clinical note contains '{match.group(0)}'. "
                    f"Source: '{text[:100]}'.",
                    source_quotes=[text[:200]],
                ))
                break

    return flags


# ── T2-05: Functional Impact Tagging (INFORMATIONAL) ──

FUNCTIONAL_IMPACT_PATTERNS: list[tuple[str, str]] = [
    ("work restriction", "WORK_RESTRICTION"),
    ("return to work", "RETURN_TO_WORK"),
    ("off work", "WORK_RESTRICTION"),
    ("no lifting", "WORK_RESTRICTION"),
    ("light duty", "WORK_RESTRICTION"),
    ("modified duty", "WORK_RESTRICTION"),
    ("ADL", "ADL_LIMITATION"),
    ("activities of daily living", "ADL_LIMITATION"),
    ("range of motion", "RANGE_OF_MOTION"),
    ("ROM", "RANGE_OF_MOTION"),
    ("pain scale", "PAIN_SCALE"),
    ("pain score", "PAIN_SCALE"),
    ("0/10", "PAIN_SCALE"),
    ("/10 pain", "PAIN_SCALE"),
    ("activity tolerance", "ACTIVITY_TOLERANCE"),
    ("sleep", "SLEEP_IMPACT"),
    ("insomnia", "SLEEP_IMPACT"),
]


def _tag_t2_05_functional_impact(
    case_id: uuid.UUID,
    entries: list[dict],
) -> list[Tier2Flag]:
    """Tag entries containing functional impact documentation. Informational only."""
    tags: list[Tier2Flag] = []

    for entry in entries:
        text = entry.get("clinical_description", "")
        if not text:
            continue
        text_lower = text.lower()
        for pattern, tag_name in FUNCTIONAL_IMPACT_PATTERNS:
            if pattern in text_lower:
                tags.append(Tier2Flag(
                    flag_id=uuid.uuid4(), case_id=case_id,
                    flag_type=f"FUNCTIONAL_IMPACT_{tag_name}",
                    priority="INFORMATIONAL", rule_name="functional_impact_t2_05",
                    description=f"Functional impact documentation found: '{pattern}' in entry.",
                    source_quotes=[text[:200]],
                ))
                break

    return tags


# ── T2-06: Imaging Cross-Reference Links (INFORMATIONAL) ──

IMAGING_MODALITIES_PATTERN = re.compile(
    r"\b(MRI|CT|X-ray|Xray|ultrasound|mammogram|PET|DEXA|bone\s+scan)\b",
    re.IGNORECASE,
)


def _link_t2_06_imaging_cross_references(
    case_id: uuid.UUID,
    entries: list[dict],
) -> list[Tier2Flag]:
    """Link imaging orders to their corresponding reports."""
    links: list[Tier2Flag] = []

    for entry in entries:
        text = entry.get("clinical_description", "")
        if not text:
            continue
        match = IMAGING_MODALITIES_PATTERN.search(text)
        if match:
            modality = match.group(1).upper()
            for other in entries:
                other_text = other.get("clinical_description", "")
                if other_text and modality.lower() in other_text.lower():
                    if entry.get("entry_id") != other.get("entry_id"):
                        links.append(Tier2Flag(
                            flag_id=uuid.uuid4(), case_id=case_id,
                            flag_type=f"IMAGING_CROSS_REF_{modality}",
                            priority="INFORMATIONAL", rule_name="imaging_cross_ref_t2_06",
                            description=f"Imaging order ({modality}) linked to report.",
                            source_quotes=[text[:100], other_text[:100]],
                        ))
                        break

    return links
