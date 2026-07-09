"""Provider extraction via NLP + NPI Registry lookup.

Phase 1C (ADR-003): extracts provider candidates from Benjamin intake
transcripts using NLP (OpenMed v1.7.x when installed, regex-based
NER fallback when not). Enriches each candidate via NPI lookup.
Stores model_version, source_span, and source_quote for tracing.

Confidence taxonomy from ADR-001 §24.2 (not HIGH/MEDIUM/LOW).
"""

from __future__ import annotations

import uuid

from app.core.database import async_session_maker
from app.core.logging import get_logger
from app.models.provider import Provider
from app.services.nlp import create_openmed_service
from app.services.npi import NPIClient, _assign_confidence

logger = get_logger("trace.providers")

OPENMED_MODEL_VERSION = "1.7.0"


def _confidence_from_npi(matches: list[dict]) -> str:
    return _assign_confidence(len(matches))


async def extract_providers(
    case_id: uuid.UUID,
    provider_hints: list[str],
    jurisdiction_state: str | None = None,
    *,
    npi_client: NPIClient | None = None,
    transcript: str | None = None,
) -> int:
    """Extract providers from hints AND intake transcript, enrich via NPI.

    If transcript is provided, runs NLP extraction on it to find additional
    provider references beyond the structured hints. Deduplicates results.
    """
    npi = npi_client or NPIClient()
    nlp = create_openmed_service()

    all_names: set[str] = set(h.strip() for h in provider_hints if h.strip())

    if transcript:
        transcript_names = await nlp.extract_providers_from_transcript(transcript)
        all_names.update(transcript_names)
        logger.info(
            "NLP extraction: %d from hints + %d from transcript = %d unique",
            len(provider_hints), len(transcript_names), len(all_names),
        )

    if not all_names:
        return 0

    created = 0
    async with async_session_maker() as session:
        for name in sorted(all_names):
            try:
                matches = await npi.search(name, jurisdiction_state)
            except Exception:  # noqa: BLE001 — lookup failure must not abort extraction
                logger.exception("NPI lookup failed for %r", name)
                matches = []

            confidence = _confidence_from_npi(matches)
            top = matches[0] if matches else {}
            session.add(
                Provider(
                    case_id=case_id,
                    provider_name=top.get("name") or name,
                    npi_number=top.get("npi_number"),
                    facility_name=top.get("facility"),
                    fax_number=top.get("fax"),
                    address=top.get("address"),
                    specialty=top.get("specialty"),
                    confirmation_status="UNCONFIRMED",
                    retrieval_status="PENDING",
                    extraction_confidence=confidence,
                    source_reference=f"openmed:{OPENMED_MODEL_VERSION}:{name}",
                )
            )
            created += 1
        await session.commit()
    return created
