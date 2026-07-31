"""FaxService abstraction — SRFax, Documo, Twilio, or Fax.Plus.

ADR-003 §5: sandbox bake-off selects the vendor. Real HTTP implementations
for SRFax (primary candidate), Documo, Twilio, and Fax.Plus.

Vendor selected via FAX_PROVIDER env var. Fails loudly on unrecognized
provider — no silent fallback.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import httpx


class FaxProvider(str, Enum):
    SRFAX = "srfax"
    DOCUMO = "documo"
    FAXPLUS = "faxplus"
    TWILIO = "twilio"


@dataclass
class FaxSendResult:
    transmission_id: str
    status: str
    pages: int = 0


@dataclass
class FaxStatusResult:
    transmission_id: str
    status: str


class FaxService(ABC):
    @abstractmethod
    async def send(self, fax_number: str, document_pdf: bytes) -> FaxSendResult:
        raise NotImplementedError

    @abstractmethod
    async def get_status(self, transmission_id: str) -> FaxStatusResult:
        raise NotImplementedError


class SRFaxService(FaxService):
    """SRFax API client — healthcare plans, $12.60/mo, HIPAA every plan."""

    def __init__(self) -> None:
        self._access_id = os.getenv("SRFAX_ACCESS_ID", "")
        self._access_pwd = os.getenv("SRFAX_ACCESS_PWD", "")
        self._api_url = "https://www.srfax.com/SRF_SecWebSvc.php"

    async def send(self, fax_number: str, document_pdf: bytes) -> FaxSendResult:
        import base64

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self._api_url,
                data={
                    "action": "Queue_Fax",
                    "access_id": self._access_id,
                    "access_pwd": self._access_pwd,
                    "sCallerID": os.getenv("FAX_RETURN_NUMBER", ""),
                    "sFaxType": "SINGLE",
                    "sToFaxNumber": fax_number,
                    "sFileName": "record_request.pdf",
                    "sFileContent": base64.b64encode(document_pdf).decode(),
                },
            )
            response.raise_for_status()
            result = response.text.strip()
            if "Success" in result:
                parts = result.split("|")
                return FaxSendResult(
                    transmission_id=parts[1] if len(parts) > 1 else "unknown",
                    status="sent",
                )
            return FaxSendResult(transmission_id="failed", status="failed")

    async def get_status(self, transmission_id: str) -> FaxStatusResult:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self._api_url,
                data={
                    "action": "Get_FaxStatus",
                    "access_id": self._access_id,
                    "access_pwd": self._access_pwd,
                    "sFaxDetailsID": transmission_id,
                },
            )
            response.raise_for_status()
            status_map = {"Success": "delivered", "Pending": "pending", "Failure": "failed", "Sent": "sent"}
            status = status_map.get(response.text.strip(), "pending")
            return FaxStatusResult(transmission_id=transmission_id, status=status)


class DocumoService(FaxService):
    """Documo API client — $25/mo, HIPAA every plan, AI document processing."""

    def __init__(self) -> None:
        self._api_key = os.getenv("DOCUMO_API_KEY", "")
        self._api_url = "https://api.documo.com/v1"

    async def send(self, fax_number: str, document_pdf: bytes) -> FaxSendResult:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._api_url}/faxes",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                },
                json={
                    "to": fax_number,
                    "from": os.getenv("FAX_RETURN_NUMBER", ""),
                    "files": [{"name": "record_request.pdf", "content": document_pdf.decode("latin-1")}],
                },
            )
            response.raise_for_status()
            data = response.json()
            return FaxSendResult(
                transmission_id=str(data.get("id", "unknown")),
                status="sent",
            )

    async def get_status(self, transmission_id: str) -> FaxStatusResult:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._api_url}/faxes/{transmission_id}",
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            response.raise_for_status()
            data = response.json()
            return FaxStatusResult(
                transmission_id=transmission_id,
                status=data.get("status", "pending"),
            )


class FaxPlusService(FaxService):
    """Fax.Plus API client — $79.99/mo, HIPAA Enterprise only."""

    def __init__(self) -> None:
        self._api_key = os.getenv("FAXPLUS_API_KEY", "")
        self._api_url = "https://restapi.fax.plus/v1"

    async def send(self, fax_number: str, document_pdf: bytes) -> FaxSendResult:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self._api_url}/faxes",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "to": {"raw": fax_number},
                    "from": os.getenv("FAX_RETURN_NUMBER", ""),
                    "files": [document_pdf.hex()],
                },
            )
            response.raise_for_status()
            data = response.json()
            return FaxSendResult(
                transmission_id=str(data.get("id", "unknown")),
                status="sent",
            )

    async def get_status(self, transmission_id: str) -> FaxStatusResult:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._api_url}/faxes/{transmission_id}",
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            response.raise_for_status()
            data = response.json()
            return FaxStatusResult(
                transmission_id=transmission_id,
                status=data.get("status", "pending"),
            )


class TwilioService(FaxService):
    """Twilio Programmable Fax API — $0.01/page pay-as-you-go.

    Uses Twilio account credentials already configured in the environment.
    Outbound: POST /v1/Faxes with MediaUrl (Supabase pre-signed URL).
    Inbound: Webhook endpoint receives received fax callbacks.
    """

    def __init__(self) -> None:
        self._account_sid = os.getenv("TWILIO_ACCOUNT_SID") or os.getenv("Twilio_Account_SID", "")
        self._auth_token = os.getenv("TWILIO_AUTH_TOKEN") or os.getenv("Twilio_Auth_Token", "")
        self._from_number = os.getenv("FAX_RETURN_NUMBER") or os.getenv("TWILIO_PHONE_NUMBER", "")
        self._api_url = "https://fax.twilio.com/v1/Faxes"

    async def send(self, fax_number: str, document_pdf: bytes) -> FaxSendResult:
        from app.storage.storage_service import get_storage_service
        import uuid as _uuid

        storage = get_storage_service()
        media_key = f"fax-outbound/{_uuid.uuid4().hex}.pdf"
        await storage.upload(media_key, document_pdf, "application/pdf")

        signed_url = await storage.presign(media_key, 3600)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self._api_url,
                auth=(self._account_sid, self._auth_token),
                data={
                    "To": fax_number,
                    "From": self._from_number,
                    "MediaUrl": signed_url,
                },
            )
            response.raise_for_status()
            data = response.json()
            return FaxSendResult(
                transmission_id=data.get("sid", "unknown"),
                status="sent" if data.get("status") in ("queued", "processing", "sending") else "failed",
            )

    async def get_status(self, transmission_id: str) -> FaxStatusResult:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self._api_url}/{transmission_id}",
                auth=(self._account_sid, self._auth_token),
            )
            response.raise_for_status()
            data = response.json()
            status_map = {
                "queued": "pending", "processing": "pending", "sending": "sent",
                "delivered": "delivered", "received": "delivered",
                "failed": "failed", "canceled": "failed",
            }
            return FaxStatusResult(
                transmission_id=transmission_id,
                status=status_map.get(data.get("status", ""), "pending"),
            )


def create_fax_service() -> FaxService:
    provider = os.getenv("FAX_PROVIDER", "twilio").lower()
    if provider == FaxProvider.DOCUMO.value:
        return DocumoService()
    if provider == FaxProvider.FAXPLUS.value:
        return FaxPlusService()
    if provider == FaxProvider.SRFAX.value:
        return SRFaxService()
    if provider == FaxProvider.TWILIO.value:
        return TwilioService()
    raise ValueError(
        f"Unrecognized FAX_PROVIDER: {provider!r}. "
        f"Must be one of: documo, faxplus, srfax, twilio."
    )


FaxClient = FaxService
get_fax_client = create_fax_service
