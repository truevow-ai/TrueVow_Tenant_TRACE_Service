"""Phase 1A acceptance: health + authentication gate."""

from __future__ import annotations

import pytest

from tests.conftest import auth_header, fetch_audit_rows


@pytest.mark.asyncio
async def test_health_is_public_and_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["service"] == "trace"


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401(client):
    resp = await client.get("/api/v1/trace/cases")
    assert resp.status_code == 401
    # Plain-English, no stack trace.
    assert "message" in resp.json()


@pytest.mark.asyncio
async def test_bad_token_returns_401(client):
    resp = await client.get(
        "/api/v1/trace/cases", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_call_succeeds_and_is_audited(client):
    resp = await client.get("/api/v1/trace/cases", headers=auth_header())
    assert resp.status_code == 200
    assert "X-Correlation-ID" in resp.headers

    rows = await fetch_audit_rows()
    assert len(rows) >= 1
    entry = rows[-1]
    # Acceptance: actor_id, timestamp, action, resource_type all populated.
    assert entry.actor_id is not None
    assert entry.timestamp is not None
    assert entry.action == "GET /api/v1/trace/cases"
    assert entry.resource_type == "cases"
    assert entry.firm_id is not None
