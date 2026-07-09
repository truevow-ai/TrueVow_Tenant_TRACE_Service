"""Phase 1C verification: fax gates and PHI-free cover sheets.

Three non-negotiable gates before Phase 1C is complete:
1. No fax without signed HIPAA authorization
2. No fax without confirmed provider list
3. Cover sheet must not accept client PII parameters
"""

from __future__ import annotations

import inspect
import uuid

import pytest

from tests.conftest import auth_header


def _case_payload(**over) -> dict:
    base = {
        "intake_record_id": str(uuid.uuid4()),
        "client_data": {
            "name": "Verify Phase1C",
            "dob": "1985-06-15",
            "address": "123 Test St",
            "phone": "+13105550000",
        },
        "incident_date": "2025-03-01",
        "jurisdiction_state": "CA",
        "provider_hints": [],
    }
    base.update(over)
    return base


@pytest.mark.asyncio
async def test_fax_blocked_without_hipaa_authorization(client):
    """Fax transmission must be blocked until hipaa_auth_status = SIGNED."""


    firm = str(uuid.uuid4())
    resp = await client.post(
        "/api/v1/trace/cases",
        json=_case_payload(),
        headers=auth_header(firm_id=firm),
    )
    assert resp.status_code == 201
    case_id = resp.json()["case_id"]

    # Attempt to send fax without signed HIPAA — must fail
    send_resp = await client.post(
        f"/api/v1/trace/cases/{case_id}/requests/send",
        headers=auth_header(firm_id=firm),
    )
    assert send_resp.status_code in (400, 403), (
        f"Expected 400/403, got {send_resp.status_code}. "
        f"Fax must be blocked before HIPAA authorization is signed."
    )


@pytest.mark.asyncio
async def test_fax_blocked_without_confirmed_provider_list(client):
    """Fax transmission must be blocked if no providers are confirmed."""
    from sqlalchemy import select

    from app.core.database import async_session_maker
    from app.models.case import Case

    firm = str(uuid.uuid4())
    resp = await client.post(
        "/api/v1/trace/cases",
        json=_case_payload(),
        headers=auth_header(firm_id=firm),
    )
    assert resp.status_code == 201
    case_id = resp.json()["case_id"]

    # Simulate signing complete
    async with async_session_maker() as session:
        case = (await session.execute(
            select(Case).where(Case.case_id == uuid.UUID(case_id))
        )).scalar_one()
        case.case_stage = "INITIALIZATION"
        case.hipaa_auth_status = "SIGNED"
        await session.commit()

    # Attempt to send fax without confirmed providers — must fail
    send_resp = await client.post(
        f"/api/v1/trace/cases/{case_id}/requests/send",
        headers=auth_header(firm_id=firm),
    )
    assert send_resp.status_code in (400, 403), (
        f"Expected 400/403, got {send_resp.status_code}. "
        f"Fax must be blocked before provider list is confirmed."
    )


def test_cover_sheet_accepts_no_client_pii_params():
    """Cover sheet generator must not accept client PII in its signature."""
    from app.services.cover_sheet import CoverSheetGenerator

    params = set(inspect.signature(CoverSheetGenerator.generate).parameters)
    forbidden = {"client_name", "name", "dob", "patient", "address", "ssn", "phone", "email"}
    for field in forbidden:
        assert field not in params, (
            f"CoverSheetGenerator.generate() must not accept '{field}'. "
            f"PHI must never appear in fax cover sheets."
        )

    required = {"case_ref", "provider_name", "provider_fax"}
    for field in required:
        assert field in params, (
            f"CoverSheetGenerator.generate() must accept '{field}'."
        )
