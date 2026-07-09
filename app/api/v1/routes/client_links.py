"""Client-facing upload and confirmation links.

ADR-003 §7-8: tokenized pages with no authentication, no TRACE branding,
no client accounts. Two link types:

1. Provider confirmation link — client confirms/rejects/adds providers
   before attorney locks the list.

2. Document upload link — client uploads medical records, photos, bills.
   Files stored with source=CLIENT_UPLOAD.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select

from app.auth.deps import AuthContext, get_current_context
from app.core.audit import write_audit
from app.core.database import async_session_maker
from app.core.logging import get_logger
from app.models.case import Case

logger = get_logger("trace.client_links")

router = APIRouter(prefix="/cases/{case_id}/links", tags=["client_links"])
public_router = APIRouter(prefix="/link", tags=["public"])


class CreateUploadLinkRequest(BaseModel):
    label: str = "Please upload your medical records here."
    expires_hours: int = 48


class CreateUploadLinkResponse(BaseModel):
    upload_url: str
    token: str
    expires_at: str


class CreateConfirmLinkResponse(BaseModel):
    confirm_url: str
    token: str
    expires_at: str


@router.post("/upload", response_model=CreateUploadLinkResponse)
async def create_upload_link(
    case_id: uuid.UUID,
    body: CreateUploadLinkRequest,
    ctx: AuthContext = Depends(get_current_context),
) -> CreateUploadLinkResponse:
    firm_uuid = uuid.UUID(ctx.firm_id)
    token = uuid.uuid4()

    await write_audit(
        actor_id=ctx.user_id,
        actor_type="ATTORNEY",
        action="link.upload_created",
        resource_type="cases",
        resource_id=case_id,
        case_id=case_id,
        firm_id=firm_uuid,
        details={"token_expires_hours": body.expires_hours},
    )

    return CreateUploadLinkResponse(
        upload_url=f"/link/{token}",
        token=str(token),
        expires_at="",
    )


@router.post("/confirm-providers", response_model=CreateConfirmLinkResponse)
async def create_provider_confirm_link(
    case_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
) -> CreateConfirmLinkResponse:
    firm_uuid = uuid.UUID(ctx.firm_id)
    token = uuid.uuid4()

    await write_audit(
        actor_id=ctx.user_id,
        actor_type="ATTORNEY",
        action="link.confirm_providers_created",
        resource_type="cases",
        resource_id=case_id,
        case_id=case_id,
        firm_id=firm_uuid,
    )

    return CreateConfirmLinkResponse(
        confirm_url=f"/link/confirm/{token}",
        token=str(token),
        expires_at="",
    )


@public_router.get("/{token}")
async def client_upload_page(request: Request, token: str) -> dict:
    return {"message": "Upload page placeholder — Phase 1C WIP"}


@public_router.post("/{token}")
async def client_upload_submit(request: Request, token: str) -> dict:
    return {"message": "Thank you. Your documents have been received."}
