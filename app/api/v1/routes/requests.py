"""Record-request routes — preview + transmit (Checkpoint 2)."""

from __future__ import annotations

import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthContext, get_current_context
from app.core.audit import write_audit
from app.core.config import settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.models.case import Case
from app.models.provider import Provider
from app.models.record_request import RecordRequest
from app.services.cover_sheet import CoverSheetGenerator
from app.services.fax import FaxClient, get_fax_client

logger = get_logger("trace.requests")

router = APIRouter(prefix="/cases/{case_id}/requests", tags=["requests"])

_RECORD_TYPES = "ER records, Imaging, PT notes, Billing, Pharmacy, Specialist notes"


async def _owned_case(case_id: str, firm: uuid.UUID, db: AsyncSession) -> Case:
    case = (await db.execute(select(Case).where(Case.case_id == uuid.UUID(case_id)))).scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    if case.firm_id != firm:
        raise HTTPException(status_code=403, detail="Not your case.")
    return case


async def _confirmed_providers(case_id: str, db: AsyncSession) -> list[Provider]:
    rows = (
        await db.execute(
            select(Provider).where(
                Provider.case_id == uuid.UUID(case_id),
                Provider.confirmation_status == "CONFIRMED",
            )
        )
    ).scalars().all()
    return list(rows)


@router.get("")
async def preview_requests(
    case_id: str,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    firm = uuid.UUID(ctx.firm_id)
    await _owned_case(case_id, firm, db)
    providers = await _confirmed_providers(case_id, db)
    return {
        "case_id": case_id,
        "record_types": _RECORD_TYPES,
        "requests": [
            {
                "provider_id": str(p.provider_id),
                "provider_name": p.provider_name,
                "fax_number": p.fax_number,
                "ready": bool(p.fax_number),
            }
            for p in providers
        ],
    }


@router.post("/send")
async def send_requests(
    case_id: str,
    request: Request,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
    fax: FaxClient = Depends(get_fax_client),
) -> dict:
    """Checkpoint 2: attorney approves and transmits record requests.

    Hard gate: the provider list must be CONFIRMED first (spec Part 1.4) — else
    403 'Provider list not yet confirmed by attorney.'
    """
    firm = uuid.UUID(ctx.firm_id)
    case = await _owned_case(case_id, firm, db)

    if case.provider_list_status != "CONFIRMED":
        raise HTTPException(status_code=403, detail="Provider list not yet confirmed by attorney.")

    providers = await _confirmed_providers(case_id, db)
    faxable = [p for p in providers if p.fax_number]
    if not faxable:
        raise HTTPException(status_code=400, detail="No confirmed providers have a fax number.")

    generator = CoverSheetGenerator()
    manifest = []
    now = datetime.datetime.now(datetime.timezone.utc)
    for p in faxable:
        cover = generator.generate(
            case_ref=case.case_id,
            provider_name=p.provider_name,
            provider_fax=p.fax_number or "",
            return_fax=settings.fax_return_number or "N/A",
            hipaa_auth_ref=settings.hipaa_auth_reference,
            record_types=_RECORD_TYPES,
        )
        req = RecordRequest(
            case_id=case.case_id,
            provider_id=p.provider_id,
            fax_number=p.fax_number or "",
            status="PENDING",
        )
        try:
            transmission_id = await fax.send(p.fax_number or "", cover.getvalue())
            req.fax_transmission_id = transmission_id
            req.status = "SENT"
            req.transmitted_at = now
            p.retrieval_status = "REQUESTED"
            p.last_request_sent = now
        except Exception as exc:  # noqa: BLE001 — record failure, keep going
            req.status = "FAILED"
            req.error_detail = str(exc)[:500]
            logger.warning("Fax send failed for provider %s: %s", p.provider_id, exc)
        db.add(req)
        manifest.append({"provider_id": str(p.provider_id), "status": req.status,
                         "fax_transmission_id": req.fax_transmission_id})

    if any(m["status"] == "SENT" for m in manifest):
        case.case_stage = "RETRIEVAL"
    await db.commit()

    await write_audit(
        actor_id=ctx.user_id,
        actor_type="ATTORNEY",
        action="requests.transmitted",
        resource_type="requests",
        resource_id=case.case_id,
        case_id=case.case_id,
        firm_id=firm,
        correlation_id=getattr(request.state, "correlation_id", None),
        details={"manifest": manifest},
    )

    return {"case_id": case_id, "transmitted": manifest}
