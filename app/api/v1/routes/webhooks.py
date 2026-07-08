"""Fax delivery-status webhook (Fax.Plus callback).

Machine-to-machine endpoint (no Clerk session). Optionally protected by a shared
secret header. Updates the matching ``record_requests`` row and writes an audit
entry. No PHI is accepted or returned.
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Header, HTTPException, Request
from sqlalchemy import select

from app.core.audit import write_audit
from app.core.config import settings
from app.core.database import async_session_maker
from app.models.record_request import RecordRequest

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_STATUS_MAP = {
    "success": "DELIVERED",
    "delivered": "DELIVERED",
    "sent": "DELIVERED",
    "failed": "FAILED",
    "error": "FAILED",
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
