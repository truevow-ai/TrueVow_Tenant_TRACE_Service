"""DocuSeal signing endpoints.

ADR-002 §6: two methods — send_signing_package() and handle_signing_webhook().
The signing flow is what advances the case from PENDING_SIGNATURE to
INITIALIZATION. Nothing else should do this.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.auth.deps import AuthContext, get_current_context
from app.core.audit import write_audit
from app.core.database import async_session_maker
from app.core.logging import get_logger
from app.models.case import Case
from app.models.signed_document import SignedDocument
from app.services.phi_store import get_client
from app.services.signing import SigningService, WebhookSignatureError

logger = get_logger("trace.signing.routes")

router = APIRouter(prefix="/cases/{case_id}/signing", tags=["signing"])
webhook_router = APIRouter(prefix="/webhooks/docuseal", tags=["webhooks"])


class SendSigningResponse(BaseModel):
    submission_id: str
    signing_status: str
    message: str


async def _get_signing_service() -> SigningService:
    return SigningService()


async def _get_case(case_id: uuid.UUID, firm_id: uuid.UUID) -> Case | None:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Case).where(
                Case.case_id == case_id,
                Case.firm_id == firm_id,
            )
        )
        return result.scalar_one_or_none()


@router.post("/send", response_model=SendSigningResponse)
async def send_signing_package(
    case_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    signing_service: SigningService = Depends(_get_signing_service),
) -> SendSigningResponse:
    firm_uuid = uuid.UUID(ctx.firm_id)
    case = await _get_case(case_id, firm_uuid)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.case_stage != "PENDING_SIGNATURE":
        raise HTTPException(
            status_code=400,
            detail="Signing package can only be sent when the case is awaiting client signature.",
        )

    client_contact = await get_client(case.client_token)
    if client_contact is None:
        raise HTTPException(status_code=400, detail="Client contact information not found.")

    result = await signing_service.send_signing_package(
        client_name=client_contact["name"],
        client_email=client_contact.get("email", ""),
        client_phone=client_contact.get("phone", ""),
        firm_id=firm_uuid,
        matter_reference=f"Matter #{case.case_id}",
    )

    async with async_session_maker() as session:
        case.hipaa_auth_status = "SENT"
        case.signing_sent_at = datetime.now(timezone.utc)
        case.docuseal_submission_id = result.submission_id

        signed_doc = SignedDocument(
            case_id=case.case_id,
            firm_id=firm_uuid,
            docuseal_submission_id=result.submission_id,
            document_type="RETAINER",
            signing_status="SENT",
        )
        session.add(signed_doc)
        await session.commit()

        await write_audit(
            actor_id=ctx.user_id,
            actor_type="ATTORNEY",
            action="signing.package_sent",
            resource_type="cases",
            resource_id=case.case_id,
            case_id=case.case_id,
            firm_id=firm_uuid,
            details={"submission_id": result.submission_id},
        )

    return SendSigningResponse(
        submission_id=result.submission_id,
        signing_status="SENT",
        message="Signing package has been sent. The client will receive an email and text message with a link to sign.",
    )


@webhook_router.post("/signing-complete")
async def handle_signing_webhook(
    request: Request,
    signing_service: SigningService = Depends(_get_signing_service),
) -> dict:
    raw_body = await request.body()
    signature = request.headers.get("X-Docuseal-Signature", "")

    try:
        await signing_service.verify_webhook_signature(raw_body, signature)
    except WebhookSignatureError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature.") from None

    payload = signing_service.parse_webhook_payload(raw_body)

    async with async_session_maker() as session:
        existing = await session.execute(
            select(SignedDocument).where(
                SignedDocument.docuseal_submission_id == payload.submission_id,
            )
        )
        signed_doc = existing.scalar_one_or_none()

        if signed_doc and signed_doc.signing_status == "COMPLETED":
            return {"status": "already_processed"}  # idempotent

        result = await session.execute(
            select(Case).where(Case.docuseal_submission_id == payload.submission_id)
        )
        case = result.scalar_one_or_none()

        if case is None:
            logger.warning(
                "DocuSeal webhook received for unknown submission",
                extra={"submission_id": payload.submission_id},
            )
            return {"status": "no_matching_case"}

        case.case_stage = "INITIALIZATION"
        case.hipaa_auth_status = "SIGNED"
        case.signing_completed_at = (
            datetime.fromisoformat(payload.completed_at)
            if payload.completed_at
            else datetime.now(timezone.utc)
        )

        if signed_doc:
            signed_doc.signing_status = "COMPLETED"
            signed_doc.client_signed_at = datetime.now(timezone.utc)

        await write_audit(
            actor_id=None,
            actor_type="SYSTEM",
            action="signing.webhook_received",
            resource_type="cases",
            resource_id=case.case_id,
            case_id=case.case_id,
            firm_id=case.firm_id,
            details={
                "submission_id": payload.submission_id,
                "event_id": payload.event_id,
            },
        )
        await session.commit()

    return {"status": "processed"}
