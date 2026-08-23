"""FND-003-R1 — canonical internal tenant-context helper tests.

Seam-only ticket: proves parameterized GUC setting, transaction-local
reset across pooled reuse, and fail-closed construction. No callers are
migrated in this ticket.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from app.core.database import (
    BlockedInternalTenantContext,
    async_session_maker,
    engine,
    internal_tenant_session,
)

TEST_PG_URL = os.environ.get("TRACE_TEST_PG_URL", "")
DESTRUCTIVE_CONFIRMED = (
    os.environ.get("TRACE_TEST_ALLOW_DESTRUCTIVE", "") == "TRUEVOW_NONPROD_TEST_DB"
)
GUARDS_OK = bool(TEST_PG_URL) and DESTRUCTIVE_CONFIRMED

pytestmark = pytest.mark.skipif(
    not GUARDS_OK,
    reason="guarded PostgreSQL lane (TRACE_TEST_PG_URL + destructive token) required",
)

TENANT_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


@pytest.mark.asyncio
async def test_fails_closed_without_tenant():
    with pytest.raises(BlockedInternalTenantContext):
        async with internal_tenant_session(tenant_id=""):
            pass  # pragma: no cover - never yields


@pytest.mark.asyncio
async def test_gucs_set_and_parameterized(_setup_db):
    # A quote-bearing value must round-trip as a bound parameter, proving
    # no string interpolation happens on the seam.
    hostile_tenant = "x'; SELECT 1; --"
    async with internal_tenant_session(tenant_id=hostile_tenant) as session:
        stored = (
            await session.execute(
                text("SELECT current_setting('app.current_tenant_id', true)")
            )
        ).scalar_one()
        assert stored == hostile_tenant


@pytest.mark.asyncio
async def test_context_is_transaction_local_no_pool_leak(_setup_db):
    async with internal_tenant_session(tenant_id=TENANT_A, user_id="u-1", role="attorney") as session:
        inside = (
            await session.execute(
                text("SELECT current_setting('app.current_tenant_id', true)")
            )
        ).scalar_one()
        assert inside == TENANT_A

    # A fresh connection from the pool must observe reset defaults.
    async with async_session_maker() as fresh:
        leaked = (
            await fresh.execute(
                text("SELECT current_setting('app.current_tenant_id', true)")
            )
        ).scalar_one()
    assert leaked in ("", None)


@pytest.mark.asyncio
async def test_engine_level_defaults_untouched(_setup_db):
    # The helper must not mutate engine-level server settings.
    async with engine.connect() as conn:
        value = (
            await conn.execute(
                text("SELECT current_setting('app.current_tenant_id', true)")
            )
        ).scalar_one()
    assert value in ("", None)
