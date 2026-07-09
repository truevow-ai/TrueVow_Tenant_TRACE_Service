"""CMS NPI Registry client.

Queries the public NPI Registry API and normalizes results into a simple shape
the extraction pipeline consumes. No PHI is sent — only a provider name and
state. The client is injectable so tests never hit the network.

Rate limiting: exponential backoff on 429 responses, max 4 attempts.
Confidence taxonomy per ADR-001 §24.2 and ADR-002 §13.5:
    1 result  → CONFIRMED
    2-3 results → NEEDS_CLIENT_CONFIRMATION
    4+ results → NEEDS_STAFF_REVIEW
    0 results → DO_NOT_REQUEST
"""

from __future__ import annotations

import asyncio

import httpx

NPI_API_URL = "https://npiregistry.cms.hhs.gov/api/"
MAX_RETRIES = 4


class NpiRegistryUnavailableError(Exception):
    def __init__(self, provider_name: str) -> None:
        super().__init__(f"NPI Registry unavailable after {MAX_RETRIES} attempts for: {provider_name}")


def _normalize(result: dict) -> dict:
    basic = result.get("basic", {}) or {}
    name = basic.get("organization_name") or " ".join(
        p for p in [basic.get("first_name"), basic.get("last_name")] if p
    )
    addresses = result.get("addresses", []) or []
    addr = addresses[0] if addresses else {}
    taxonomies = result.get("taxonomies", []) or []
    specialty = next((t.get("desc") for t in taxonomies if t.get("primary")), None)
    if specialty is None and taxonomies:
        specialty = taxonomies[0].get("desc")
    address_str = ", ".join(
        p for p in [addr.get("address_1"), addr.get("city"), addr.get("state"), addr.get("postal_code")] if p
    )
    return {
        "npi_number": str(result.get("number")) if result.get("number") else None,
        "name": name or None,
        "facility": basic.get("organization_name"),
        "fax": addr.get("fax_number"),
        "address": address_str or None,
        "specialty": specialty,
    }


def _assign_confidence(result_count: int) -> str:
    if result_count == 0:
        return "DO_NOT_REQUEST"
    if result_count == 1:
        return "CONFIRMED"
    if result_count <= 3:
        return "NEEDS_CLIENT_CONFIRMATION"
    return "NEEDS_STAFF_REVIEW"


class NPIClient:
    def __init__(self, base_url: str = NPI_API_URL, timeout: float = 10.0) -> None:
        self._base_url = base_url
        self._timeout = timeout

    async def search(self, name: str, state: str | None = None, limit: int = 5) -> list[dict]:
        """Return normalized provider matches with confidence labels.

        Exponential backoff on 429 rate limits. Raises NpiRegistryUnavailableError
        if all retry attempts are exhausted.
        """
        params: dict[str, str | int] = {"version": "2.1", "limit": limit}
        tokens = name.split()
        if len(tokens) >= 2:
            params["first_name"] = tokens[0]
            params["last_name"] = tokens[-1]
        else:
            params["organization_name"] = name
        if state:
            params["state"] = state

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.get(self._base_url, params=params)

                if resp.status_code == 429:
                    wait_seconds = 2 ** attempt
                    await asyncio.sleep(wait_seconds)
                    continue

                resp.raise_for_status()
                payload = resp.json()
                break
            except httpx.TimeoutException:
                if attempt == MAX_RETRIES - 1:
                    raise NpiRegistryUnavailableError(provider_name=name) from None
                await asyncio.sleep(2 ** attempt)
        else:
            raise NpiRegistryUnavailableError(provider_name=name)

        results = [_normalize(r) for r in payload.get("results", [])]
        confidence = _assign_confidence(len(results))
        for r in results:
            r["confidence"] = confidence
        return results
