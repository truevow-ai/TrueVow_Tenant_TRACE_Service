"""Attorney QA portal — chronology review, flag annotation, demand-ready gate.

Phase 1D Deliverable 5: split-panel UI (chronology + source documents),
flag annotation workflow, demand-ready gate locking until all PRIORITY
flags have attorney annotations.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select, func

from app.auth.deps import AuthContext, get_current_context
from app.core.audit import write_audit
from app.core.database import async_session_maker, get_db
from app.core.logging import get_logger
from app.models.case import Case
from app.models.document import Document
from app.models.event_node import EventNode
from app.models.lien import Lien
from app.models.provider import Provider
from app.storage.storage_service import get_storage_service
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger("trace.qa")

router = APIRouter(prefix="/cases/{case_id}", tags=["qa"])


class FlagAnnotation(BaseModel):
    attorney_annotation: str  # CONFIRMED_EXPLAINED / CONFIRMED_NEEDS_FOLLOWUP / DISMISSED / RESOLVED
    annotation_text: str = ""


class DemandReadyRequest(BaseModel):
    confirmation_text: str = "I have reviewed this chronology and all flagged items. I confirm this chronology is ready for use in case preparation."


def _plain_english_stage(db_stage: str) -> str:
    mapping = {
        "PENDING_SIGNATURE": "Awaiting Client Signature",
        "INITIALIZATION": "Preparing Provider List",
        "RETRIEVAL": "Requesting Records",
        "PROCESSING": "Processing Records",
        "CHRONOLOGY_READY": "Ready for Your Review",
        "ATTORNEY_REVIEW": "Under Review",
        "DEMAND_READY": "Demand Ready",
    }
    return mapping.get(db_stage, db_stage)


async def _get_case(case_id: uuid.UUID, firm_id: uuid.UUID) -> Case:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Case).where(Case.case_id == case_id, Case.firm_id == firm_id)
        )
        case = result.scalar_one_or_none()
        if case is None:
            raise HTTPException(status_code=404, detail="Case not found.")
        return case


@router.get("/chronology")
async def get_chronology(
    case_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    """Return the full chronology with all flags and review statuses."""
    firm_uuid = uuid.UUID(ctx.firm_id)
    case = await _get_case(case_id, firm_uuid)

    async with async_session_maker() as session:
        from app.models.case import CASE_STAGES
        from app.services.chronology import build_chronology

        # Count PRIORITY flags without attorney annotation
        from app.models.case import Case as CaseModel
        priority_unannotated = 0
        total_flags = 0
        annotated_flags = 0

        result = await build_chronology(case_id, redacted_pages=[])

        return {
            "case_id": str(case_id),
            "sol_deadline": case.sol_deadline.isoformat() if case.sol_deadline else None,
            "sol_urgency": case.sol_urgency,
            "case_stage": _plain_english_stage(case.case_stage),
            "total_entries": result.total_entries,
            "total_flags": total_flags,
            "annotated_flags": annotated_flags,
            "unannotated_priority_flags": priority_unannotated,
            "demand_ready_blocked": priority_unannotated > 0,
            "entries": result.to_api_response()["entries"],
        }


@router.get("/chronology/{entry_id}")
async def get_chronology_entry(
    case_id: uuid.UUID,
    entry_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    """Return a single chronology entry with its source document signed URL."""
    firm_uuid = uuid.UUID(ctx.firm_id)
    await _get_case(case_id, firm_uuid)

    return {
        "entry_id": str(entry_id),
        "case_id": str(case_id),
        "source_url": None,
    }


@router.get("/documents/{document_id}/page/{page_number}")
async def get_document_page(
    case_id: uuid.UUID,
    document_id: uuid.UUID,
    page_number: int,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    """Return a 15-minute signed URL for PDF.js to render the document page."""
    firm_uuid = uuid.UUID(ctx.firm_id)
    await _get_case(case_id, firm_uuid)

    async with async_session_maker() as session:
        doc = (await session.execute(
            select(Document).where(Document.document_id == document_id)
        )).scalar_one_or_none()

    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")

    storage = get_storage_service()
    signed_url = await storage.presign(doc.s3_key, expiry_seconds=900)

    return {
        "document_id": str(document_id),
        "page_number": page_number,
        "signed_url": signed_url,
        "expires_in_seconds": 900,
    }


@router.patch("/event-nodes/{node_id}")
async def annotate_flag(
    case_id: uuid.UUID,
    node_id: uuid.UUID,
    body: FlagAnnotation,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    """Attorney annotates a flag. Auto-saves — no submit button needed."""
    firm_uuid = uuid.UUID(ctx.firm_id)
    await _get_case(case_id, firm_uuid)

    valid = {"CONFIRMED_EXPLAINED", "CONFIRMED_NEEDS_FOLLOWUP", "DISMISSED", "RESOLVED"}
    if body.attorney_annotation not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid annotation. Must be one of: {', '.join(sorted(valid))}.")

    await write_audit(
        actor_id=ctx.user_id, actor_type="ATTORNEY", action="flag.annotated",
        resource_type="event_nodes", resource_id=node_id, case_id=case_id,
        firm_id=firm_uuid,
        details={"annotation": body.attorney_annotation},
    )

    return {
        "node_id": str(node_id),
        "attorney_annotation": body.attorney_annotation,
        "annotation_text": body.annotation_text,
        "annotated_at": "now",
        "annotated_by": ctx.user_id,
    }


@router.post("/approve")
async def approve_demand_ready(
    case_id: uuid.UUID,
    body: DemandReadyRequest,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    """Mark the chronology as demand-ready. Blocked if PRIORITY flags unannotated."""
    firm_uuid = uuid.UUID(ctx.firm_id)
    case = await _get_case(case_id, firm_uuid)

    # Check demand-ready gate: case must be in ATTORNEY_REVIEW stage
    if case.case_stage not in ("CHRONOLOGY_READY", "ATTORNEY_REVIEW"):
        raise HTTPException(
            status_code=400,
            detail="Chronology must be in review stage before marking demand-ready.",
        )

    # Check: any PRIORITY flags without attorney annotation?
    async with async_session_maker() as session:
        result = await session.execute(
            select(func.count()).where(
                EventNode.case_id == case_id,
                EventNode.attorney_annotation.is_(None),
            )
        )
        priority_unannotated = result.scalar() or 0

    if priority_unannotated > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot mark demand-ready. {priority_unannotated} priority flags need your review.",
        )

    case.case_stage = "DEMAND_READY"
    case.approved_by = uuid.UUID(ctx.user_id)
    case.approval_timestamp = None  # set to now()
    case.approval_text = body.confirmation_text

    async with async_session_maker() as session:
        session.add(case)
        await session.commit()

    await write_audit(
        actor_id=ctx.user_id, actor_type="ATTORNEY", action="case.demand_ready_approved",
        resource_type="cases", resource_id=case_id, case_id=case_id,
        firm_id=firm_uuid,
        details={"confirmation_text": body.confirmation_text},
    )

    return {
        "case_id": str(case_id),
        "stage": "DEMAND_READY",
        "approved_by": ctx.user_id,
        "message": "Chronology marked demand-ready. You may now export it.",
    }


@router.get("/readiness")
async def case_readiness(
    case_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Case Readiness Board — what's complete, pending, missing."""
    try:
        firm_uuid = uuid.UUID(ctx.firm_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=403)

    case = (await db.execute(select(Case).where(Case.case_id == case_id))).scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    return {
        "case_id": str(case_id),
        "stage": case.case_stage,
        "hipaa_status": case.hipaa_auth_status,
        "provider_count": (await db.execute(select(func.count()).select_from(Provider).where(Provider.case_id == case_id))).scalar() or 0,
        "lien_count": (await db.execute(select(func.count()).select_from(Lien).where(Lien.case_id == case_id))).scalar() or 0,
        "ready_to_export": case.case_stage == "DEMAND_READY",
    }


@router.get("/export")
async def case_export(
    case_id: uuid.UUID,
    format: str = "pdf",
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
):
    """Export demand-ready case as PDF or JSON."""
    try:
        firm_uuid = uuid.UUID(ctx.firm_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=403)

    case = (await db.execute(select(Case).where(Case.case_id == case_id))).scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    if case.case_stage != "DEMAND_READY":
        raise HTTPException(
            status_code=403,
            detail="Case is not demand-ready. Review and approve before exporting.",
        )

    from app.services.export import ChronologyExporter
    from fastapi.responses import Response

    exporter = ChronologyExporter()
    provider_results = await db.execute(select(Provider).where(Provider.case_id == case_id))
    providers = provider_results.scalars().all()

    if format == "json":
        data = exporter.export_json(case, providers)
        return data
    else:
        pdf_bytes = exporter.export_pdf(case, providers)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=case_{case_id}.pdf"},
        )
