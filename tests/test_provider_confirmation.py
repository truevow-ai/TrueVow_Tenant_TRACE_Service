"""Phase 1C: provider confirmation CRUD + Checkpoint 1 gate."""

from __future__ import annotations

import datetime
import uuid

import pytest
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.case import Case
from app.models.provider import Provider
from tests.conftest import auth_header


async def _seed_case_with_provider(firm: str, *, confirmed: bool = False) -> tuple[str, str]:
    async with async_session_maker() as session:
        case = Case(
            client_token=uuid.uuid4(),
            firm_id=uuid.UUID(firm),
            intake_record_id=uuid.uuid4(),
            incident_date=datetime.date(2025, 1, 15),
            jurisdiction_state="CA",
        )
        session.add(case)
        await session.flush()
        provider = Provider(
            case_id=case.case_id,
            provider_name="Cedars-Sinai Medical Center",
            fax_number="3105551212",
            confirmation_status="CONFIRMED" if confirmed else "UNCONFIRMED",
            extraction_confidence="HIGH",
            source_reference="intake",
        )
        session.add(provider)
        await session.commit()
        return str(case.case_id), str(provider.provider_id)


@pytest.mark.asyncio
async def test_list_and_add_provider(client):
    firm = str(uuid.uuid4())
    case_id, _ = await _seed_case_with_provider(firm)
    r = await client.get(f"/api/v1/trace/cases/{case_id}/providers", headers=auth_header(firm_id=firm))
    assert r.status_code == 200
    assert r.json()["count"] == 1

    add = await client.post(
        f"/api/v1/trace/cases/{case_id}/providers",
        json={"provider_name": "Westside Imaging", "fax_number": "3105559999"},
        headers=auth_header(firm_id=firm),
    )
    assert add.status_code == 201
    assert add.json()["confirmation_status"] == "UNCONFIRMED"


@pytest.mark.asyncio
async def test_confirm_requires_at_least_one_confirmed(client):
    firm = str(uuid.uuid4())
    case_id, _ = await _seed_case_with_provider(firm, confirmed=False)
    r = await client.post(
        f"/api/v1/trace/cases/{case_id}/providers/confirm", headers=auth_header(firm_id=firm)
    )
    assert r.status_code == 400  # nothing CONFIRMED yet


@pytest.mark.asyncio
async def test_checkpoint1_confirm_locks_list(client):
    firm = str(uuid.uuid4())
    case_id, _ = await _seed_case_with_provider(firm, confirmed=True)
    r = await client.post(
        f"/api/v1/trace/cases/{case_id}/providers/confirm", headers=auth_header(firm_id=firm)
    )
    assert r.status_code == 200
    assert r.json()["provider_list_status"] == "CONFIRMED"

    async with async_session_maker() as session:
        case = (await session.execute(select(Case).where(Case.case_id == uuid.UUID(case_id)))).scalar_one()
        prov = (await session.execute(select(Provider).where(Provider.case_id == uuid.UUID(case_id)))).scalars().all()
    assert case.provider_list_status == "CONFIRMED"
    # Providers remain CONFIRMED; the lock is enforced at the case level.
    assert all(p.confirmation_status == "CONFIRMED" for p in prov)


@pytest.mark.asyncio
async def test_cannot_edit_after_confirm(client):
    firm = str(uuid.uuid4())
    case_id, provider_id = await _seed_case_with_provider(firm, confirmed=True)
    await client.post(f"/api/v1/trace/cases/{case_id}/providers/confirm", headers=auth_header(firm_id=firm))
    r = await client.put(
        f"/api/v1/trace/cases/{case_id}/providers/{provider_id}",
        json={"provider_name": "Changed"},
        headers=auth_header(firm_id=firm),
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_other_firm_cannot_touch_providers(client):
    firm_a = str(uuid.uuid4())
    firm_b = str(uuid.uuid4())
    case_id, _ = await _seed_case_with_provider(firm_a)
    r = await client.get(f"/api/v1/trace/cases/{case_id}/providers", headers=auth_header(firm_id=firm_b))
    assert r.status_code == 403
