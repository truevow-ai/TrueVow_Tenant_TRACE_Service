"""Cases router — case initialization (Checkpoint-free trigger) + firm-scoped list."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthContext, get_current_context
from app.core.audit import write_audit
from app.core.database import get_db
from app.models.case import Case
from app.schemas.cases import CaseCreateRequest, CaseCreateResponse
from app.services.phi_store import store_client
from app.services.providers import extract_providers
from app.services.sol import calculate_sol

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
        return {"cases": [], "count": 0}

    result = await db.execute(select(Case).where(Case.firm_id == firm_uuid))
    cases = result.scalars().all()
    return {"cases": [c.to_summary() for c in cases], "count": len(cases)}


@router.post("", response_model=CaseCreateResponse, status_code=status.HTTP_201_CREATED)
async def initialize_case(
    payload: CaseCreateRequest,
    request: Request,
    background: BackgroundTasks,
    ctx: AuthContext = Depends(get_current_context),
    db: AsyncSession = Depends(get_db),
) -> CaseCreateResponse:
    """Initialize a TRACE case from an intake record (spec §4.2).

    Encrypts client PII to the PHI store (operational DB sees only a token),
    resolves the SOL (preferring the INTAKE snapshot), creates the case, and
    triggers async provider extraction.
    """
    # Firm identity: the token is authoritative; a body firm_id must not disagree.
    try:
        firm_uuid = uuid.UUID(ctx.firm_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid firm identity.") from None
    if payload.firm_id is not None and payload.firm_id != firm_uuid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="firm_id does not match the authenticated firm."
        )

    # Validation.
    if payload.incident_date > date.today():
        raise HTTPException(status_code=400, detail="Incident date cannot be in the future.")
    state = payload.jurisdiction_state.upper()

    # Duplicate guard (spec §4.2): one case per intake record.
    existing = await db.execute(
        select(Case).where(Case.intake_record_id == payload.intake_record_id)
    )
    dup = existing.scalar_one_or_none()
    if dup is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A case already exists for this intake record (case_id={dup.case_id}).",
        )

    # SOL — prefer the INTAKE statute snapshot, else the fallback table.
    snapshot = payload.intake_statute
    try:
        sol = calculate_sol(
            payload.incident_date,
            state,
            sol_years=snapshot.sol_years if snapshot else None,
            reference=snapshot.reference if snapshot else None,
        )
    except KeyError:
        raise HTTPException(
            status_code=400, detail=f"'{state}' is not a recognized US state code."
        ) from None

    # Encrypt PII into the separate PHI store; operational DB gets only the token.
    client_token = await store_client(
        name=payload.client_data.name,
        dob=payload.client_data.dob,
        address=payload.client_data.address,
        phone=payload.client_data.phone,
        firm_id=firm_uuid,
    )

    case = Case(
        client_token=client_token,
        firm_id=firm_uuid,
        intake_record_id=payload.intake_record_id,
        incident_date=payload.incident_date,
        jurisdiction_state=state,
        sol_deadline=sol.sol_deadline,
        sol_urgency=sol.urgency,
        sol_table_version=sol.table_version,
        # case_stage defaults to PENDING_SIGNATURE per database constraint.
        # Only the DocuSeal webhook advances it to INITIALIZATION.
    )
    db.add(case)
    await db.commit()

    await write_audit(
        actor_id=ctx.user_id,
        actor_type="SYSTEM",
        action="case.initialized",
        resource_type="cases",
        resource_id=case.case_id,
        case_id=case.case_id,
        firm_id=firm_uuid,
        correlation_id=getattr(request.state, "correlation_id", None),
        details={"sol_source": sol.source, "sol_urgency": sol.urgency},
    )

    # Provider extraction runs after the response is returned (does not block).
    if payload.provider_hints:
        background.add_task(extract_providers, case.case_id, payload.provider_hints, state)

    return CaseCreateResponse(
        case_id=str(case.case_id),
        sol_deadline=sol.sol_deadline.isoformat() if sol.sol_deadline else None,
        sol_urgency=sol.urgency,
        sol_disclaimer=sol.disclaimer,
        stage=case.case_stage,
    )
