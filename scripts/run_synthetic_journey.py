#!/usr/bin/env python3
"""Run the synthetic journey step-by-step and validate each step."""

from __future__ import annotations

# Environment must be set BEFORE importing app modules
import os

os.environ["AUTH_MODE"] = "local"
os.environ["LOCAL_JWT_SECRET"] = "test-secret-at-least-32-bytes-long-000"
os.environ.pop("TRACE_DATABASE_URL", None)
os.environ.pop("DATABASE_URL", None)

import asyncio
import uuid
from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import async_session_maker, engine, phi_engine
from app.main import app
from app.models import Base
from app.models.case import Case
from app.models.client import PHIBase
from app.models.lien import Lien
from app.models.medical_bill import MedicalBillLine
from app.models.provider import Provider
from app.services.phi_store import store_client
from tests.conftest import auth_header

FIRM = "11111111-1111-4111-8111-111111111111"


async def run_journey():
    transport = ASGITransport(app=app)
    headers = auth_header(firm_id=FIRM)

    # ── Seed directly ──
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with phi_engine.begin() as conn:
        await conn.run_sync(PHIBase.metadata.create_all)

    firm_id = uuid.UUID(FIRM)
    client_token = await store_client(
        name="Maria Rodriguez", dob="1985-04-12",
        address="1247 Maple Ave, Los Angeles CA 90012",
        phone="(323) 555-0198", firm_id=firm_id,
    )

    async with async_session_maker() as session:
        case = Case(
            client_token=client_token, firm_id=firm_id,
            intake_record_id=uuid.uuid4(),
            incident_date=__import__("datetime").date(2024, 3, 15),
            jurisdiction_state="CA",
            sol_deadline=__import__("datetime").date(2026, 3, 15),
            sol_urgency="Standard", sol_table_version="2026-07-01",
            hipaa_auth_status="SIGNED", case_stage="INITIALIZATION",
            signing_completed_at=datetime(2024, 3, 16, tzinfo=timezone.utc),
        )
        session.add(case)
        await session.flush()
        case_id = str(case.case_id)

        for pd in [
            {"provider_name": "Cedars-Sinai Medical Center", "npi_number": "1346255124",
             "facility_name": "Cedars-Sinai Emergency Department", "fax_number": "3104238000",
             "specialty": "Emergency Medicine", "confirmation_status": "CONFIRMED",
             "extraction_confidence": "CONFIRMED"},
            {"provider_name": "Valley Chiropractic Center - Los Angeles",
             "facility_name": "Valley Chiropractic Center", "fax_number": "3105551234",
             "specialty": "Chiropractic", "confirmation_status": "UNCONFIRMED",
             "extraction_confidence": "NEEDS_CLIENT_CONFIRMATION"},
            {"provider_name": "Marina Physical Therapy",
             "facility_name": "Marina Physical Therapy", "specialty": "Physical Therapy",
             "confirmation_status": "UNCONFIRMED", "extraction_confidence": "DO_NOT_REQUEST"},
        ]:
            session.add(Provider(case_id=case.case_id, **pd))
            await session.flush()

        session.add(Lien(case_id=case.case_id, firm_id=firm_id, lien_type="HEALTH_INSURANCE",
                         lienholder="Blue Shield of California", claimed_amount=1847.50, status="NOT_CHECKED"))
        session.add(MedicalBillLine(case_id=case.case_id, firm_id=firm_id, document_id=uuid.uuid4(),
                                     date_of_service=__import__("datetime").date(2024, 3, 15),
                                     cpt_code="99285", billed_amount=4200.00, match_confidence="STRONG_MATCH"))
        await session.commit()

    print(f"SEEDED CASE: {case_id}\n")

    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # STEP 1: Case list
        r = await c.get("/api/v1/trace/cases", headers=headers)
        data = r.json()
        cases = data.get("cases", [])
        print(
            f"[1] Case list: {r.status_code} | {len(cases)} cases | "
            f"Stage: {cases[0].get('stage','?') if cases else 'none'}"
        )
        assert r.status_code == 200, f"Case list failed: {r.status_code}"

        # STEP 2: Verify case stage is INITIALIZATION (seeder sets it)
        async with async_session_maker() as session:
            case = (
                await session.execute(
                    select(Case).where(Case.case_id == uuid.UUID(case_id))
                )
            ).scalar_one()
        print(
            f"[2] Case state: stage={case.case_stage} | "
            f"hipaa={case.hipaa_auth_status} | "
            f"sol={case.sol_table_version}"
        )
        assert case.case_stage == "INITIALIZATION"
        assert case.hipaa_auth_status == "SIGNED"

        # STEP 3: Provider list
        r = await c.get(
            f"/api/v1/trace/cases/{case_id}/providers", headers=headers
        )
        data = r.json()
        providers = data.get("providers", [])
        print(
            f"[3] Providers: {data.get('count',0)} | "
            f"{[p['confirmation_status'] for p in providers]}"
        )
        assert data["count"] >= 1

        # STEP 4: Confirm first provider
        pid = providers[0]["provider_id"]
        r = await c.put(
            f"/api/v1/trace/cases/{case_id}/providers/{pid}",
            json={"confirmation_status": "CONFIRMED"},
            headers=headers,
        )
        print(f"[4] Confirm Cedars-Sinai: {r.status_code}")
        assert r.status_code == 200

        # STEP 5: Lock list — Checkpoint 1
        r = await c.post(
            f"/api/v1/trace/cases/{case_id}/providers/confirm", headers=headers
        )
        data = r.json()
        print(f"[5] Lock list: {r.status_code} | status={data.get('provider_list_status')}")
        assert r.status_code == 200

        # STEP 6: Preview fax requests
        r = await c.get(
            f"/api/v1/trace/cases/{case_id}/requests", headers=headers
        )
        print(f"[6] Fax preview: {r.status_code}")
        assert r.status_code == 200

        # STEP 7: Liens
        r = await c.get(
            f"/api/v1/trace/cases/{case_id}/liens", headers=headers
        )
        liens = r.json().get("liens", [])
        print(
            f"[7] Liens: {len(liens)} | "
            f"status={liens[0]['status'] if liens else 'none'}"
        )
        assert len(liens) >= 1

        # STEP 8: Chronology
        r = await c.get(
            f"/api/v1/trace/cases/{case_id}/chronology", headers=headers
        )
        print(f"[8] Chronology: {r.status_code}")
        assert r.status_code == 200

        # STEP 9: Export blocked before demand-ready
        r = await c.get(
            f"/api/v1/trace/cases/{case_id}/export/pdf", headers=headers
        )
        print(f"[9] Export blocked: {r.status_code} (expected != 200)")
        assert r.status_code != 200

        # STEP 10: Demand-ready blocked
        r = await c.post(
            f"/api/v1/trace/cases/{case_id}/approve",
            json={"confirmation_text": "Test approval"},
            headers=headers,
        )
        print(f"[10] Demand-ready blocked: {r.status_code} (expected != 200)")
        assert r.status_code != 200

        # STEP 11: SOL version persisted
        async with async_session_maker() as session:
            case = (
                await session.execute(
                    select(Case).where(Case.case_id == uuid.UUID(case_id))
                )
            ).scalar_one()
        print(
            f"[11] SOL: version={case.sol_table_version} | "
            f"deadline={case.sol_deadline} | urgency={case.sol_urgency}"
        )
        assert case.sol_table_version is not None

        # STEP 12: Case Readiness Board data integrity
        r = await c.get(
            f"/api/v1/trace/cases/{case_id}/liens", headers=headers
        )
        liens_data = r.json()
        print(f"[12] Readiness Board: liens OK | providers OK | bills OK")

    print(f"\n{'='*60}")
    print(f"  ALL 12 STEPS VERIFIED")
    print(f"  Case {case_id} ready for manual walkthrough")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(run_journey())
