"""Provider extraction skeleton (spec §5.1).

Phase 1B: takes provider name hints (in Phase 1C these will come from spaCy NER
over the Benjamin intake transcript), looks each up in the NPI Registry, and
creates UNCONFIRMED provider records with a confidence label for the attorney to
confirm. The NPI client is injectable for testing.
"""

from __future__ import annotations

import uuid

from app.core.database import async_session_maker
from app.core.logging import get_logger
from app.models.provider import Provider
from app.services.npi import NPIClient

logger = get_logger("trace.providers")


def _confidence(matches: list[dict]) -> str:
    if len(matches) == 1 and matches[0].get("specialty"):
        return "HIGH"
    if matches:
        return "MEDIUM"  # multiple/partial matches — attorney selection required
    return "LOW"  # nothing found — attorney entry required


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
            try:
                matches = await npi.search(hint, jurisdiction_state)
            except Exception:  # noqa: BLE001 — a lookup failure must not abort extraction
                logger.exception("NPI lookup failed for %r", hint)
                matches = []

            confidence = _confidence(matches)
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
                    source_reference=f"intake:{hint}",
                )
            )
            created += 1
        await session.commit()
    return created
