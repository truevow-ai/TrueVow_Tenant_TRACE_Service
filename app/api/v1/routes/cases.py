"""Cases router.

Phase 1A ships a firm-scoped read endpoint so the isolation acceptance criterion
is exercised end-to-end. Case creation (``POST /cases``) and the provider flow
arrive in Phase 1B/1C, strictly after Phase 1A acceptance passes.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthContext, get_current_context
from app.core.database import get_db
from app.models.case import Case

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("")
async def list_cases(
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List cases for the authenticated firm only.

    Isolation is enforced two ways: RLS (``app.current_tenant_id``) on Postgres,
    and the explicit ``firm_id`` filter here (which also protects the SQLite path).
    """
    try:
        firm_uuid = uuid.UUID(ctx.firm_id)
    except (ValueError, TypeError):
        # A non-UUID firm identity can own no cases in Phase 1A's UUID schema.
        return {"cases": [], "count": 0}

    result = await db.execute(select(Case).where(Case.firm_id == firm_uuid))
    cases = result.scalars().all()
    return {"cases": [c.to_summary() for c in cases], "count": len(cases)}
