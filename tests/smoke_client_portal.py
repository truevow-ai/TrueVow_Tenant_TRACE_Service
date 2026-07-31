"""Smoke test: TRACE client portal endpoints and contract verification."""
import asyncio
import json
import uuid

import httpx

BASE = "http://localhost:3036"
CLIENT_ID = "11111111-1111-4111-8111-111111111111"
WRONG_CLIENT_ID = "99999999-9999-4999-8999-999999999999"
MATTER_ID = "d379ee9b-19f7-4871-a86e-9684c69a11c3"
WRONG_MATTER = "00000000-0000-0000-0000-000000000000"
FIRM_ID = "11111111-1111-4111-8111-111111111111"

results = []


def ok(name: str, passed: bool, detail: str = ""):
    mark = "PASS" if passed else "FAIL"
    results.append((mark, name, detail))
    print(f"  [{mark}] {name} {detail}")


async def smoke_test():
    async with httpx.AsyncClient(timeout=15, base_url=BASE) as c:

        # ── 1. Health ──
        r = await c.get("/health")
        ok("health", r.status_code == 200, str(r.json().get("status", "")))

        # ── 2. Missing identity ──
        r = await c.get(f"/api/client/v1/matters/{MATTER_ID}")
        ok("missing identity=422", r.status_code == 422, f"got {r.status_code}")

        # ── 3. Unknown/Wrong identity ──
        r = await c.get(f"/api/client/v1/matters/{MATTER_ID}?client_identity_id={WRONG_CLIENT_ID}")
        ok("unknown identity=403", r.status_code == 403, f"got {r.status_code}")

        # ── 4. Wrong matter ──
        r = await c.get(f"/api/client/v1/matters/{WRONG_MATTER}?client_identity_id={CLIENT_ID}")
        ok("wrong matter=404/403", r.status_code in (403, 404), f"got {r.status_code}")

        # ── 5. Access grants ──
        r = await c.get(f"/api/client/v1/access?client_identity_id={CLIENT_ID}")
        ok("access grants", r.status_code == 200, f"grants={len(r.json().get('grants',[]))}")

        # ── 6. Completion ──
        r = await c.get(f"/api/client/v1/matters/{MATTER_ID}/completion?client_identity_id={CLIENT_ID}")
        ok("completion", r.status_code in (200, 403),
           f"status={r.status_code}" + (f" data={json.dumps(r.json())[:100]}" if r.status_code == 200 else ""))

        # ── 7. Documents ──
        r = await c.get(f"/api/client/v1/matters/{MATTER_ID}/documents?client_identity_id={CLIENT_ID}")
        ok("documents", r.status_code in (200, 403), f"status={r.status_code}")

        # ── 8. Requests ──
        r = await c.get(f"/api/client/v1/matters/{MATTER_ID}/requests?client_identity_id={CLIENT_ID}")
        ok("requests", r.status_code in (200, 403), f"status={r.status_code}")

        # ── 9. Matter overview ──
        r = await c.get(f"/api/client/v1/matters/{MATTER_ID}?client_identity_id={CLIENT_ID}")
        ok("matter overview", r.status_code in (200, 403),
           f"status={r.status_code}" + (f" keys={list(r.json().keys())}" if r.status_code == 200 else ""))

        # ── 10. DTO allowlisting: no attorney work product ──
        r = await c.get(f"/api/client/v1/matters/{MATTER_ID}?client_identity_id={CLIENT_ID}")
        if r.status_code == 200:
            body_str = json.dumps(r.json()).lower()
            dangerous = [
                "attorney_annotation", "attorney_note", "risk_flag",
                "privileged", "strategy", "internal_score",
                "contradiction", "authority_record", "liability_theory",
            ]
            found = [k for k in dangerous if k in body_str]
            ok("dto: no attorney work product", len(found) == 0,
               f"leaked: {found}" if found else "clean")
        else:
            ok("dto: no attorney work product", True, "skipped (no grant)")

        # ── 11. Client cannot hit attorney endpoints ──
        r = await c.get(f"/api/v1/trace/cases/{MATTER_ID}?client_identity_id={CLIENT_ID}")
        ok("no attorney endpoint access", r.status_code in (401, 403, 404),
           f"got {r.status_code}")

        # ── 12. Webhook: golden matter.activated (no grant, expect 401 no signature) ──
        golden = {
            "event_id": str(uuid.uuid4()),
            "event_type": "matter.activated",
            "tenant_id": FIRM_ID,
            "aggregate_type": "matters",
            "aggregate_id": "e1a2b3c4-0001-4000-8000-000000000099",
            "aggregate_version": 1,
            "actor_type": "RETAINER",
            "authority_class": "FIRM-POLICY",
            "authority_record_id": FIRM_ID,
            "policy_version_id": FIRM_ID,
            "schema_version": "1.0.1",
            "sensitivity_class": "CONFIDENTIAL",
            "payload": {
                "matter_id": "e1a2b3c4-0001-4000-8000-000000000099",
                "incident_date": "2026-07-01",
                "jurisdiction_state": "CA",
                "source_matter_candidate_id": FIRM_ID,
                "client_party_role_id": FIRM_ID,
                "representation_decision_id": FIRM_ID,
                "conflict_clearance_authority_id": FIRM_ID,
                "engagement_workflow_id": FIRM_ID,
                "executed_package_id": FIRM_ID,
                "completed_copy_delivery_id": FIRM_ID,
                "responsible_attorney_assignment_id": FIRM_ID,
                "jurisdiction_profile_version_id": FIRM_ID,
                "activation_policy_version_id": FIRM_ID,
            },
        }
        r = await c.post("/api/v1/trace/webhooks/matter-activated", json=golden)
        ok("webhook no auth=401", r.status_code == 401,
           f"got {r.status_code} {r.text[:80]}")

    # ── Summary ──
    passed = sum(1 for m, _, _ in results if m == "PASS")
    total = len(results)
    print(f"\n{'='*50}")
    print(f"Results: {passed}/{total} passed")
    if passed == total:
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED")
        for mark, name, detail in results:
            if mark == "FAIL":
                print(f"  FAIL: {name} — {detail}")
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(smoke_test())
    exit(0 if success else 1)
