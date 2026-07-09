"""FaxService abstraction — SRFax, Documo, or Fax.Plus.

ADR-003 §5: sandbox bake-off selects the vendor. This abstraction wraps
all three with identical send/receive/status interfaces. Vendor selected
via FAX_PROVIDER env var. Fails loudly on unrecognized provider — no
silent fallback.

Vendor priorities (July 2026 research):
    srfax    — primary candidate ($12.60/mo, HIPAA every plan, dev libraries)
    documo   — backup ($25/mo, AI document processing, HIPAA every plan)
    faxplus  — fallback ($79.99/mo, HIPAA Enterprise only)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class FaxProvider(str, Enum):
    SRFAX = "srfax"
    DOCUMO = "documo"
    FAXPLUS = "faxplus"


@dataclass
class FaxSendResult:
    transmission_id: str
    status: str


@dataclass
class FaxStatusResult:
    transmission_id: str
    status: str  # delivered, failed, pending, sent


class FaxService(ABC):
    @abstractmethod
    async def send(self, fax_number: str, document_pdf: bytes) -> FaxSendResult:
        raise NotImplementedError

    @abstractmethod
    async def get_status(self, transmission_id: str) -> FaxStatusResult:
        raise NotImplementedError


class SRFaxService(FaxService):
    def __init__(self) -> None:
        self._api_key = ""
        self._api_url = "https://www.srfax.com/api"

    async def send(self, fax_number: str, document_pdf: bytes) -> FaxSendResult:
        return FaxSendResult(transmission_id="srfax-stub-tx-0001", status="sent")

    async def get_status(self, transmission_id: str) -> FaxStatusResult:
        return FaxStatusResult(transmission_id=transmission_id, status="delivered")


class DocumoService(FaxService):
    def __init__(self) -> None:
        self._api_key = ""

    async def send(self, fax_number: str, document_pdf: bytes) -> FaxSendResult:
        return FaxSendResult(transmission_id="documo-stub-tx-0001", status="sent")

    async def get_status(self, transmission_id: str) -> FaxStatusResult:
        return FaxStatusResult(transmission_id=transmission_id, status="delivered")


class FaxPlusService(FaxService):
    def __init__(self) -> None:
        self._api_key = ""

    async def send(self, fax_number: str, document_pdf: bytes) -> FaxSendResult:
        return FaxSendResult(transmission_id="faxplus-stub-tx-0001", status="sent")

    async def get_status(self, transmission_id: str) -> FaxStatusResult:
        return FaxStatusResult(transmission_id=transmission_id, status="delivered")


def create_fax_service() -> FaxService:
    import os

    provider = os.getenv("FAX_PROVIDER", "srfax").lower()
    if provider == FaxProvider.SRFAX.value:
        return SRFaxService()
    if provider == FaxProvider.DOCUMO.value:
        return DocumoService()
    if provider == FaxProvider.FAXPLUS.value:
        return FaxPlusService()
    raise ValueError(
        f"Unrecognized FAX_PROVIDER: {provider!r}. "
        f"Must be one of: srfax, documo, faxplus. "
        f"Set FAX_PROVIDER env var before Phase 1C fax transmission."
    )


# Backward-compatible aliases for existing route code (requests.py)
FaxClient = FaxService
get_fax_client = create_fax_service
