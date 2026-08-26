"""Evidence routes — source-linked fact management, contradictions, missing evidence.

New routes under /cases/{case_id}/evidence/... that expose the full
provenance chain: facts linked to source documents, contradiction pairs
preserved across providers, missing-evidence signals, and attorney review
workflows with versioned audit trails.

Authority Gate: attorney-only actions (review, resolve, edit) are enforced
by the shared Authority Gate service.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.auth.deps import AuthContext, get_current_context
from app.core.audit import write_audit
from app.core.database import internal_tenant_session
from app.core.logging import get_logger
from app.models.case import Case
from app.services.evidence import get_evidence_service
from app.services.fact_review import EditFactRequest, get_fact_review_service
from app.shared import ActorRole, get_authority_gate

logger = get_logger("trace.evidence_routes")


def _require_authority(action: str, ctx: AuthContext) -> None:
    """Fail-closed authority gate check. Raises HTTPException if not authorized."""
    gate = get_authority_gate()
    role = ActorRole(ctx.role) if ctx.role else ActorRole.LEGAL_ASSISTANT
    result = gate.evaluate(action=action, actor_role=role, actor_id=uuid.UUID(ctx.user_id) if ctx.user_id else None)
    if not result.allowed:
        raise HTTPException(status_code=403, detail=result.reason)


def _role_from_context(ctx: AuthContext) -> ActorRole:
    role_map = {
        "attorney": ActorRole.ATTORNEY,
        "admin": ActorRole.FIRM_ADMINISTRATOR,
        "intake_coordinator": ActorRole.INTAKE_COORDINATOR,
        "legal_assistant": ActorRole.LEGAL_ASSISTANT,
        "case_manager": ActorRole.CASE_MANAGER,
        "paralegal": ActorRole.PARALEGAL,
        "supervising_attorney": ActorRole.SUPERVISING_ATTORNEY,
        "managing_attorney": ActorRole.MANAGING_ATTORNEY,
    }
    return role_map.get(ctx.role or "", ActorRole.LEGAL_ASSISTANT)

router = APIRouter(prefix="/cases/{case_id}", tags=["evidence"])


class ReviewStatusRequest(BaseModel):
    status: str
    review_note: str | None = None


class EditFactInput(BaseModel):
    fact_text: str | None = None
    fact_date: str | None = None
    fact_type: str | None = None
    provider_id: str | None = None
    change_reason: str | None = None


class ResolveContradictionInput(BaseModel):
    resolution_status: str
    attorney_note: str | None = None


class DismissSignalInput(BaseModel):
    note: str | None = None


async def _get_case(case_id: uuid.UUID, firm_id: uuid.UUID) -> Case:
    async with internal_tenant_session(tenant_id=firm_id) as session:
        result = await session.execute(
            select(Case).where(Case.case_id == case_id, Case.firm_id == firm_id)
        )
        case = result.scalar_one_or_none()
        if case is None:
            raise HTTPException(status_code=404, detail="Case not found.")
        return case


@router.get("/evidence/facts")
async def list_facts(
    case_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    """List all facts for a case with full source provenance."""
    firm_uuid = uuid.UUID(ctx.firm_id)
    await _get_case(case_id, firm_uuid)

    service = get_evidence_service()
    chronology = await service.build_chronology_from_facts(firm_uuid, case_id)
    return chronology


@router.get("/evidence/facts/{fact_id}")
async def get_fact(
    case_id: uuid.UUID,
    fact_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    """Get a single fact with full provenance and version history."""
    firm_uuid = uuid.UUID(ctx.firm_id)
    await _get_case(case_id, firm_uuid)

    from app.models.evidence_fact import EvidenceFact

    async with internal_tenant_session(
        tenant_id=firm_uuid, user_id=ctx.user_id, role=ctx.role
    ) as session:
        result = await session.execute(
            select(EvidenceFact).where(
                EvidenceFact.fact_id == fact_id,
                EvidenceFact.case_id == case_id,
            )
        )
        fact = result.scalar_one_or_none()

    if fact is None:
        raise HTTPException(status_code=404, detail="Fact not found.")

    review_service = get_fact_review_service()
    history = await review_service.get_fact_history(firm_uuid, fact_id)

    source = fact.source_location if fact.source_location else None
    return {
        "fact_id": str(fact.fact_id),
        "case_id": str(fact.case_id),
        "fact_type": fact.fact_type,
        "fact_date": fact.fact_date.isoformat() if fact.fact_date else None,
        "fact_text": fact.fact_text,
        "provider_id": str(fact.provider_id) if fact.provider_id else None,
        "source": {
            "location_id": str(source.location_id) if source else None,
            "document_id": str(source.document_id) if source else None,
            "page_number": source.page_number if source else None,
            "text_snippet": source.text_snippet if source else None,
            "extraction_method": source.extraction_method if source else "unknown",
            "extraction_confidence": source.extraction_confidence,
            "extraction_model_version": source.extraction_model_version,
        },
        "review": {
            "review_status": fact.review_status,
            "reviewed_by": str(fact.reviewed_by) if fact.reviewed_by else None,
            "reviewed_at": fact.reviewed_at.isoformat() if fact.reviewed_at else None,
            "review_note": fact.review_note,
            "version": fact.version,
        },
        "is_contradicted": fact.is_contradicted,
        "is_duplicate": fact.is_duplicate,
        "duplicate_of_fact_id": str(fact.duplicate_of_fact_id) if fact.duplicate_of_fact_id else None,
        "version_history": history,
    }


@router.patch("/evidence/facts/{fact_id}/review")
async def review_fact(
    case_id: uuid.UUID,
    fact_id: uuid.UUID,
    body: ReviewStatusRequest,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    """Set review status on a fact. Creates a version snapshot. Requires ATTY_AUTH."""
    firm_uuid = uuid.UUID(ctx.firm_id)
    await _get_case(case_id, firm_uuid)
    _require_authority("trace.review_fact", ctx)

    service = get_fact_review_service()
    reviewer = uuid.UUID(ctx.user_id) if ctx.user_id else None
    result = await service.set_review_status(firm_uuid, fact_id, body.status, reviewer, body.review_note)

    if result.error:
        raise HTTPException(status_code=400, detail=result.error)

    await write_audit(
        actor_id=ctx.user_id, actor_type="ATTORNEY",
        action=f"fact.review.{result.new_status.lower()}",
        resource_type="evidence_facts", resource_id=fact_id,
        case_id=case_id, firm_id=firm_uuid,
        details={"previous_status": result.previous_status, "new_status": result.new_status},
    )

    return {
        "fact_id": str(result.fact_id),
        "previous_status": result.previous_status,
        "new_status": result.new_status,
        "version_created": result.version_created,
        "version_id": str(result.version_id) if result.version_id else None,
    }


@router.patch("/evidence/facts/{fact_id}/edit")
async def edit_fact(
    case_id: uuid.UUID,
    fact_id: uuid.UUID,
    body: EditFactInput,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    """Edit a fact. Creates a version snapshot. Requires ATTY_AUTH."""
    firm_uuid = uuid.UUID(ctx.firm_id)
    await _get_case(case_id, firm_uuid)
    _require_authority("trace.edit_fact_text", ctx)

    from datetime import date

    service = get_fact_review_service()
    request = EditFactRequest(
        fact_id=fact_id,
        fact_text=body.fact_text,
        fact_date=date.fromisoformat(body.fact_date) if body.fact_date else None,
        fact_type=body.fact_type,
        provider_id=uuid.UUID(body.provider_id) if body.provider_id else None,
        changed_by=uuid.UUID(ctx.user_id) if ctx.user_id else None,
        change_reason=body.change_reason,
    )
    result = await service.edit_fact(firm_uuid, request)

    if result.error:
        raise HTTPException(status_code=400, detail=result.error)

    await write_audit(
        actor_id=ctx.user_id, actor_type="ATTORNEY",
        action="fact.edited",
        resource_type="evidence_facts", resource_id=fact_id,
        case_id=case_id, firm_id=firm_uuid,
        details={"change_reason": body.change_reason},
    )

    return {
        "fact_id": str(result.fact_id),
        "version_created": result.version_created,
        "version_id": str(result.version_id) if result.version_id else None,
    }


@router.get("/evidence/contradictions")
async def list_contradictions(
    case_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    """List all contradiction pairs for a case."""
    firm_uuid = uuid.UUID(ctx.firm_id)
    await _get_case(case_id, firm_uuid)

    service = get_evidence_service()
    contradictions = await service.get_contradictions_for_case(firm_uuid, case_id)

    return {
        "case_id": str(case_id),
        "total_contradictions": len(contradictions),
        "contradictions": contradictions,
    }


@router.patch("/evidence/contradictions/{contradiction_id}/resolve")
async def resolve_contradiction(
    case_id: uuid.UUID,
    contradiction_id: uuid.UUID,
    body: ResolveContradictionInput,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    """Resolve a contradiction pair. Requires ATTY_AUTH."""
    firm_uuid = uuid.UUID(ctx.firm_id)
    await _get_case(case_id, firm_uuid)
    _require_authority("trace.resolve_contradiction", ctx)

    try:
        service = get_fact_review_service()
        result = await service.resolve_contradiction(
            firm_uuid,
            contradiction_id,
            body.resolution_status,
            uuid.UUID(ctx.user_id) if ctx.user_id else None,
            body.attorney_note,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await write_audit(
        actor_id=ctx.user_id, actor_type="ATTORNEY",
        action="contradiction.resolved",
        resource_type="contradiction_pairs", resource_id=contradiction_id,
        case_id=case_id, firm_id=firm_uuid,
        details={"resolution": body.resolution_status},
    )

    return result


@router.get("/evidence/missing-evidence")
async def list_missing_evidence(
    case_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    """List all missing-evidence signals for a case."""
    firm_uuid = uuid.UUID(ctx.firm_id)
    await _get_case(case_id, firm_uuid)

    service = get_evidence_service()
    signals = await service.get_missing_evidence_for_case(firm_uuid, case_id)

    return {
        "case_id": str(case_id),
        "total_signals": len(signals),
        "signals": signals,
    }


@router.patch("/evidence/missing-evidence/{signal_id}/dismiss")
async def dismiss_missing_evidence(
    case_id: uuid.UUID,
    signal_id: uuid.UUID,
    body: DismissSignalInput,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    """Dismiss a missing-evidence signal."""
    firm_uuid = uuid.UUID(ctx.firm_id)
    await _get_case(case_id, firm_uuid)

    try:
        service = get_fact_review_service()
        result = await service.dismiss_missing_evidence(
            firm_uuid,
            signal_id,
            uuid.UUID(ctx.user_id) if ctx.user_id else None,
            body.note,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    await write_audit(
        actor_id=ctx.user_id, actor_type="ATTORNEY",
        action="missing_evidence.dismissed",
        resource_type="missing_evidence_signals", resource_id=signal_id,
        case_id=case_id, firm_id=firm_uuid,
    )

    return result


@router.post("/evidence/rescan")
async def rescan_evidence(
    case_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    """Trigger a full rescan: re-extract facts, detect contradictions, generate missing-evidence."""
    firm_uuid = uuid.UUID(ctx.firm_id)
    await _get_case(case_id, firm_uuid)

    async with internal_tenant_session(
        tenant_id=firm_uuid, user_id=ctx.user_id, role=ctx.role
    ) as session:
        from app.models.document import Document as DocModel

        docs_result = await session.execute(
            select(DocModel).where(DocModel.case_id == case_id)
        )
        documents = docs_result.scalars().all()

        pages: list[dict] = []
        for doc in documents:
            pages.append({
                "document_id": str(doc.document_id),
                "page_number": 1,
                "redacted_text": "",
                "provider_id": str(doc.provider_id) if doc.provider_id else None,
            })

    service = get_evidence_service()
    result = await service.rescan_case(firm_uuid, case_id, pages)

    await write_audit(
        actor_id=ctx.user_id, actor_type="ATTORNEY",
        action="evidence.rescan",
        resource_type="cases", resource_id=case_id,
        case_id=case_id, firm_id=firm_uuid,
        details={
            "facts_created": result.facts_created,
            "contradictions_found": result.contradictions_found,
            "missing_evidence_signals": result.missing_evidence_signals,
        },
    )

    return {
        "case_id": str(case_id),
        "facts_created": result.facts_created,
        "contradictions_found": result.contradictions_found,
        "missing_evidence_signals": result.missing_evidence_signals,
        "errors": result.errors,
    }
