"""HIPAA-compliant cloud fax client (mockable).

Makes no attempt to send PHI inside the cover-sheet text — the cover sheet
references only the opaque case-id and the HIPAA-authorization reference number.
The signed authorization PDF (containing actual PII) is attached separately and
retrieved securely. The Fax.Plus API is called with ``hipaa_mode=true`` so that
no PHI appears in Fax.Plus notification emails.
"""

from __future__ import annotations


from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("trace.fax")


class FaxClient:
    """Production adapter for Fax.Plus Enterprise."""

    def __init__(self, api_key: str = "", base_url: str = "https://restapi.fax.plus/v1") -> None:
        self._api_key = api_key
        self._base_url = base_url

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    async def send(
        self,
        fax_number: str,
        cover_sheet_pdf: bytes,
        hipaa_authorization_pdf: bytes | None = None,
    ) -> str:
        """Transmit a fax. Returns the Fax.Plus transmission ID. NOT IMPLEMENTED — stub only."""
        if not self.configured:
            raise RuntimeError("Fax.Plus API key not set.")
        # Production would POST to self._base_url/files + POST fax.
        raise NotImplementedError("Fax.Plus transmission not implemented (requires live creds).")

    async def status(self, fax_id: str) -> dict:
        """Query transmission status. NOT IMPLEMENTED — stub only."""
        raise NotImplementedError("Fax.Plus status not implemented (requires live creds).")


def get_fax_client() -> FaxClient:
    """FastAPI dependency — overridable in tests."""
    return FaxClient(api_key=settings.fax_api_key)
