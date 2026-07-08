"""Phase 1A acceptance: audit-log completeness + append-only intent."""

from __future__ import annotations

import pytest

from tests.conftest import auth_header, fetch_audit_rows


@pytest.mark.asyncio
async def test_every_authenticated_api_call_is_logged(client):
    before = len(await fetch_audit_rows())
    await client.get("/api/v1/trace/cases", headers=auth_header())
    after = await fetch_audit_rows()
    assert len(after) == before + 1
    entry = after[-1]
    assert entry.actor_id is not None
    assert entry.resource_type is not None
    assert entry.resource_id is not None
    assert entry.action is not None
    assert entry.timestamp is not None


@pytest.mark.asyncio
async def test_unauthenticated_call_creates_no_actor_audit(client):
    before = len(await fetch_audit_rows())
    resp = await client.get("/api/v1/trace/cases")
    assert resp.status_code == 401
    after = await fetch_audit_rows()
    # No authenticated actor => no audited action row for this request.
    assert len(after) == before
