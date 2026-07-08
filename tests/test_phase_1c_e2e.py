"""Phase 1C end-to-end: extract → confirm → send → status webhook + Checkpoint 2 gate."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.record_request import RecordRequest
from tests.conftest import auth_header


class MockFaxClient:
    def __init__(self, fail: bool = False):
        self.calls: list[tuple[str, bytes]] = []

    async def send(self, fax_number: str, cover_sheet_pdf: bytes, **kw) -> str:
        self.calls.append((fax_number, cover_sheet_pdf))
        return f"fax-tx-{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_phase_1c_e2e_extract_confirm_send_webhook(client):
    import app.services.providers as prov_mod
    from app.main import app
    from app.services.fax import get_fax_client

    mock_fax = MockFaxClient()

    class _FakeNPI:
        async def search(self, name, state=None, limit=5):
            return []

    app.dependency_overrides[get_fax_client] = lambda: mock_fax
    orig_npi = prov_mod.NPIClient
    prov_mod.NPIClient = _FakeNPI  # type: ignore[assignment,misc]

    try:
        firm = str(uuid.uuid4())

        # 1. Create case with provider hints (triggers background extraction).
        resp = await client.post(
            "/api/v1/trace/cases",
            json={
                "intake_record_id": str(uuid.uuid4()),
                "client_data": {"name": "J. Doe", "dob": "1980-06-15", "address": "addr", "phone": "555"},
                "incident_date": "2025-03-01",
                "jurisdiction_state": "CA",
                "provider_hints": ["Cedars-Sinai Medical Center"],
            },
            headers=auth_header(firm_id=firm),
        )
        assert resp.status_code == 201
        case_id = resp.json()["case_id"]

        # 2. List, mark confirmed, and lock (Checkpoint 1).
        provs = await client.get(f"/api/v1/trace/cases/{case_id}/providers", headers=auth_header(firm_id=firm))
        data = provs.json()
        assert data["count"] >= 1
        pid = data["providers"][0]["provider_id"]

        await client.put(
            f"/api/v1/trace/cases/{case_id}/providers/{pid}",
            json={"confirmation_status": "CONFIRMED", "fax_number": "3105551212"},
            headers=auth_header(firm_id=firm),
        )
        conf = await client.post(
            f"/api/v1/trace/cases/{case_id}/providers/confirm", headers=auth_header(firm_id=firm)
        )
        assert conf.status_code == 200

        # 3. Preview requests.
        prev = await client.get(f"/api/v1/trace/cases/{case_id}/requests", headers=auth_header(firm_id=firm))
        assert prev.status_code == 200
        assert prev.json()["requests"][0]["ready"] is True

        # 4. Send (Checkpoint 2).
        send = await client.post(
            f"/api/v1/trace/cases/{case_id}/requests/send", headers=auth_header(firm_id=firm)
        )
        assert send.status_code == 200
        manifest = send.json()["transmitted"]
        assert manifest[0]["status"] == "SENT"

        # Cover-sheet PDF was generated (non-empty bytes).
        assert mock_fax.calls
        assert len(mock_fax.calls[0][1]) > 100

        # 5. Webhook delivers confirmation.
        tx_id = manifest[0]["fax_transmission_id"]
        wh_resp = await client.post(
            "/api/v1/trace/webhooks/fax-status",
            json={"fax_transmission_id": tx_id, "status": "delivered"},
        )
        assert wh_resp.status_code == 200

        # 6. DB reflects DELIVERED.
        async with async_session_maker() as session:
            req = (
                await session.execute(select(RecordRequest).where(RecordRequest.fax_transmission_id == tx_id))
            ).scalar_one_or_none()
            assert req is not None
            assert req.status == "DELIVERED"
            assert req.confirmed_at is not None
    finally:
        app.dependency_overrides.clear()
        prov_mod.NPIClient = orig_npi  # type: ignore[misc]


@pytest.mark.asyncio
async def test_send_blocked_before_confirm(client):
    firm = str(uuid.uuid4())
    resp = await client.post(
        "/api/v1/trace/cases",
        json={
            "intake_record_id": str(uuid.uuid4()),
            "client_data": {"name": "Test", "dob": "2000-01-01", "address": "addr", "phone": "555"},
            "incident_date": "2025-01-15",
            "jurisdiction_state": "CA",
        },
        headers=auth_header(firm_id=firm),
    )
    assert resp.status_code == 201
    case_id = resp.json()["case_id"]
    r = await client.post(f"/api/v1/trace/cases/{case_id}/requests/send", headers=auth_header(firm_id=firm))
    assert r.status_code == 403  # Checkpoint 2 gate: list not confirmed


@pytest.mark.asyncio
async def test_cover_sheet_contains_no_pii():
    import inspect

    from app.services.cover_sheet import CoverSheetGenerator

    # Structural guarantee: the generator has NO parameter that could carry client
    # PII — it only accepts an opaque case_ref, provider details, and an auth ref.
    params = set(inspect.signature(CoverSheetGenerator.generate).parameters)
    for forbidden in ("client_name", "name", "dob", "patient", "address", "ssn"):
        assert forbidden not in params

    gen = CoverSheetGenerator()
    buf = gen.generate(
        case_ref=uuid.uuid4(),
        provider_name="Test Hospital",
        provider_fax="3105550000",
        return_fax="8005551111",
        hipaa_auth_ref="REF-NO-PII",
    )
    data = buf.read()
    assert data.startswith(b"%PDF")  # valid PDF
    assert len(data) > 500

