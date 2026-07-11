"""Phase 1E verification: export disclaimer, export gate, liens scoping."""

from __future__ import annotations

import uuid

import pytest

from tests.conftest import auth_header


def _case_payload(**over) -> dict:
    base = {
        "intake_record_id": str(uuid.uuid4()),
        "client_data": {
            "name": "Verify Phase1E",
            "dob": "1985-06-15",
            "address": "123 Test St",
            "phone": "+13105550000",
        },
        "incident_date": "2025-03-01",
        "jurisdiction_state": "CA",
        "provider_hints": [],
    }
    base.update(over)
    return base


def test_disclaimer_is_on_every_export_page():
    """PDF export must include the disclaimer on every page, not just the cover."""
    from io import BytesIO
    from app.services.export import EXPORT_DISCLAIMER, ChronologyExporter

    exporter = ChronologyExporter()
    entries = [
        {"event_date": "2025-01-01", "event_type": "VISIT",
         "clinical_description": "Test entry A", "source_document_id": "doc-1", "source_page_number": 1},
    ] * 30  # enough to span multiple pages

    pdf_bytes = exporter.export_pdf(
        matter_reference="Test Matter",
        incident_date="2024-01-01",
        sol_estimate="2026-01-01",
        entries=entries,
    )
    pdf_bytes.seek(0)

    from pypdf import PdfReader
    reader = PdfReader(pdf_bytes)

    assert len(reader.pages) > 1, f"PDF must have multiple pages. Got {len(reader.pages)}."
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        assert "ATTORNEY WORK PRODUCT" in text.upper() or "attorney work product" in text.lower(), (
            f"Disclaimer missing from page {page_num + 1}."
        )


@pytest.mark.asyncio
async def test_export_blocked_before_demand_ready(client):
    """Export must return 403 if the case is not demand-ready."""
    firm = str(uuid.uuid4())
    resp = await client.post(
        "/api/v1/trace/cases",
        json=_case_payload(),
        headers=auth_header(firm_id=firm),
    )
    assert resp.status_code == 201
    case_id = resp.json()["case_id"]

    export_resp = await client.get(
        f"/api/v1/trace/cases/{case_id}/export/pdf",
        headers=auth_header(firm_id=firm),
    )
    assert export_resp.status_code in (400, 403, 404), (
        f"Export must be blocked before demand-ready. Got {export_resp.status_code}."
    )


@pytest.mark.asyncio
async def test_liens_scoped_to_firm(client):
    """Firm B must not see Firm A's liens."""
    firm_a = str(uuid.uuid4())
    firm_b = str(uuid.uuid4())

    resp = await client.post(
        "/api/v1/trace/cases",
        json=_case_payload(),
        headers=auth_header(firm_id=firm_a),
    )
    assert resp.status_code == 201
    case_id = resp.json()["case_id"]

    # Firm A creates a lien
    lien_resp = await client.post(
        f"/api/v1/trace/cases/{case_id}/liens",
        json={"lien_type": "MEDICARE", "lienholder": "CMS", "claimed_amount": 5000.0},
        headers=auth_header(firm_id=firm_a),
    )
    assert lien_resp.status_code == 201
    lien_id = lien_resp.json()["lien_id"]

    # Firm B cannot see Firm A's lien
    firm_b_resp = await client.get(
        f"/api/v1/trace/cases/{case_id}/liens/{lien_id}",
        headers=auth_header(firm_id=firm_b),
    )
    assert firm_b_resp.status_code in (403, 404), (
        f"Firm B must not access Firm A's lien. Got {firm_b_resp.status_code}."
    )
