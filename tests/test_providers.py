"""Provider extraction skeleton tests (NPI client mocked — no network)."""

from __future__ import annotations

import datetime
import uuid

import pytest
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.case import Case
from app.models.provider import Provider
from app.services.providers import extract_providers


class FakeNPIClient:
    def __init__(self, results_by_name: dict[str, list[dict]]):
        self._results = results_by_name

    async def search(self, name: str, state: str | None = None, limit: int = 5) -> list[dict]:
        return self._results.get(name, [])


async def _make_case(firm_id: uuid.UUID) -> uuid.UUID:
    async with async_session_maker() as session:
        case = Case(
            client_token=uuid.uuid4(),
            firm_id=firm_id,
            intake_record_id=uuid.uuid4(),
            incident_date=datetime.date(2025, 1, 15),
            jurisdiction_state="CA",
        )
        session.add(case)
        await session.commit()
        return case.case_id


@pytest.mark.asyncio
async def test_extraction_confidence_high_medium_low():
    case_id = await _make_case(uuid.uuid4())
    fake = FakeNPIClient(
        {
            "Cedars Sinai": [
                {"npi_number": "1234567890", "name": "Cedars Sinai", "facility": "Cedars Sinai",
                 "fax": "3105550000", "address": "LA, CA", "specialty": "Emergency Medicine"}
            ],
            "Dr Smith": [
                {"npi_number": "1111111111", "name": "John Smith", "facility": None,
                 "fax": None, "address": None, "specialty": "Orthopedics"},
                {"npi_number": "2222222222", "name": "Jane Smith", "facility": None,
                 "fax": None, "address": None, "specialty": "Cardiology"},
            ],
            "Unknown Clinic": [],
        }
    )

    count = await extract_providers(
        case_id, ["Cedars Sinai", "Dr Smith", "Unknown Clinic"], "CA", npi_client=fake
    )
    assert count == 3

    async with async_session_maker() as session:
        rows = (await session.execute(select(Provider).where(Provider.case_id == case_id))).scalars().all()
    by_conf = {r.source_reference: r.extraction_confidence for r in rows}
    assert by_conf["intake:Cedars Sinai"] == "HIGH"
    assert by_conf["intake:Dr Smith"] == "MEDIUM"
    assert by_conf["intake:Unknown Clinic"] == "LOW"
    # All created providers start UNCONFIRMED (attorney must confirm — Checkpoint 1).
    assert all(r.confirmation_status == "UNCONFIRMED" for r in rows)


@pytest.mark.asyncio
async def test_no_hints_creates_nothing():
    case_id = await _make_case(uuid.uuid4())
    assert await extract_providers(case_id, [], "CA") == 0


@pytest.mark.asyncio
async def test_npi_failure_falls_back_to_low_confidence():
    case_id = await _make_case(uuid.uuid4())

    class BoomClient:
        async def search(self, name, state=None, limit=5):
            raise RuntimeError("NPI down")

    count = await extract_providers(case_id, ["Some Provider"], "CA", npi_client=BoomClient())
    assert count == 1
    async with async_session_maker() as session:
        row = (await session.execute(select(Provider).where(Provider.case_id == case_id))).scalar_one()
    assert row.extraction_confidence == "LOW"
    assert row.provider_name == "Some Provider"
