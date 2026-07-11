"""TRACE Phase 1F — Load Testing Suite.

Targets per Spec Part 9:
  - 100 concurrent fax receipt events: OCR < 5 min
  - 50 concurrent portal sessions: case list < 2s, chronology < 3s, citation < 500ms
  - 20 concurrent demand-ready approvals: gate + update < 1s
  - 10 concurrent PDF exports: < 10s

All synthetic data only — no real PHI, no real Documo API calls.
"""

from locust import HttpUser, between, task


class FaxReceiptUser(HttpUser):
    """Simulate inbound fax webhooks triggering OCR pipeline."""
    wait_time = between(1, 3)

    @task(3)
    def receive_fax(self):
        self.client.post(
            "/api/v1/trace/webhooks/fax-status",
            json={
                "fax_transmission_id": "test-load-tx-001",
                "status": "delivered",
                "pages": 15,
            },
            headers={"X-Trace-Webhook-Secret": "test-load-secret"},
        )

    @task(1)
    def check_fax_status(self):
        self.client.get(
            "/api/v1/trace/webhooks/fax-status?transmission_id=test-load-tx-001",
        )


class AttorneyPortalUser(HttpUser):
    """Simulate attorney portal usage: case list, chronology, source citations."""
    wait_time = between(2, 5)

    @task(5)
    def view_case_list(self):
        self.client.get("/api/v1/trace/cases", name="GET /cases")

    @task(3)
    def view_chronology(self):
        self.client.get(
            "/api/v1/trace/cases/test-load-case/chronology",
            name="GET /cases/{id}/chronology",
        )

    @task(2)
    def view_source_citation(self):
        self.client.get(
            "/api/v1/trace/cases/test-load-case/documents/test-doc/page/1",
            name="GET /cases/{id}/documents/{id}/page/{n}",
        )

    @task(1)
    def list_providers(self):
        self.client.get(
            "/api/v1/trace/cases/test-load-case/providers",
            name="GET /cases/{id}/providers",
        )


class DemandReadyUser(HttpUser):
    """Simulate demand-ready approval flow."""
    wait_time = between(3, 8)

    @task(1)
    def approve_demand_ready(self):
        self.client.post(
            "/api/v1/trace/cases/test-load-case/approve",
            json={"confirmation_text": "Load test approval — attorney reviewed."},
            name="POST /cases/{id}/approve",
        )


class ExportUser(HttpUser):
    """Simulate chronology export (PDF + JSON)."""
    wait_time = between(5, 15)

    @task(2)
    def export_pdf(self):
        self.client.get(
            "/api/v1/trace/cases/test-load-case/export/pdf",
            name="GET /cases/{id}/export/pdf",
        )

    @task(1)
    def export_json(self):
        self.client.get(
            "/api/v1/trace/cases/test-load-case/export/json",
            name="GET /cases/{id}/export/json",
        )
