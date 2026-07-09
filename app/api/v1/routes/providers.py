"""Provider routes — CRUD + confirmation (Checkpoint 1)."""

from __future__ import annotations

import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthContext, get_current_context
from app.core.audit import write_audit
from app.core.database import get_db
from app.models.case import Case
from app.models.provider import Provider

router = APIRouter(prefix="/cases/{case_id}/providers", tags=["providers"])


async def _check_case_owner(
    case_id: str, firm_uuid: uuid.UUID, db: AsyncSession
) -> Case:
    case = (await db.execute(select(Case).where(Case.case_id == uuid.UUID(case_id)))).scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.firm_id != firm_uuid:
        raise HTTPException(status_code=403, detail="Not your case.")
    return case


async def _check_not_confirmed(case: Case) -> None:
    if case.provider_list_status != "DRAFT":
        raise HTTPException(
            status_code=400,
            detail="Provider list has already been confirmed and locked.",
        )


@router.get("")
async def list_providers(
    case_id: str,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    firm = uuid.UUID(ctx.firm_id)
    await _check_case_owner(case_id, firm, db)
    result = await db.execute(
        select(Provider).where(Provider.case_id == uuid.UUID(case_id))
    )
    rows = result.scalars().all()
    return {"providers": [r.to_summary() for r in rows], "count": len(rows)}


@router.put("/{provider_id}")
async def update_provider(
    case_id: str,
    provider_id: str,
    payload: dict,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    firm = uuid.UUID(ctx.firm_id)
    c = await _check_case_owner(case_id, firm, db)
    await _check_not_confirmed(c)

    row = (
        await db.execute(
            select(Provider).where(
                Provider.case_id == uuid.UUID(case_id),
                Provider.provider_id == uuid.UUID(provider_id),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Provider not found.")
    if row.confirmation_status == "REMOVED":
        raise HTTPException(status_code=400, detail="Provider has been removed.")

    updatable = {
        "provider_name", "facility_name", "npi_number", "fax_number",
        "address", "specialty",
    }
    for k in updatable:
        if k in payload:
            setattr(row, k, payload[k])
    if "confirmation_status" in payload and payload["confirmation_status"] in (
        "UNCONFIRMED", "CONFIRMED", "REMOVED"
    ):
        row.confirmation_status = payload["confirmation_status"]
    await db.commit()
    return row.to_summary()


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_provider(
    case_id: str,
    payload: dict,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    firm = uuid.UUID(ctx.firm_id)
    c = await _check_case_owner(case_id, firm, db)
    await _check_not_confirmed(c)

    provider = Provider(
        case_id=uuid.UUID(case_id),
        provider_name=payload.get("provider_name", "Unknown"),
        facility_name=payload.get("facility_name"),
        npi_number=payload.get("npi_number"),
        fax_number=payload.get("fax_number"),
        address=payload.get("address"),
        specialty=payload.get("specialty"),
        confirmation_status="UNCONFIRMED",
        extraction_confidence="LOW",
        source_reference="manual",
    )
    db.add(provider)
    await db.commit()
    return provider.to_summary()


@router.delete("/{provider_id}")
async def remove_provider(
    case_id: str,
    provider_id: str,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    firm = uuid.UUID(ctx.firm_id)
    c = await _check_case_owner(case_id, firm, db)
    await _check_not_confirmed(c)

    row = (
        await db.execute(
            select(Provider).where(
                Provider.case_id == uuid.UUID(case_id),
                Provider.provider_id == uuid.UUID(provider_id),
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Provider not found.")
    row.confirmation_status = "REMOVED"
    await db.commit()
    return {"status": "removed"}


@router.post("/confirm")
async def confirm_provider_list(
    case_id: str,
    request: Request,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Checkpoint 1: attorney confirms and LOCKS the provider list.

    At least one provider must be CONFIRMED before the list can be locked.
    Once locked, individual providers can no longer be edited (only removed via
    a documented override). Does NOT transmit any fax — that is a separate
    attorney action (Checkpoint 2).
    """
    firm = uuid.UUID(ctx.firm_id)
    c = await _check_case_owner(case_id, firm, db)
    await _check_not_confirmed(c)

    if c.case_stage == "PENDING_SIGNATURE":
        raise HTTPException(
            status_code=403,
            detail="Provider list cannot be confirmed before the client has signed the retainer and HIPAA authorization.",
        )

    confirmed_count = (
        await db.execute(
            select(func.count())
            .select_from(Provider)
            .where(
                Provider.case_id == uuid.UUID(case_id),
                Provider.confirmation_status == "CONFIRMED",
            )
        )
    ).scalar()
    if not confirmed_count:
        raise HTTPException(
            status_code=400,
            detail="At least one provider must be CONFIRMED before locking the list.",
        )

    # Lock the list at the case level (providers remain CONFIRMED). Once the list
    # is CONFIRMED, individual providers can no longer be edited.
    c.provider_list_status = "CONFIRMED"
    await db.commit()

    await write_audit(
        actor_id=ctx.user_id,
        actor_type="ATTORNEY",
        action="providers.confirmed",
        resource_type="providers",
        resource_id=uuid.UUID(case_id),
        case_id=uuid.UUID(case_id),
        firm_id=firm,
        correlation_id=getattr(request.state, "correlation_id", None),
        details={"confirmed_by": ctx.user_id},
    )

    return {
        "case_id": case_id,
        "provider_list_status": "CONFIRMED",
        "confirmed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
