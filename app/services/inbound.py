"""Inbound document reception — email (Resend) and fax (Documo) webhooks.

Receives medical records from providers via email attachments or fax,
matches them to the correct TRACE case, stores in Supabase Storage,
and triggers the OCR + chronology pipeline.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import uuid
from base64 import b64decode
from dataclasses import dataclass, field

import httpx

from app.core.database import async_session_maker
from app.core.logging import get_logger
from app.models.case import Case
from app.models.document import Document
from app.storage.storage_service import get_storage_service
from sqlalchemy import select

logger = get_logger("trace.inbound")

# ── Case matching patterns ──
CASE_ID_PATTERN = re.compile(r"case[:\s-]*([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12})")
BARCODE_PATTERN = re.compile(r"(?:ref|reference|barcode)[:\s#-]*([A-Z0-9]{6,20})", re.IGNORECASE)
NAME_PATTERN = re.compile(r"(?:patient|client|claimant)[:\s-]*([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2})", re.IGNORECASE)


@dataclass
class InboundAttachment:
    filename: str
    content_type: str
    data: bytes
    size: int = 0

    def __post_init__(self):
        self.size = len(self.data)


@dataclass
class InboundResult:
    success: bool
    document_id: uuid.UUID | None = None
    case_id: uuid.UUID | None = None
    error: str | None = None


# ── Email ingestion (Resend inbound webhook) ──

def _verify_hmac(body: bytes, secret: str, signature_header: str) -> bool:
    if not secret or not signature_header:
        return True  # webhook not configured — allow in dev
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def _extract_case_id_from_text(text: str) -> uuid.UUID | None:
    match = CASE_ID_PATTERN.search(text)
    if match:
        try:
            return uuid.UUID(match.group(1))
        except ValueError:
            pass

    match = BARCODE_PATTERN.search(text)
    if match:
        ref = match.group(1)
        return _lookup_case_by_reference(ref)

    return None


def _lookup_case_by_reference(ref: str) -> uuid.UUID | None:
    """Look up case by reference code in document filenames and record requests."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        return None

    async def _lookup() -> uuid.UUID | None:
        async with async_session_maker() as session:
            from sqlalchemy import select, cast, String
            result = await session.execute(
                select(Case.case_id).where(cast(Case.case_id, String).like(f"{ref}%"))
            )
            row = result.first()
            return row[0] if row else None

    try:
        return loop.run_until_complete(_lookup())
    except Exception:
        return None


async def process_inbound_email(
    raw_body: bytes,
    signature_header: str = "",
) -> list[InboundResult]:
    """Process a Resend inbound email webhook payload.

    Resend sends JSON with the structure:
        {
          "to": "records+case-id@yourdomain.com",
          "from": "hospital@example.com",
          "subject": "Medical Records for Case abc-123",
          "text": "Here are the records",
          "attachments": [
            {"filename": "mri.pdf", "content_type": "application/pdf", "content": "<base64>"}
          ]
        }
    """
    import json

    webhook_secret = ""  # TODO: configure RESEND_INBOUND_WEBHOOK_SECRET in settings
    if not _verify_hmac(raw_body, webhook_secret, signature_header):
        logger.warning("Inbound email HMAC verification failed")
        return [InboundResult(success=False, error="Invalid HMAC signature")]

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return [InboundResult(success=False, error="Invalid JSON payload")]

    subject = (payload.get("subject") or "")
    text_body = (payload.get("text") or "")
    from_addr = (payload.get("from") or "")
    all_text = f"{subject}\n{text_body}"

    # Case matching
    case_id = (
        _extract_case_id_from_text(subject)
        or _extract_case_id_from_text(text_body)
        or _extract_case_id_from_text(from_addr)
    )
    if not case_id:
        logger.info("Inbound email could not be matched to a case — subject=%r from=%r", subject[:80], from_addr)
        return [InboundResult(success=False, error="Could not match email to any case")]

    # Verify case exists
    async with async_session_maker() as session:
        result = await session.execute(select(Case).where(Case.case_id == case_id))
        case = result.scalar_one_or_none()
        if case is None:
            return [InboundResult(success=False, error=f"Case {case_id} not found")]

    # Process attachments
    attachments = payload.get("attachments", [])
    if not attachments:
        logger.info("Inbound email had no attachments — case=%s", case_id)
        return [InboundResult(success=False, error="No attachments in email")]

    results: list[InboundResult] = []
    storage = get_storage_service()

    for att in attachments:
        try:
            filename = att.get("filename", f"inbound_{uuid.uuid4().hex[:8]}.pdf")
            content_type = att.get("content_type", "application/pdf")
            content_b64 = att.get("content", "")

            raw_data = b64decode(content_b64) if content_b64 else b""

            if not raw_data:
                results.append(InboundResult(success=False, error=f"Empty attachment: {filename}"))
                continue

            storage_key = f"cases/{case_id}/inbound-email/{filename}"
            await storage.upload(storage_key, raw_data, content_type)

            sha = hashlib.sha256(raw_data).hexdigest()
            doc = Document(
                case_id=case_id,
                s3_bucket="trace-medical-records",
                s3_key=storage_key,
                document_type="MEDICAL_RECORD",
                sha256_hash=sha,
                page_count=0,
                ocr_status="PENDING",
                source="INBOUND_EMAIL",
                original_filename=filename,
            )

            async with async_session_maker() as session:
                session.add(doc)
                await session.commit()
                doc_id = doc.document_id

            results.append(InboundResult(success=True, document_id=doc_id, case_id=case_id))
            logger.info("Inbound email doc stored: %s -> case %s", filename, case_id)

        except Exception as exc:
            logger.exception("Failed to process inbound attachment %s", att.get("filename", "?"))
            results.append(InboundResult(success=False, error=str(exc)[:200]))

    return results


# ── Fax reception (Documo received fax callback) ──

async def process_inbound_fax(payload: dict, secret_header: str = "") -> InboundResult:
    """Process a Documo inbound fax webhook payload.

    Documo sends JSON with:
        {
          "id": "fax_transmission_id",
          "status": "received",
          "from": "+13105551234",
          "to": "+18005551234",
          "pages": 3,
          "media_url": "https://api.documo.com/v1/faxes/{id}/media",
          "received_at": "2025-01-15T10:30:00Z"
        }
    """
    fax_webhook_secret = ""  # TODO: configure in settings (or reuse FAX_WEBHOOK_SECRET)
    if not _verify_hmac(repr(payload).encode(), fax_webhook_secret, secret_header):
        logger.warning("Inbound fax HMAC verification failed")

    fax_id = payload.get("id") or payload.get("fax_id")
    from_number = payload.get("from", "")
    to_number = payload.get("to", "")
    media_url = payload.get("media_url")

    if not fax_id:
        return InboundResult(success=False, error="Missing fax ID")

    # Match to case by the destination fax number (which TRACE sent in the cover sheet)
    case_id = await _match_fax_to_case(to_number, from_number)
    if not case_id:
        logger.info("Inbound fax could not be matched — from=%s to=%s", from_number, to_number)
        return InboundResult(success=False, error="Could not match fax to any case")

    # Download the fax PDF from Documo
    if not media_url:
        return InboundResult(success=False, error="No media_url for fax download")

    try:
        documo_key = ""  # TODO: configure DOCUMO_API_KEY in settings
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(media_url, headers={"Authorization": f"Bearer {documo_key}"} if documo_key else {})
            resp.raise_for_status()
            pdf_data = resp.content
    except Exception as exc:
        logger.exception("Failed to download fax media from Documo")
        return InboundResult(success=False, error=str(exc)[:200])

    if not pdf_data:
        return InboundResult(success=False, error="Empty fax PDF")

    # Store the fax PDF
    filename = f"fax-inbound-{fax_id}.pdf"
    storage_key = f"cases/{case_id}/inbound-fax/{filename}"

    storage = get_storage_service()
    await storage.upload(storage_key, pdf_data, "application/pdf")

    sha = hashlib.sha256(pdf_data).hexdigest()
    doc = Document(
        case_id=case_id,
        s3_bucket="trace-medical-records",
        s3_key=storage_key,
        document_type="MEDICAL_RECORD",
        sha256_hash=sha,
        page_count=0,
        ocr_status="PENDING",
        source="INBOUND_FAX",
        original_filename=filename,
    )

    async with async_session_maker() as session:
        session.add(doc)
        await session.commit()
        doc_id = doc.document_id

    logger.info("Inbound fax stored: %s -> case %s (from %s)", filename, case_id, from_number)
    return InboundResult(success=True, document_id=doc_id, case_id=case_id)


async def _match_fax_to_case(to_number: str, from_number: str) -> uuid.UUID | None:
    """Match an inbound fax to a case by the destination fax number.

    When TRACE sends a fax, the cover sheet includes a unique reference.
    Providers fax records back to the TRACE return number. We match by
    looking up which case last sent a fax request to the provider with
    this phone number.
    """
    async with async_session_maker() as session:
        from sqlalchemy import select, desc
        from app.models.record_request import RecordRequest
        from app.models.provider import Provider

        # Find provider by phone number
        result = await session.execute(
            select(Provider.case_id, Provider.provider_id)
            .where(Provider.fax_number == from_number)
            .order_by(desc(Provider.provider_id))
            .limit(1)
        )
        row = result.first()
        if row:
            return row[0]

        # Fallback: match by recent record request
        result = await session.execute(
            select(RecordRequest.case_id)
            .order_by(desc(RecordRequest.sent_at))
            .limit(1)
        )
        row = result.first()
        return row[0] if row else None
