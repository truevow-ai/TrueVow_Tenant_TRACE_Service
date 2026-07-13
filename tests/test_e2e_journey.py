"""End-to-end synthetic journey walkthrough test."""
import asyncio, json, os, sys, uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["ENVIRONMENT"] = "development"
os.environ["AUTH_MODE"] = "local"
os.environ["LOCAL_JWT_SECRET"] = "test-secret-at-least-32-bytes-long-000"

import jwt
import httpx

BASE = "http://test/api/v1/trace"

FIRM_ID = "11111111-1111-4111-8111-111111111111"
USER_ID = "synthetic_attorney_sarah_chen"


def auth_header():
    payload = {"sub": USER_ID, "firm_id": FIRM_ID, "role": "attorney", "mfa": True}
    token = jwt.encode(payload, os.environ["LOCAL_JWT_SECRET"], algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}


async def step(label, fn):
    print(f"\n[{label}] ", end="", flush=True)
    try:
        result = await fn()
        if isinstance(result, httpx.Response):
            status = "PASS" if 200 <= result.status_code < 300 else f"FAIL({result.status_code})"
            body = result.text[:120].replace("\n", " ")
        else:
            status, body = "PASS", str(result)[:120]
        print(f"{status} - {body}")
        return result
    except Exception as e:
        print(f"FAIL - {e}")
        return None


async def main():
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:

        # 1. Health
        r = await step("1. Health check", lambda: c.get("/health"))
        assert r and r.status_code == 200

        h = auth_header()

        # 2. Create case with client PHI
        case_data = {
            "intake_record_id": str(uuid.uuid4()),
            "client_data": {
                "name": "Maria Rodriguez",
                "dob": "1985-04-12",
                "address": "1247 Maple Ave, Los Angeles CA 90012",
                "phone": "+13235550198",
            },
            "incident_date": "2024-03-15",
            "jurisdiction_state": "CA",
        }
        r = await step("2. Create case", lambda: c.post(f"{BASE}/cases", json=case_data, headers=h))
        case_id = r.json().get("case_id") if r and r.status_code in (200, 201) else str(uuid.uuid4())
        print(f"       case_id={case_id}")

        # 3. Get case
        r = await step("3. Get case", lambda: c.get(f"{BASE}/cases/{case_id}", headers=h))
        if r and r.status_code == 200:
            print(f"       stage={r.json().get('case_stage','?')}")

        # 4. Providers
        r = await step("4. List providers", lambda: c.get(f"{BASE}/cases/{case_id}/providers", headers=h))

        # 5. Add provider
        provider_data = {"provider_name": "Cedars-Sinai Medical Center", "npi_number": "1346255124", "facility_name": "Cedars-Sinai ER", "fax_number": "3104238000", "specialty": "Emergency Medicine"}
        r = await step("5. Add provider", lambda: c.post(f"{BASE}/cases/{case_id}/providers", json=provider_data, headers=h))

        # 6. Liens
        r = await step("6. List liens", lambda: c.get(f"{BASE}/cases/{case_id}/liens", headers=h))

        # 7. Add lien
        r = await step("7. Add lien", lambda: c.post(f"{BASE}/cases/{case_id}/liens", json={"lien_type": "HEALTH_INSURANCE", "lienholder": "Blue Shield", "claimed_amount": 1847.50}, headers=h))

        # 8. Chronology
        r = await step("8. Get chronology", lambda: c.get(f"{BASE}/cases/{case_id}/chronology", headers=h))

        # 9. Readiness
        r = await step("9. Case readiness", lambda: c.get(f"{BASE}/cases/{case_id}/readiness", headers=h))

        # 10. Export (should 403 if not demand-ready)
        r = await step("10. Export PDF", lambda: c.get(f"{BASE}/cases/{case_id}/export", params={"format": "pdf"}, headers=h))

        # 11. Duplicate case (409 expected)
        r = await step("11. Duplicate case", lambda: c.post(f"{BASE}/cases", json=case_data, headers=h))

        print(f"\n=== JOURNEY COMPLETE ===")
        return case_id


if __name__ == "__main__":
    case_id = asyncio.run(main())
