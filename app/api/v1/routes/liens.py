"""Lien tracking endpoints — attorney-managed, firm-scoped.

ADR-004 §3: TRACE tracks lien status. Does not detect liens automatically.
Tier 3 (attorney judgment only).
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
from app.models.lien import Lien

logger = get_logger("trace.liens")

router = APIRouter(prefix="/cases/{case_id}/liens", tags=["liens"])


class LienCreate(BaseModel):
    lien_type: str
    lienholder: str | None = None
    claimed_amount: float | None = None
    status: str = "NOT_CHECKED"
    notes: str | None = None


class LienUpdate(BaseModel):
    lien_type: str | None = None
    lienholder: str | None = None
    claimed_amount: float | None = None
    status: str | None = None
    notes: str | None = None


@router.post("", status_code=201)
async def create_lien(
    case_id: uuid.UUID,
    body: LienCreate,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    firm_uuid = uuid.UUID(ctx.firm_id)
    lien = Lien(
        case_id=case_id,
        firm_id=firm_uuid,
        lien_type=body.lien_type,
        lienholder=body.lienholder,
        claimed_amount=body.claimed_amount,
        status=body.status,
        notes=body.notes,
    )
    async with async_session_maker() as session:
        session.add(lien)
        await session.commit()

    await write_audit(
        actor_id=ctx.user_id, actor_type="ATTORNEY", action="lien.created",
        resource_type="liens", resource_id=lien.lien_id, case_id=case_id,
        firm_id=firm_uuid,
    )
    return {
        "lien_id": str(lien.lien_id),
        "case_id": str(case_id),
        "lien_type": lien.lien_type,
        "status": lien.status,
    }


@router.get("")
async def list_liens(
    case_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    firm_uuid = uuid.UUID(ctx.firm_id)
    async with async_session_maker() as session:
        result = await session.execute(
            select(Lien).where(Lien.case_id == case_id, Lien.firm_id == firm_uuid)
        )
        liens = result.scalars().all()
    return {
        "case_id": str(case_id),
        "liens": [
            {
                "lien_id": str(l.lien_id), "lien_type": l.lien_type,
                "lienholder": l.lienholder, "claimed_amount": float(l.claimed_amount) if l.claimed_amount else None,
                "status": l.status, "notes": l.notes,
            }
            for l in liens
        ],
    }


@router.get("/{lien_id}")
async def get_lien(
    case_id: uuid.UUID,
    lien_id: uuid.UUID,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    firm_uuid = uuid.UUID(ctx.firm_id)
    async with async_session_maker() as session:
        lien = (await session.execute(
            select(Lien).where(Lien.lien_id == lien_id, Lien.case_id == case_id, Lien.firm_id == firm_uuid)
        )).scalar_one_or_none()
    if lien is None:
        raise HTTPException(status_code=404, detail="Lien not found.")
    return {
        "lien_id": str(lien.lien_id), "lien_type": lien.lien_type,
        "lienholder": lien.lienholder, "claimed_amount": float(lien.claimed_amount) if lien.claimed_amount else None,
        "status": lien.status, "notes": lien.notes,
    }


@router.patch("/{lien_id}")
async def update_lien(
    case_id: uuid.UUID,
    lien_id: uuid.UUID,
    body: LienUpdate,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    firm_uuid = uuid.UUID(ctx.firm_id)
    async with async_session_maker() as session:
        lien = (await session.execute(
            select(Lien).where(Lien.lien_id == lien_id, Lien.case_id == case_id, Lien.firm_id == firm_uuid)
        )).scalar_one_or_none()
        if lien is None:
            raise HTTPException(status_code=404, detail="Lien not found.")
        for field, value in body.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(lien, field, value)
        await session.commit()
    return {"lien_id": str(lien_id), "status": lien.status}
