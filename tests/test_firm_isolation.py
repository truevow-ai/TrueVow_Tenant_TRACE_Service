"""Phase 1A acceptance: firm A cannot read firm B's data."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_header, seed_case


@pytest.mark.asyncio
async def test_firm_cannot_read_another_firms_cases(client):
    firm_a = str(uuid.uuid4())
    firm_b = str(uuid.uuid4())

    case_id = await seed_case(firm_a)

    # Firm A sees its own case.
    resp_a = await client.get("/api/v1/trace/cases", headers=auth_header(firm_id=firm_a))
    assert resp_a.status_code == 200
    body_a = resp_a.json()
    assert body_a["count"] == 1
    assert body_a["cases"][0]["case_id"] == case_id

    # Firm B sees nothing — no leakage across firms.
    resp_b = await client.get("/api/v1/trace/cases", headers=auth_header(firm_id=firm_b))
    assert resp_b.status_code == 200
    body_b = resp_b.json()
    assert body_b["count"] == 0
    assert body_b["cases"] == []
