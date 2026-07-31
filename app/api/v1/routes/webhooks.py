"""Fax/webhook callbacks — inbound + outbound status updates.

Machine-to-machine endpoints (no Clerk session). Protected by shared
secret headers. Handles:
  - Outbound fax delivery status (Documo callback)
  - Inbound email with attachments (Resend webhook)
  - Inbound fax receipt (Documo received-fax callback)
  - Matter activation from RETAINER (matter.activated event)
"""

from __future__ import annotations

from datetime import date as date_type
import datetime
import uuid

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import select

from app.core.audit import write_audit
from app.core.config import settings
from app.core.database import async_session_maker
from app.core.logging import get_logger
from app.models.provider import Provider
from app.models.record_request import RecordRequest
from app.services.inbound import process_inbound_email, process_inbound_fax
from app.services.matter_activation import ActivationPayload, get_matter_activation_handler
from app.shared import get_event_store, EventEnvelope
from app.shared.webhook_auth import VerifyStatus, get_webhook_verifier

logger = get_logger("trace.webhooks")


def _parse_uuid_list(value: list[str] | None) -> list[uuid.UUID] | None:
    if not value:
        return None
    result: list[uuid.UUID] = []
    for item in value:
        try:
            result.append(uuid.UUID(item))
        except (ValueError, TypeError):
            pass
    return result if result else None

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


@router.post("/matter-activated")
async def matter_activated(
    request: Request,
    payload: dict,
    x_truevow_key_id: str | None = Header(default=None),
    x_truevow_timestamp: str | None = Header(default=None),
    x_truevow_signature: str | None = Header(default=None),
) -> dict:
    """Consume matter.activated event from RETAINER.

    Creates or projects TRACE's case-production context idempotently.
    Authentication via HMAC signature (X-TrueVow-Key-Id + X-TrueVow-Timestamp
    + X-TrueVow-Signature). Rejects with 422 if any validation fails.
    """
    raw_body = await request.body()
    verifier = get_webhook_verifier(tolerance_seconds=300)
    auth_result = verifier.verify_from_request(
        method="POST",
        path="/api/v1/trace/webhooks/matter-activated",
        raw_body=raw_body,
        key_id=x_truevow_key_id,
        timestamp=x_truevow_timestamp,
        signature=x_truevow_signature,
    )
    if auth_result.status != VerifyStatus.OK:
        raise HTTPException(status_code=401, detail=auth_result.detail)

    event_id = payload.get("event_id")
    if not event_id:
        raise HTTPException(status_code=400, detail="Missing event_id")

    if verifier.is_replay(event_id):
        return {"status": "duplicate", "event_id": event_id, "detail": "Event already processed"}

    try:
        event_uuid = uuid.UUID(event_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid event_id format")

    inner = payload.get("payload", {})
    activation = ActivationPayload(
        matter_id=uuid.UUID(str(inner.get("matter_id", inner.get("aggregate_id", "00000000-0000-0000-0000-000000000000")))),
        tenant_id=uuid.UUID(payload["tenant_id"]) if payload.get("tenant_id") else None,
        activation_id=uuid.UUID(inner["activation_id"]) if inner.get("activation_id") else None,
        evidence_manifest_id=uuid.UUID(inner["evidence_manifest_id"]) if inner.get("evidence_manifest_id") else None,
        representation_decision_id=uuid.UUID(inner["representation_decision_id"]) if inner.get("representation_decision_id") else None,
        conflict_clearance_authority_id=uuid.UUID(inner["conflict_clearance_authority_id"]) if inner.get("conflict_clearance_authority_id") else None,
        engagement_workflow_id=uuid.UUID(inner["engagement_workflow_id"]) if inner.get("engagement_workflow_id") else None,
        executed_package_id=uuid.UUID(inner["executed_package_id"]) if inner.get("executed_package_id") else None,
        signature_evidence_ids=_parse_uuid_list(inner.get("signature_evidence_ids")),
        completed_copy_delivery_id=uuid.UUID(inner["completed_copy_delivery_id"]) if inner.get("completed_copy_delivery_id") else None,
        responsible_attorney_assignment_id=uuid.UUID(inner["responsible_attorney_assignment_id"]) if inner.get("responsible_attorney_assignment_id") else None,
        jurisdiction_profile_version_id=uuid.UUID(inner["jurisdiction_profile_version_id"]) if inner.get("jurisdiction_profile_version_id") else None,
        activation_policy_version_id=uuid.UUID(inner["activation_policy_version_id"]) if inner.get("activation_policy_version_id") else None,
        source_matter_candidate_id=uuid.UUID(inner["source_matter_candidate_id"]) if inner.get("source_matter_candidate_id") else None,
        client_party_role_id=uuid.UUID(inner["client_party_role_id"]) if inner.get("client_party_role_id") else None,
        client_token=uuid.UUID(inner["client_token"]) if inner.get("client_token") else None,
        incident_date=None,
        jurisdiction_state=inner.get("jurisdiction_state"),
        sol_deadline=None,
        sol_urgency=inner.get("sol_urgency"),
        schema_version=payload.get("schema_version", "1.0.1"),
        authority_class=payload.get("authority_class", "FIRM-POLICY"),
        authority_record_id=uuid.UUID(payload["authority_record_id"]) if payload.get("authority_record_id") else None,
        occurred_at=None,
        metadata=inner.get("metadata", {}),
    )

    if inner.get("incident_date"):
        try:
            activation.incident_date = date_type.fromisoformat(inner["incident_date"])
        except (ValueError, TypeError):
            pass

    if inner.get("sol_deadline"):
        try:
            activation.sol_deadline = date_type.fromisoformat(inner["sol_deadline"])
        except (ValueError, TypeError):
            pass

    handler = get_matter_activation_handler()
    result = await handler.handle(event_uuid, activation)

    verifier.mark_consumed(event_id)

    if result.accepted:
        event_store = get_event_store()
        await event_store.record(EventEnvelope(
            event_id=event_uuid,
            event_type="matter.activated",
            tenant_id=activation.tenant_id,
            aggregate_type="cases",
            aggregate_id=result.case_id,
            aggregate_version=1,
            actor_type="RETAINER",
            authority_class=activation.authority_class,
            authority_record_id=activation.authority_record_id,
            policy_version_id=activation.activation_policy_version_id,
            schema_version=activation.schema_version,
            correlation_id=str(activation.activation_id) if activation.activation_id else None,
            payload={
                "matter_id": str(activation.matter_id),
                "case_id": str(result.case_id) if result.case_id else None,
                "jurisdiction_state": activation.jurisdiction_state,
                "is_duplicate": result.is_duplicate,
            },
            sensitivity_class="CONFIDENTIAL",
        ))

        return {
            "status": "accepted",
            "case_id": str(result.case_id) if result.case_id else None,
            "is_duplicate": result.is_duplicate,
        }

    raise HTTPException(
        status_code=422,
        detail={
            "rejection_reason": result.rejection_reason.value if result.rejection_reason else "UNKNOWN",
            "detail": result.rejection_detail,
        },
    )
