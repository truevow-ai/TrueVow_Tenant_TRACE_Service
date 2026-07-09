"""Phase 1B verification: signing gate enforcement.

Confirms that provider actions are blocked until the client has signed
the HIPAA authorization and the case has advanced to INITIALIZATION.
"""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_header


def _case_payload(**over) -> dict:
    base = {
        "intake_record_id": str(uuid.uuid4()),
        "client_data": {
            "name": "Verify Gates",
            "dob": "1985-01-01",
            "address": "123 Test St",
            "phone": "+13105550000",
        },
        "incident_date": "2025-06-15",
        "jurisdiction_state": "CA",
    }
    base.update(over)
    return base


@pytest.mark.asyncio
async def test_provider_confirmation_blocked_before_signing(client):
    """Provider confirmation must be blocked until signing is complete."""
    firm = str(uuid.uuid4())
    resp = await client.post(
        "/api/v1/trace/cases",
        json=_case_payload(),
        headers=auth_header(firm_id=firm),
    )
    assert resp.status_code == 201
    assert resp.json()["stage"] == "PENDING_SIGNATURE"
    case_id = resp.json()["case_id"]

    confirm_resp = await client.post(
        f"/api/v1/trace/cases/{case_id}/providers/confirm",
        headers=auth_header(firm_id=firm),
    )
    assert confirm_resp.status_code == 403
    response_text = confirm_resp.text.lower()
    assert any(
        word in response_text
        for word in ["not yet signed", "pending", "awaiting", "signed", "signature", "client"]
    ), f"Expected signing gate message, got: {response_text[:200]}"


@pytest.mark.asyncio
async def test_sol_table_version_persisted_on_case(client):
    """SOL table version must be stored in DB, not just API response."""
    from sqlalchemy import select

    from app.core.database import async_session_maker
    from app.models.case import Case
    from app.services.sol import SOL_TABLE_VERSION

    firm = str(uuid.uuid4())
    resp = await client.post(
        "/api/v1/trace/cases",
        json=_case_payload(),
        headers=auth_header(firm_id=firm),
    )
    assert resp.status_code == 201
    case_id = resp.json()["case_id"]

    async with async_session_maker() as session:
        case = (await session.execute(
            select(Case).where(Case.case_id == uuid.UUID(case_id))
        )).scalar_one()
        assert case.sol_table_version is not None
        assert case.sol_table_version == SOL_TABLE_VERSION
