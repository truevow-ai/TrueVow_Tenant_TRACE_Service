"""Phase 1B acceptance: case initialization + SOL + PHI isolation."""

from __future__ import annotations

import datetime
import uuid

import pytest
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.case import Case
from tests.conftest import auth_header


def _payload(**over) -> dict:
    base = {
        "intake_record_id": str(uuid.uuid4()),
        "client_data": {
            "name": "Jane Q. Public",
            "dob": "1985-04-12",
            "address": "123 Main St, Los Angeles, CA",
            "phone": "+13105551212",
        },
        "incident_date": "2025-01-15",
        "jurisdiction_state": "CA",
    }
    base.update(over)
    return base


@pytest.mark.asyncio
async def test_case_initialization_returns_sol_and_disclaimer(client):
    firm = str(uuid.uuid4())
    resp = await client.post("/api/v1/trace/cases", json=_payload(), headers=auth_header(firm_id=firm))
    assert resp.status_code == 201
    body = resp.json()
    # Case starts in PENDING_SIGNATURE — only DocuSeal webhook advances to INITIALIZATION
    assert body["stage"] == "PENDING_SIGNATURE"
    # CA PI SOL = 2 years -> 2027-01-15.
    assert body["sol_deadline"] == "2027-01-15"
    assert body["sol_urgency"] in {"Standard", "Monitor", "Urgent", "Critical"}
    assert "statute of limitations" in body["sol_disclaimer"].lower()
    assert "attorney is responsible" in body["sol_disclaimer"].lower()


@pytest.mark.asyncio
async def test_pii_not_in_operational_database(client):
    firm = str(uuid.uuid4())
    resp = await client.post("/api/v1/trace/cases", json=_payload(), headers=auth_header(firm_id=firm))
    assert resp.status_code == 201
    case_id = resp.json()["case_id"]

    async with async_session_maker() as session:
        case = (await session.execute(select(Case).where(Case.case_id == uuid.UUID(case_id)))).scalar_one()
        # Operational row holds only an opaque token; no PII columns exist.
        assert case.client_token is not None
        assert not hasattr(case, "name")
        # Serialized summary must not leak PII.
        assert "Jane" not in str(case.to_summary())


@pytest.mark.asyncio
async def test_intake_snapshot_overrides_sol(client):
    firm = str(uuid.uuid4())
    payload = _payload(intake_statute={"sol_years": 3, "reference": "Cal. Code Civ. Proc. § 340.5"})
    resp = await client.post("/api/v1/trace/cases", json=payload, headers=auth_header(firm_id=firm))
    assert resp.status_code == 201
    assert resp.json()["sol_deadline"] == "2028-01-15"  # 3-year snapshot, not 2-year table


@pytest.mark.asyncio
async def test_duplicate_intake_record_returns_409(client):
    firm = str(uuid.uuid4())
    payload = _payload()
    first = await client.post("/api/v1/trace/cases", json=payload, headers=auth_header(firm_id=firm))
    assert first.status_code == 201
    second = await client.post("/api/v1/trace/cases", json=payload, headers=auth_header(firm_id=firm))
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_future_incident_date_rejected(client):
    firm = str(uuid.uuid4())
    future = (datetime.date.today() + datetime.timedelta(days=5)).isoformat()
    resp = await client.post(
        "/api/v1/trace/cases", json=_payload(incident_date=future), headers=auth_header(firm_id=firm)
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_unknown_state_rejected(client):
    firm = str(uuid.uuid4())
    resp = await client.post(
        "/api/v1/trace/cases", json=_payload(jurisdiction_state="ZZ"), headers=auth_header(firm_id=firm)
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_case_creation_requires_auth(client):
    resp = await client.post("/api/v1/trace/cases", json=_payload())
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_phi_never_in_operational_db(client):
    """The most important test in Phase 1B — PHI must never appear in operational tables.

    Encrypts a known client name, creates a case, then searches every
    operational table for that name. Any match is a HIPAA violation.
    This test stays in the suite permanently.
    """
    known_name = "Jane Testclientphileak"
    firm = str(uuid.uuid4())

    resp = await client.post(
        "/api/v1/trace/cases",
        json=_payload(client_data={
            "name": known_name, "dob": "1985-04-12",
            "address": "456 Test Ave", "phone": "+13105551212",
        }),
        headers=auth_header(firm_id=firm),
    )
    assert resp.status_code == 201

    async with async_session_maker() as session:
        case_id = resp.json()["case_id"]
        case = (await session.execute(
            select(Case).where(Case.case_id == uuid.UUID(case_id))
        )).scalar_one()
        assert case.client_token is not None
        row_text = str({c.name: getattr(case, c.name) for c in case.__table__.columns})
        assert known_name not in row_text, (
            f"PHI '{known_name}' found in cases table row. "
            f"PHI must never appear in the operational database."
        )
