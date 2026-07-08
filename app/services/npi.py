"""CMS NPI Registry client.

Queries the public NPI Registry API and normalizes results into a simple shape
the extraction pipeline consumes. No PHI is sent — only a provider name and
state. The client is injectable so tests never hit the network.
"""

from __future__ import annotations

import httpx

NPI_API_URL = "https://npiregistry.cms.hhs.gov/api/"


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


class NPIClient:
    def __init__(self, base_url: str = NPI_API_URL, timeout: float = 10.0) -> None:
        self._base_url = base_url
        self._timeout = timeout

    async def search(self, name: str, state: str | None = None, limit: int = 5) -> list[dict]:
        """Return normalized provider matches for a name (optionally state-filtered)."""
        params: dict[str, str | int] = {"version": "2.1", "limit": limit}
        tokens = name.split()
        if len(tokens) >= 2:
            params["first_name"] = tokens[0]
            params["last_name"] = tokens[-1]
        else:
            params["organization_name"] = name
        if state:
            params["state"] = state

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(self._base_url, params=params)
            resp.raise_for_status()
            payload = resp.json()

        return [_normalize(r) for r in payload.get("results", [])]
