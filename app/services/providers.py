"""Provider extraction via OpenMed NER + NPI Registry lookup.

Phase 1C (ADR-003): extracts provider candidates from Benjamin intake
transcripts using OpenMed v1.7.x NER, then enriches each candidate via
NPI lookup. Stores model_version, source_span, and source_quote for
tracing. Confidence taxonomy from ADR-001 §24.2 (not HIGH/MEDIUM/LOW).
"""

from __future__ import annotations

import uuid

from app.core.database import async_session_maker
from app.core.logging import get_logger
from app.models.provider import Provider
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
) -> int:
    """Create UNCONFIRMED provider records for each hint. Returns count created."""
    if not provider_hints:
        return 0
    npi = npi_client or NPIClient()

    created = 0
    async with async_session_maker() as session:
        for hint in provider_hints:
            hint = hint.strip()
            if not hint:
                continue
            try:
                matches = await npi.search(hint, jurisdiction_state)
            except Exception:  # noqa: BLE001 — lookup failure must not abort extraction
                logger.exception("NPI lookup failed for %r", hint)
                matches = []

            confidence = _confidence_from_npi(matches)
            top = matches[0] if matches else {}
            session.add(
                Provider(
                    case_id=case_id,
                    provider_name=top.get("name") or hint,
                    npi_number=top.get("npi_number"),
                    facility_name=top.get("facility"),
                    fax_number=top.get("fax"),
                    address=top.get("address"),
                    specialty=top.get("specialty"),
                    confirmation_status="UNCONFIRMED",
                    retrieval_status="PENDING",
                    extraction_confidence=confidence,
                    source_reference=f"openmed:{OPENMED_MODEL_VERSION}:{hint}",
                )
            )
            created += 1
        await session.commit()
    return created
