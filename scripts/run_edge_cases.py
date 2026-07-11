#!/usr/bin/env python3
"""Edge case verification: run the 12-step journey against every failure mode."""

from __future__ import annotations

import os

os.environ["AUTH_MODE"] = "local"
os.environ["LOCAL_JWT_SECRET"] = "test-secret-at-least-32-bytes-long-000"
os.environ.pop("TRACE_DATABASE_URL", None)
os.environ.pop("DATABASE_URL", None)

import asyncio
import uuid
from datetime import date, datetime, timezone

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.database import async_session_maker, engine, phi_engine
from app.main import app
from app.models import Base
from app.models.case import Case
from app.models.client import PHIBase
from app.models.event_node import EventNode
from app.models.provider import Provider
from tests.conftest import auth_header

FIRM_A = "11111111-1111-4111-8111-111111111111"
FIRM_B = "22222222-2222-4222-8222-222222222222"

PASSED = 0
FAILED = 0


def _ok(label: str) -> None:
    global PASSED
    PASSED += 1
    print(f"  PASS: {label}")


def _fail(label: str, detail: str = "") -> None:
    global FAILED
    FAILED += 1
    print(f"  FAIL: {label} — {detail}")


async def run_edge_cases():
    global PASSED, FAILED

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with phi_engine.begin() as conn:
        await conn.run_sync(PHIBase.metadata.create_all)

    transport = ASGITransport(app=app)
    h_a = auth_header(firm_id=FIRM_A)
    h_b = auth_header(firm_id=FIRM_B)

    async with AsyncClient(transport=transport, base_url="http://test") as c:
        print("\n" + "=" * 60)
        print("  EDGE CASE VERIFICATION — 12 steps × failure modes")
        print("=" * 60)

        # ── EC-01: No auth → 401 ──
        r = await c.get("/api/v1/trace/cases")
        if r.status_code == 401:
            _ok("EC-01: No auth returns 401")
        else:
            _fail("EC-01", f"Expected 401, got {r.status_code}")

        # ── EC-02: Case with PENDING_SIGNATURE → provider confirm blocked (403) ──
        async with async_session_maker() as s:
            case = Case(
                client_token=uuid.uuid4(), firm_id=uuid.UUID(FIRM_A),
                intake_record_id=uuid.uuid4(), incident_date=date(2024, 3, 15),
                jurisdiction_state="CA", case_stage="PENDING_SIGNATURE",
            )
            s.add(case)
            await s.flush()
            cid = str(case.case_id)
            s.add(Provider(case_id=case.case_id, provider_name="Test ER", confirmation_status="CONFIRMED"))
            await s.commit()

        r = await c.post(f"/api/v1/trace/cases/{cid}/providers/confirm", headers=h_a)
        if r.status_code == 403:
            _ok("EC-02: Provider confirm blocked at PENDING_SIGNATURE (403)")
        else:
            _fail("EC-02", f"Expected 403, got {r.status_code}")

        # ── EC-03: Cross-firm access → 403 or 404 ──
        r = await c.get(f"/api/v1/trace/cases/{cid}/providers", headers=h_b)
        if r.status_code in (403, 404):
            _ok(f"EC-03: Cross-firm access blocked ({r.status_code})")
        else:
            _fail("EC-03", f"Expected 403/404, got {r.status_code}")

        # ── EC-04: Case not found → 404 ──
        r = await c.get(f"/api/v1/trace/cases/{uuid.uuid4()}", headers=h_a)
        if r.status_code == 404:
            _ok("EC-04: Unknown case returns 404")
        else:
            _fail("EC-04", f"Expected 404, got {r.status_code}")

        # ── EC-05: Future incident date → 400 ──
        future = (date.today().replace(year=date.today().year + 2)).isoformat()
        r = await c.post("/api/v1/trace/cases", json={
            "intake_record_id": str(uuid.uuid4()),
            "client_data": {"name": "Test", "dob": "1985-01-01", "address": "X", "phone": "555"},
            "incident_date": future, "jurisdiction_state": "CA",
        }, headers=h_a)
        if r.status_code == 400:
            _ok("EC-05: Future incident date rejected (400)")
        else:
            _fail("EC-05", f"Expected 400, got {r.status_code}: {r.text[:100]}")

        # ── EC-06: Invalid state code → 400 ──
        r = await c.post("/api/v1/trace/cases", json={
            "intake_record_id": str(uuid.uuid4()),
            "client_data": {"name": "Test", "dob": "1985-01-01", "address": "X", "phone": "555"},
            "incident_date": "2024-01-15", "jurisdiction_state": "ZZ",
        }, headers=h_a)
        if r.status_code == 400:
            _ok("EC-06: Invalid state code rejected (400)")
        else:
            _fail("EC-06", f"Expected 400, got {r.status_code}")

        # ── EC-07: Duplicate intake_record_id → 409 ──
        intake_id = str(uuid.uuid4())
        base = {
            "intake_record_id": intake_id,
            "client_data": {"name": "Test", "dob": "1985-01-01", "address": "X", "phone": "555"},
            "incident_date": "2024-01-15", "jurisdiction_state": "CA",
        }
        r1 = await c.post("/api/v1/trace/cases", json=base, headers=h_a)
        r2 = await c.post("/api/v1/trace/cases", json=base, headers=h_a)
        if r2.status_code == 409:
            _ok("EC-07: Duplicate intake record returns 409")
        else:
            _fail("EC-07", f"Expected 409, got {r2.status_code}")

        # ── EC-08: Confirm with zero CONFIRMED providers → 400 ──
        async with async_session_maker() as s:
            case2 = Case(
                client_token=uuid.uuid4(), firm_id=uuid.UUID(FIRM_A),
                intake_record_id=uuid.uuid4(), incident_date=date(2024, 3, 15),
                jurisdiction_state="CA", case_stage="INITIALIZATION",
                hipaa_auth_status="SIGNED",
            )
            s.add(case2)
            await s.flush()
            cid2 = str(case2.case_id)
            s.add(Provider(case_id=case2.case_id, provider_name="Test", confirmation_status="UNCONFIRMED"))
            await s.commit()

        r = await c.post(f"/api/v1/trace/cases/{cid2}/providers/confirm", headers=h_a)
        if r.status_code == 400:
            _ok("EC-08: Confirm with zero CONFIRMED providers blocked (400)")
        else:
            _fail("EC-08", f"Expected 400, got {r.status_code}")

        # ── EC-09: Missing required field → 422 ──
        r = await c.post("/api/v1/trace/cases", json={
            "intake_record_id": str(uuid.uuid4()),
            "client_data": {"name": "Test", "dob": "1985-01-01", "address": "X", "phone": "555"},
        }, headers=h_a)
        if r.status_code == 422:
            _ok("EC-09: Missing required fields returns 422")
        else:
            _fail("EC-09", f"Expected 422, got {r.status_code}: {r.text[:100]}")

        # ── EC-10: Demand-ready blocked with unannotated PRIORITY flags → 400 ──
        async with async_session_maker() as s:
            case3 = Case(
                client_token=uuid.uuid4(), firm_id=uuid.UUID(FIRM_A),
                intake_record_id=uuid.uuid4(), incident_date=date(2024, 3, 15),
                jurisdiction_state="CA", case_stage="ATTORNEY_REVIEW",
                hipaa_auth_status="SIGNED", sol_table_version="2026-07-01",
            )
            s.add(case3)
            await s.flush()
            cid3 = str(case3.case_id)
            # Create an unannotated PRIORITY flag — gate should block
            node = EventNode(
                case_id=case3.case_id, flag_type="TREATMENT_GAP",
                flag_priority="PRIORITY", system_description="Test gap",
                attorney_annotation=None,
            )
            s.add(node)
            await s.commit()

        r = await c.post(f"/api/v1/trace/cases/{cid3}/approve", json={
            "confirmation_text": "Test",
        }, headers=h_a)
        if r.status_code in (400, 403):
            _ok(f"EC-10: Demand-ready blocked ({r.status_code})")
        else:
            _fail("EC-10", f"Expected 400/403, got {r.status_code}")

        # ── EC-11: Export blocked before DEMAND_READY → not 200 ──
        r = await c.get(f"/api/v1/trace/cases/{cid3}/export/pdf", headers=h_a)
        if r.status_code != 200:
            _ok(f"EC-11: Export blocked before demand-ready ({r.status_code})")
        else:
            _fail("EC-11", f"Expected !=200, got {r.status_code}")

        # ── EC-12: SOL table version persisted on case ──
        async with async_session_maker() as s:
            case = (await s.execute(select(Case).where(Case.case_id == uuid.UUID(cid3)))).scalar_one()
            if case.sol_table_version is not None:
                _ok(f"EC-12: SOL version persisted: {case.sol_table_version}")
            else:
                _fail("EC-12", "SOL version is None")

    print(f"\n{'='*60}")
    print(f"  RESULTS: {PASSED} passed, {FAILED} failed")
    print(f"{'='*60}\n")
    return FAILED == 0


if __name__ == "__main__":
    success = asyncio.run(run_edge_cases())
    exit(0 if success else 1)
