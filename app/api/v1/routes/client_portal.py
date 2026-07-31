"""Client Portal API — client-safe TRACE endpoints.

These endpoints serve the TrueVow Client Portal. They return only
client-permitted data — never attorney work product, risk flags,
strategy notes, or internal scores.

All endpoints verify the client has an active local ClientAccessProjection
with the appropriate scope. The canonical access grant is owned by the
Shared Platform — this local projection is a temporary convenience.

Access lifecycle:
    RETAINER: ENGAGEMENT_ONLY → ENGAGEMENT_HISTORY (never MATTER_*)
    Shared Platform: adds ACTIVE_MATTER after matter.activated
    TRACE: mirrors Shared Platform's grant via local projection

No attorney-only actions are exposed through these routes. The client
can view, upload, and respond to requests — they cannot review facts,
resolve contradictions, or approve demand readiness.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.logging import get_logger
from app.models.case import Case
from app.models.portal_access import ClientAccessProjection
from app.services.evidence import get_evidence_service

logger = get_logger("trace.client_portal")

router = APIRouter(prefix="/api/client/v1", tags=["client-portal"])


class ClientContext:
    """Resolved client context from access projection."""

    def __init__(self, projection: ClientAccessProjection):
        self.projection = projection
        self.client_identity_id = projection.client_identity_id
        self.tenant_id = projection.tenant_id
        self.matter_id = projection.matter_id
        self.party_role_id = projection.party_role_id
        self.permissions = set(projection.permissions.split(",")) if projection.permissions else set()


async def _verify_client_access(
    client_identity_id: uuid.UUID,
    matter_id: uuid.UUID,
    required_permission: str,
) -> ClientContext:
    """Verify client has active access projection for the given matter.

    Fail-closed: no projection, wrong scope, expired, revoked all result in 403.

    NOTE: This queries TRACE's local projection. The canonical source is
    the Shared Platform's client_portal_access_grants table. RETAINER must
    never independently grant MATTER_* scopes — those come from Shared
    Platform's grant upgrade after matter.activated.
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(ClientAccessProjection).where(
                ClientAccessProjection.client_identity_id == client_identity_id,
                ClientAccessProjection.matter_id == matter_id,
                ClientAccessProjection.status == "ACTIVE",
            )
        )
        projection = result.scalar_one_or_none()

        if projection is None:
            raise HTTPException(status_code=403, detail="No active access for this matter")

        if projection.expires_at and projection.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=403, detail="Access has expired")

        ctx = ClientContext(projection)
        if required_permission not in ctx.permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Missing required permission: {required_permission}",
            )

        return ctx


class ClientUploadRequest(BaseModel):
    document_title: str
    request_id: uuid.UUID | None = None


class ClientResponseInput(BaseModel):
    response_text: str | None = None
    files: list[str] = []


@router.get("/matters/{matter_id}")
async def get_matter(
    matter_id: uuid.UUID,
    client_identity_id: uuid.UUID,
) -> dict:
    """Get matter overview for a client. Returns only client-permitted data."""
    ctx = await _verify_client_access(client_identity_id, matter_id, "MATTER_VIEW")

    async with async_session_maker() as session:
        case = (await session.execute(
            select(Case).where(Case.case_id == matter_id, Case.firm_id == ctx.tenant_id)
        )).scalar_one_or_none()

        if case is None:
            raise HTTPException(status_code=404, detail="Matter not found")

    evidence = get_evidence_service()
    chronology = await evidence.build_chronology_from_facts(matter_id)

    return {
        "matter_id": str(matter_id),
        "incident_date": case.incident_date.isoformat() if case.incident_date else None,
        "jurisdiction_state": case.jurisdiction_state,
        "case_stage": case.case_stage,
        "total_documents": len(chronology.get("entries", [])),
    }


@router.get("/matters/{matter_id}/requests")
async def get_client_requests(
    matter_id: uuid.UUID,
    client_identity_id: uuid.UUID,
) -> dict:
    """Get all open requests for a client."""
    _ = await _verify_client_access(client_identity_id, matter_id, "MATTER_VIEW")

    async with async_session_maker() as session:
        from app.models.missing_evidence import MissingEvidenceSignal

        result = await session.execute(
            select(MissingEvidenceSignal)
            .where(
                MissingEvidenceSignal.case_id == matter_id,
                MissingEvidenceSignal.resolved == False,  # noqa: E712
            )
            .order_by(MissingEvidenceSignal.days_overdue.desc())
        )
        signals = result.scalars().all()

    return {
        "matter_id": str(matter_id),
        "total_requests": len(signals),
        "requests": [
            {
                "signal_id": str(s.signal_id),
                "signal_type": s.signal_type,
                "expected_record_type": s.expected_record_type,
                "days_overdue": s.days_overdue,
                "description": f"Missing: {s.signal_type} from provider",
            }
            for s in signals
        ],
    }


@router.get("/matters/{matter_id}/completion")
async def get_completion_status(
    matter_id: uuid.UUID,
    client_identity_id: uuid.UUID,
) -> dict:
    """Get practical completion status for client display.

    Returns concrete counts ("7 of 10 items received") — not internal
    scores or legal assessments. No risk flags, no attorney annotations.
    """
    _ = await _verify_client_access(client_identity_id, matter_id, "MATTER_VIEW")

    async with async_session_maker() as session:
        from app.models.document import Document as DocModel
        from app.models.record_request import RecordRequest

        docs_result = await session.execute(
            select(DocModel).where(DocModel.case_id == matter_id)
        )
        documents = docs_result.scalars().all()

        requests_result = await session.execute(
            select(RecordRequest).where(RecordRequest.case_id == matter_id)
        )
        record_requests = requests_result.scalars().all()

    total_requests = len(record_requests)
    completed_requests = len([r for r in record_requests if r.retrieval_status == "RECEIVED"])
    total_docs = len(documents)

    return {
        "matter_id": str(matter_id),
        "completion": {
            "requests": f"{completed_requests} of {total_requests} received",
            "documents": f"{total_docs} documents on file",
            "requests_completed": completed_requests,
            "requests_total": total_requests,
            "documents_total": total_docs,
        },
    }


@router.get("/matters/{matter_id}/documents")
async def get_client_documents(
    matter_id: uuid.UUID,
    client_identity_id: uuid.UUID,
) -> dict:
    """Get documents the client is permitted to view."""
    await _verify_client_access(client_identity_id, matter_id, "DOCUMENT_DOWNLOAD")

    async with async_session_maker() as session:
        from app.models.document import Document as DocModel

        result = await session.execute(
            select(DocModel).where(DocModel.case_id == matter_id)
        )
        docs = result.scalars().all()

    return {
        "matter_id": str(matter_id),
        "total_documents": len(docs),
        "documents": [
            {
                "document_id": str(d.document_id),
                "document_type": d.document_type,
                "received_at": d.received_at.isoformat() if d.received_at else None,
                "source": d.source,
            }
            for d in docs
        ],
    }


@router.get("/access")
async def get_client_access(
    client_identity_id: uuid.UUID,
) -> dict:
    """Get all active access projections for a client identity.

    NOTE: These are TRACE-local projections. The canonical source is the
    Shared Platform's client_portal_access_grants table.
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(ClientAccessProjection).where(
                ClientAccessProjection.client_identity_id == client_identity_id,
                ClientAccessProjection.status == "ACTIVE",
            )
        )
        projections = result.scalars().all()

    scopes: list[str] = []
    matters: list[str] = []
    for p in projections:
        scopes.append(p.relationship_scope)
        if p.matter_id:
            matters.append(str(p.matter_id))

    return {
        "client_identity_id": str(client_identity_id),
        "active_scopes": list(set(scopes)),
        "matter_ids": list(set(matters)),
        "projections": [
            {
                "projection_id": str(p.projection_id),
                "canonical_grant_id": str(p.canonical_grant_id) if p.canonical_grant_id else None,
                "tenant_id": str(p.tenant_id),
                "matter_id": str(p.matter_id) if p.matter_id else None,
                "relationship_scope": p.relationship_scope,
                "permissions": p.permissions.split(",") if p.permissions else [],
                "effective_from": p.effective_from.isoformat() if p.effective_from else None,
                "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            }
            for p in projections
        ],
    }
