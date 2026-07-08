"""Provider extraction from the Benjamin intake transcript.

Spec LOCKS spaCy + scispaCy ``en_core_sci_md`` for clinical NLP. That model is
heavy and optional in dev/test, so this module uses it when available and falls
back to a deterministic rule-based extractor otherwise. Output is a list of
provider-name hints, which the existing NPI pipeline (``services.providers``)
resolves and turns into UNCONFIRMED provider records for attorney confirmation.
"""

from __future__ import annotations

import re

from app.core.logging import get_logger

logger = get_logger("trace.extractor")

_FACILITY_KEYWORDS = (
    "Hospital",
    "Medical Center",
    "Medical Group",
    "Clinic",
    "Health Center",
    "Health System",
    "Urgent Care",
    "Orthopedics",
    "Orthopedic",
    "Radiology",
    "Imaging",
    "Physical Therapy",
    "Rehabilitation",
    "Emergency Room",
    "Surgery Center",
    "Pain Management",
)

# "Dr. Jane Smith" / "Doctor Smith"
_DOCTOR_RE = re.compile(r"\b(?:Dr\.?|Doctor)\s+([A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+)?)")

# A run of Capitalized tokens ending in a facility keyword, e.g.
# "Cedars-Sinai Medical Center", "LA Ortho Clinic".
_FACILITY_RE = re.compile(
    r"\b((?:[A-Z][\w'&.\-]+\s+){0,4}(?:" + "|".join(k.replace(" ", r"\s+") for k in _FACILITY_KEYWORDS) + r"))"
)


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def _rule_based(text: str) -> list[str]:
    hints: list[str] = []
    hints += [m.group(1).strip() for m in _FACILITY_RE.finditer(text)]
    hints += [f"Dr. {m.group(1).strip()}" for m in _DOCTOR_RE.finditer(text)]
    return _dedupe(hints)


def _spacy_orgs(text: str) -> list[str]:
    """Best-effort scispaCy ORG extraction. Returns [] if the model isn't installed."""
    try:
        import spacy  # type: ignore[import-not-found]
    except ImportError:
        return []
    try:
        nlp = spacy.load("en_core_sci_md")
    except Exception:  # noqa: BLE001 — model not installed in this environment
        logger.info("en_core_sci_md not available; using rule-based extraction only")
        return []
    doc = nlp(text)
    return [ent.text.strip() for ent in doc.ents if ent.label_ in {"ORG", "PERSON", "GPE"}]


def extract_provider_hints(text: str, *, use_spacy: bool = True) -> list[str]:
    """Return de-duplicated provider-name hints found in the transcript text."""
    if not text:
        return []
    hints = _rule_based(text)
    if use_spacy:
        hints = _dedupe(hints + _spacy_orgs(text))
    return hints
