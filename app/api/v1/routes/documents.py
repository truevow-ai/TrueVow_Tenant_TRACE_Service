"""Document routes — attorney upload + portal link ingestion."""
from __future__ import annotations

import uuid

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthContext, get_current_context
from app.core.database import get_db
from app.models.case import Case
from app.models.document import Document
from app.storage.storage_service import get_storage_service

router = APIRouter(prefix="/cases/{case_id}/documents", tags=["documents"])


class PortalLinkPayload(BaseModel):
    url: str
    filename: str | None = None


async def _get_case(case_id: uuid.UUID, firm_id: uuid.UUID, db: AsyncSession) -> Case:
    result = await db.execute(
        select(Case).where(Case.case_id == case_id, Case.firm_id == firm_id)
    )
    case = result.scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case


@router.post("/upload")
async def attorney_upload(
    case_id: uuid.UUID,
    file: UploadFile = File(...),
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Attorney uploads a document — drag-and-drop PDFs from portal downloads."""
    firm_uuid = uuid.UUID(ctx.firm_id)
    await _get_case(case_id, firm_uuid, db)

    contents = await file.read()
    filename = file.filename or f"upload_{uuid.uuid4().hex[:12]}.pdf"
    storage_key = f"cases/{case_id}/{filename}"

    storage = get_storage_service()
    await storage.upload(storage_key, contents, file.content_type or "application/pdf")

    doc = Document(
        case_id=case_id,
        s3_bucket="trace-medical-records",
        s3_key=storage_key,
        document_type="MEDICAL_RECORD",
        page_count=0,
        ocr_status="PENDING",
        source="ATTORNEY_UPLOAD",
        original_filename=filename,
    )
    db.add(doc)
    await db.commit()

    return {"document_id": str(doc.document_id), "filename": filename, "status": "uploaded"}


@router.post("/portal-link")
async def portal_link_ingestion(
    case_id: uuid.UUID,
    body: PortalLinkPayload,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Ingest a document from a secure portal download URL."""
    firm_uuid = uuid.UUID(ctx.firm_id)
    await _get_case(case_id, firm_uuid, db)

    filename = body.filename or f"portal_{uuid.uuid4().hex[:12]}.pdf"
    storage_key = f"cases/{case_id}/{filename}"

    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        response = await client.get(body.url)
        response.raise_for_status()
        contents = response.content

    storage = get_storage_service()
    await storage.upload(storage_key, contents, "application/pdf")

    doc = Document(
        case_id=case_id,
        s3_bucket="trace-medical-records",
        s3_key=storage_key,
        document_type="MEDICAL_RECORD",
        page_count=0,
        ocr_status="PENDING",
        source="ATTORNEY_UPLOAD",
        original_filename=filename,
    )
    db.add(doc)
    await db.commit()

    return {
        "document_id": str(doc.document_id),
        "filename": filename,
        "source_url": body.url,
        "status": "ingested",
    }
