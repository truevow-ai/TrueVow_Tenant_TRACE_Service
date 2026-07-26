"""Fax/webhook callbacks — inbound + outbound status updates.

Machine-to-machine endpoints (no Clerk session). Protected by shared
secret headers. Handles:
  - Outbound fax delivery status (Documo callback)
  - Inbound email with attachments (Resend webhook)
  - Inbound fax receipt (Documo received-fax callback)
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import select

from app.core.audit import write_audit
from app.core.config import settings
from app.core.database import async_session_maker
from app.models.provider import Provider
from app.models.record_request import RecordRequest
from app.services.inbound import process_inbound_email, process_inbound_fax

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_STATUS_MAP = {
    "success": "DELIVERED",
    "delivered": "DELIVERED",
    "sent": "DELIVERED",
    "completed": "DELIVERED",
    "failed": "FAILED",
    "error": "FAILED",
    "rejected": "FAILED",
}


@router.post("/fax-status")
async def fax_status(
    request: Request,
    payload: dict,
    x_trace_webhook_secret: str | None = Header(default=None),
) -> dict:
    if settings.fax_webhook_secret and x_trace_webhook_secret != settings.fax_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook signature.")

    transmission_id = payload.get("fax_transmission_id") or payload.get("id")
    raw_status = str(payload.get("status", "")).lower()
    if not transmission_id:
        raise HTTPException(status_code=400, detail="Missing fax_transmission_id.")

    mapped = _STATUS_MAP.get(raw_status, "FAILED")

    async with async_session_maker() as session:
        # Webhook is system-level; RLS GUC is not set here (no attorney session),
        # so this session must run without RLS. On Postgres, this endpoint uses a
        # dedicated system role in production; in tests (SQLite) RLS is absent.
        row = (
            await session.execute(
                select(RecordRequest).where(RecordRequest.fax_transmission_id == str(transmission_id))
            )
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Unknown fax transmission.")
        row.status = mapped
        if mapped == "DELIVERED":
            row.confirmed_at = datetime.datetime.now(datetime.timezone.utc)
        case_id = row.case_id
        # Update provider retrieval_status
        provider_result = await session.execute(
            select(Provider).where(Provider.provider_id == row.provider_id)
        )
        provider = provider_result.scalar_one_or_none()
        if provider:
            if mapped == "DELIVERED":
                provider.retrieval_status = "REQUESTED"
            elif mapped == "FAILED":
                provider.retrieval_status = "PENDING"
        await session.commit()

    await write_audit(
        actor_id=None,
        actor_type="SYSTEM",
        action="fax.status_update",
        resource_type="requests",
        resource_id=None,
        case_id=case_id,
        correlation_id=getattr(request.state, "correlation_id", None),
        details={"fax_transmission_id": str(transmission_id), "status": mapped},
    )
    return {"status": mapped}


# ── Inbound email (Resend webhook) ──

@router.post("/inbound-email")
async def inbound_email(
    request: Request,
    x_resend_signature: str | None = Header(default=None),
) -> dict:
    """Receive medical records via email forwarded by Resend.

    Providers email records to a TRACE address (e.g. records@intakely.xyz).
    Resend parses the email and POSTs the attachments to this webhook.
    The system matches the email to a case and stores the documents.
    """
    raw_body = await request.body()
    results = await process_inbound_email(raw_body, x_resend_signature or "")
    stored = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    return {
        "received": len(results),
        "stored": len(stored),
        "document_ids": [str(r.document_id) for r in stored if r.document_id],
        "case_ids": [str(r.case_id) for r in stored if r.case_id],
        "errors": [r.error for r in failed],
    }


# ── Inbound fax (Documo received-fax callback) ──

@router.post("/inbound-fax")
async def inbound_fax(
    request: Request,
    x_documo_signature: str | None = Header(default=None),
) -> dict:
    """Receive fax callback from Documo or Twilio when a provider faxes records back.

    Documo: sends webhook with fax metadata and media_url.
    Twilio: sends standard POST with FaxSid, MediaUrl, From, To, NumPages.
    The system matches by fax number and stores the document.
    """
    try:
        payload: dict = await request.json()
    except Exception:
        try:
            form = await request.form()
            payload = dict(form)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid payload.")

    # Twilio sends form-encoded; Documo sends JSON
    result = await process_inbound_fax(payload, x_documo_signature or "")
    if not result.success:
        return {"status": "unmatched", "error": result.error}

    return {
        "status": "stored",
        "document_id": str(result.document_id) if result.document_id else None,
        "case_id": str(result.case_id) if result.case_id else None,
    }


# ── Twilio inbound fax webhook ──

@router.post("/twilio-inbound-fax")
async def twilio_inbound_fax(request: Request) -> dict:
    """Receive inbound fax webhook from Twilio.

    Twilio sends POST with form fields: FaxSid, From, To, MediaUrl, NumPages.
    The system downloads the PDF from MediaUrl and stores it.
    """
    try:
        form = await request.form()
        payload = dict(form)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid form payload.")

    fax_sid = payload.get("FaxSid", "")
    from_number = payload.get("From", "")
    to_number = payload.get("To", "")
    media_url = payload.get("MediaUrl", "")
    pages = int(payload.get("NumPages", "0"))

    if not fax_sid or not media_url:
        return {"status": "missing_data", "error": "FaxSid or MediaUrl missing"}

    normalized = {
        "id": fax_sid,
        "from": from_number,
        "to": to_number,
        "media_url": media_url,
        "pages": pages,
        "status": "received",
    }

    result = await process_inbound_fax(normalized)
    if not result.success:
        return {"status": "unmatched", "error": result.error}

    return {
        "status": "stored",
        "document_id": str(result.document_id) if result.document_id else None,
        "case_id": str(result.case_id) if result.case_id else None,
    }
