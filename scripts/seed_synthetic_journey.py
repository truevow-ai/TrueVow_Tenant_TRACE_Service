#!/usr/bin/env python3
"""Seed a complete synthetic case for the TRACE user journey walkthrough.

Seeds ONE complete synthetic case with attorney, client, providers,
documents, billing, and lien. All data is SYNTHETIC — no real PHI.

Usage:
    python scripts/seed_synthetic_journey.py [--case-ref SYNTHETIC-001]

Outputs a summary of what was seeded and the case_id for the walkthrough.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import date, datetime, timezone
from io import BytesIO

# Synthetic data constants
SYNTHETIC_ATTORNEY = {
    "firm_id": uuid.UUID("11111111-1111-4111-8111-111111111111"),
    "user_id": "synthetic_attorney_sarah_chen",
    "name": "Sarah Chen, Esq.",
    "firm": "Chen PI Law",
    "bar": "CA Bar #298471",
    "email": "sarah.chen@synthetic.truevow.law",
    "phone": "(213) 555-0147",
}

SYNTHETIC_CLIENT = {
    "name": "Maria Rodriguez",
    "dob": "1985-04-12",
    "phone": "(323) 555-0198",
    "address": "1247 Maple Ave, Los Angeles CA 90012",
}

SYNTHETIC_INCIDENT = {
    "incident_date": date(2024, 3, 15),
    "jurisdiction_state": "CA",
    "description": "Motor vehicle accident — rear-end collision at intersection of Wilshire Blvd and Vermont Ave, Los Angeles CA",
}


def _gen_pdf(title: str, content: str) -> bytes:
    """Generate a minimal synthetic PDF with embedded text layer."""
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    y = 700
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, title)
    y -= 20
    c.setFont("Helvetica", 10)
    for line in content.split("\n"):
        if y < 50:
            c.showPage()
            y = 700
            c.setFont("Helvetica", 10)
        c.drawString(50, y, line[:120])
        y -= 14
    c.save()
    buffer.seek(0)
    return buffer.read()


def seed_synthetic_case(case_ref: str = "SYNTHETIC-001") -> str:
    """Seed a complete synthetic case. Returns case_id string."""
    from sqlalchemy import select

    from app.core.config import settings
    from app.core.database import async_session_maker, phi_session_maker
    from app.models.case import Case
    from app.models.client import Client
    from app.models.lien import Lien
    from app.models.medical_bill import MedicalBillLine
    from app.models.provider import Provider
    from app.models.record_request import RecordRequest
    from app.services.phi_store import store_client

    import asyncio

    async def _seed() -> str:
        print("\n" + "=" * 60)
        print(f"  TRACE SYNTHETIC JOURNEY SEEDER — {case_ref}")
        print("=" * 60)

        # Ensure tables exist (synthetic seeder runs standalone, not via pytest conftest)
        from app.core.database import engine, phi_engine
        from app.models import Base
        from app.models.client import PHIBase

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with phi_engine.begin() as conn:
            await conn.run_sync(PHIBase.metadata.create_all)

        firm_id = SYNTHETIC_ATTORNEY["firm_id"]

        # ── Encrypt + store synthetic client in PHI store ──
        client_token = await store_client(
            name=SYNTHETIC_CLIENT["name"],
            dob=SYNTHETIC_CLIENT["dob"],
            address=SYNTHETIC_CLIENT["address"],
            phone=SYNTHETIC_CLIENT["phone"],
            firm_id=firm_id,
        )
        print(f"  [OK] Synthetic client stored: token={client_token}")

        # ── Create case ──
        async with async_session_maker() as session:
            case = Case(
                client_token=client_token,
                firm_id=firm_id,
                intake_record_id=uuid.uuid4(),
                incident_date=SYNTHETIC_INCIDENT["incident_date"],
                jurisdiction_state=SYNTHETIC_INCIDENT["jurisdiction_state"],
                sol_deadline=date(2026, 3, 15),
                sol_urgency="Standard",
                sol_table_version="2026-07-01",
                hipaa_auth_status="SIGNED",
                case_stage="INITIALIZATION",
                signing_completed_at=datetime(2024, 3, 16, tzinfo=timezone.utc),
            )
            session.add(case)
            await session.flush()
            case_id = str(case.case_id)
            print(f"  [OK] Synthetic case created: {case_id}")

            # ── 3 providers ──
            providers_data = [
                {
                    "provider_name": "Cedars-Sinai Medical Center",
                    "npi_number": "1346255124",
                    "facility_name": "Cedars-Sinai Emergency Department",
                    "fax_number": "3104238000",
                    "specialty": "Emergency Medicine",
                    "confirmation_status": "CONFIRMED",
                    "extraction_confidence": "CONFIRMED",
                    "source_reference": "intake:went straight to Cedars-Sinai ER",
                },
                {
                    "provider_name": "Valley Chiropractic Center - Los Angeles",
                    "npi_number": None,
                    "facility_name": "Valley Chiropractic Center",
                    "fax_number": "3105551234",
                    "specialty": "Chiropractic",
                    "confirmation_status": "UNCONFIRMED",
                    "extraction_confidence": "NEEDS_CLIENT_CONFIRMATION",
                    "source_reference": "intake:chiropractor on Vermont Ave",
                },
                {
                    "provider_name": "Marina Physical Therapy",
                    "npi_number": None,
                    "facility_name": "Marina Physical Therapy",
                    "fax_number": "",
                    "specialty": "Physical Therapy",
                    "confirmation_status": "UNCONFIRMED",
                    "extraction_confidence": "DO_NOT_REQUEST",
                    "source_reference": "intake:PT twice a week in Marina del Rey",
                },
            ]
            provider_ids: list[str] = []
            for pd in providers_data:
                p = Provider(case_id=case.case_id, **pd)
                session.add(p)
                await session.flush()
                provider_ids.append(str(p.provider_id))
            print(f"  [OK] 3 providers seeded")

            # ── Lien ──
            lien = Lien(
                case_id=case.case_id,
                firm_id=firm_id,
                lien_type="HEALTH_INSURANCE",
                lienholder="Blue Shield of California",
                claimed_amount=1847.50,
                status="NOT_CHECKED",
                notes="Synthetic lien for user journey testing",
            )
            session.add(lien)
            print(f"  [OK] Lien seeded: Blue Shield — $1,847.50")

            # ── Medical bill ──
            bill = MedicalBillLine(
                case_id=case.case_id,
                firm_id=firm_id,
                document_id=uuid.uuid4(),
                provider_id=uuid.UUID(provider_ids[0]),
                date_of_service=date(2024, 3, 15),
                cpt_code="99285",
                icd10_codes="S13.4XXA,M54.2",
                billed_amount=4200.00,
                match_confidence="STRONG_MATCH",
                needs_review=False,
            )
            session.add(bill)
            print(f"  [OK] Billing seeded: CPT 99285 — $4,200.00")

            await session.commit()

        print(f"\n  {'='*60}")
        print(f"  [OK] COMPLETE — {case_ref} ready for walkthrough")
        print(f"  Case ID: {case_id}")
        print(f"  Attorney: {SYNTHETIC_ATTORNEY['name']} ({SYNTHETIC_ATTORNEY['email']})")
        print(f"  Client: {SYNTHETIC_CLIENT['name']} (SYNTHETIC)")
        print(f"  Providers: 3 (1 CONFIRMED, 1 NEEDS_CLIENT, 1 DO_NOT_REQUEST)")
        print(f"  Lien: 1 (NOT_CHECKED)")
        print(f"  Bill: 1 (STRONG_MATCH)")
        print(f"  {'='*60}\n")
        return case_id

    return asyncio.run(_seed())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed synthetic TRACE case")
    parser.add_argument("--case-ref", default="SYNTHETIC-001", help="Case reference label")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be created without touching database")
    parser.add_argument("--confirm-synthetic", action="store_true", help="Confirm synthetic data usage")
    parser.add_argument("--environment", default="development", help="Environment (development | staging)")
    args = parser.parse_args()

    if args.dry_run:
        print("=" * 60)
        print(f"  TRACE SYNTHETIC JOURNEY SEEDER -- DRY RUN")
        print("=" * 60)
        print(f"\n  Would create:")
        print(f"  [OK] Synthetic client: {SYNTHETIC_CLIENT['name']}")
        print(f"  [OK] Case: {SYNTHETIC_INCIDENT['description'][:60]}...")
        print(f"  [OK] Attorney: {SYNTHETIC_ATTORNEY['name']}")
        print(f"  [OK] Firm ID: {SYNTHETIC_ATTORNEY['firm_id']}")
        print(f"  [OK] Providers: 3 (1 CONFIRMED, 1 NEEDS_CLIENT, 1 DO_NOT_REQUEST)")
        print(f"  [OK] Lien: 1 (NOT_CHECKED)")
        print(f"  [OK] Bill: 1 (STRONG_MATCH)")
        print(f"\n  [WARN] firm_id is hardcoded UUID format")
        print(f"     Current: {SYNTHETIC_ATTORNEY['firm_id']}")
        print(f"     Expected after M1: org_synthetic_test_001 (Clerk org_id TEXT)")
        print(f"     M1 migration handles conversion -- no fix needed now")
        print(f"\n  Database: NOT TOUCHED (dry run)")
        print(f"  Environment: {args.environment}")
        print(f"  Confirm synthetic: {'YES' if args.confirm_synthetic else 'NO (required for live run)'}")
        sys.exit(0)

    if not args.confirm_synthetic:
        print("ERROR: --confirm-synthetic required for live database writes", file=sys.stderr)
        sys.exit(1)

    try:
        case_id = seed_synthetic_case(args.case_ref)
        print(f"\nCASE_ID={case_id}")
    except Exception as exc:
        print(f"\n[FAIL] Seed failed: {exc}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
