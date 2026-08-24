"""FND-003-R1 — runtime role contract tests (guarded PostgreSQL lane).

Proves the versioned 0023 role/grant contract end-to-end: catalog facts,
same-tenant CRUD, cross-tenant denial, audit INSERT-only, PHI-schema
absence, no schema CREATE, and deterministic downgrade/upgrade.

Pattern mirrors test_fnd003_rls.py: the harness superuser is used ONLY for
setup/seeding; every behavioral assertion executes via ``SET LOCAL ROLE``
so the effective privileges are exactly those of the runtime login.
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

TEST_PG_URL = os.environ.get("TRACE_TEST_PG_URL", "")
DESTRUCTIVE_CONFIRMED = (
    os.environ.get("TRACE_TEST_ALLOW_DESTRUCTIVE", "") == "TRUEVOW_NONPROD_TEST_DB"
)
GUARDS_OK = bool(TEST_PG_URL) and DESTRUCTIVE_CONFIRMED

pytestmark = pytest.mark.skipif(
    not GUARDS_OK,
    reason="guarded PostgreSQL lane (TRACE_TEST_PG_URL + destructive token) required",
)

ROLE = "trace_runtime_login"
TENANT_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
TENANT_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

from app.core.database import async_session_maker, engine  # noqa: E402


async def _as_role(session, firm: str | None = None):
    """Begin a transaction executing as the runtime login (+ optional GUC)."""
    await session.execute(text(f"SET LOCAL ROLE {ROLE}"))
    if firm is not None:
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :t, true)"),
            {"t": firm},
        )


async def _seed(firm: str) -> uuid.UUID:
    case_id = uuid.uuid4()
    async with engine.begin() as conn:
        await conn.execute(text(
            "INSERT INTO trace.cases (case_id, client_token, firm_id, "
            "intake_record_id, incident_date, jurisdiction_state) VALUES "
            "(CAST(:c AS uuid), gen_random_uuid(), CAST(:f AS uuid), "
            "gen_random_uuid(), '2026-01-15', 'CA')"
        ), {"c": str(case_id), "f": firm})
    return case_id


# ── Catalog facts ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_runtime_role_catalog_facts():
    async with engine.connect() as conn:
        row = (
            await conn.execute(text(
                "SELECT rolcanlogin, rolsuper, rolinherit, rolcreatedb, "
                "rolcreaterole, rolbypassrls FROM pg_roles WHERE rolname = :r"
            ), {"r": ROLE})
        ).one()
    assert row.rolcanlogin is True
    assert row.rolsuper is False
    assert row.rolinherit is False
    assert row.rolcreatedb is False
    assert row.rolcreaterole is False
    assert row.rolbypassrls is False


@pytest.mark.asyncio
async def test_no_phi_schema_usage():
    async with engine.connect() as conn:
        usage = (
            await conn.execute(text(
                "SELECT has_schema_privilege(:r, 'trace_phi', 'USAGE')"
            ), {"r": ROLE})
        ).scalar_one()
        create = (
            await conn.execute(text(
                "SELECT has_schema_privilege(:r, 'trace', 'CREATE')"
            ), {"r": ROLE})
        ).scalar_one()
    assert usage is False
    assert create is False


@pytest.mark.asyncio
async def test_runtime_owns_nothing():
    owned = 0
    async with engine.connect() as conn:
        owned = (
            await conn.execute(text(
                "SELECT count(*) FROM pg_class c JOIN pg_roles r ON r.oid = c.relowner "
                "WHERE r.rolname = :r"
            ), {"r": ROLE})
        ).scalar_one()
    assert owned == 0


@pytest.mark.asyncio
async def test_runtime_can_read_alembic_version(_setup_db):
    async with async_session_maker() as session:
        await _as_role(session)
        rows = (
            await session.execute(text("SELECT version_num FROM trace.alembic_version"))
        ).fetchall()
    assert len(rows) >= 1


@pytest.mark.asyncio
async def test_no_blanket_future_table_dml(_setup_db):
    """A table created AFTER 0023 must carry zero runtime privileges.

    Proves the least-privilege rule: no default-ACL contract exists, so
    future migrations must grant the runtime role deliberately.
    """
    async with engine.begin() as conn:
        await conn.execute(text(
            "CREATE TABLE trace.probe_future_acl (id int PRIMARY KEY)"
        ))
    try:
        async with engine.connect() as conn:
            for action in ("SELECT", "INSERT", "UPDATE", "DELETE"):
                granted = (
                    await conn.execute(text(
                        "SELECT has_table_privilege(:r, 'trace.probe_future_acl', :a)"
                    ), {"r": ROLE, "a": action})
                ).scalar_one()
                assert granted is False, action
    finally:
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS trace.probe_future_acl"))


# ── Behavior under RLS as the runtime login ──────────────────────────


@pytest.mark.asyncio
async def test_same_tenant_crud_ok_cross_tenant_invisible(_setup_db):
    own_case = await _seed(TENANT_A)
    other_case = await _seed(TENANT_B)

    async with async_session_maker() as session:
        await _as_role(session, TENANT_A)

        # SELECT: only own tenant visible.
        seen = (
            await session.execute(text("SELECT count(*) FROM trace.cases"))
        ).scalar_one()
        assert seen == 1

        # UPDATE within tenant succeeds.
        await session.execute(text(
            "UPDATE trace.cases SET jurisdiction_state = 'NV' "
            "WHERE case_id = CAST(:c AS uuid)"
        ), {"c": str(own_case)})

        # INSERT within tenant succeeds.
        await session.execute(text(
            "INSERT INTO trace.firm_users (clerk_user_id, firm_id) "
            "VALUES (:s, CAST(:f AS uuid))"
        ), {"s": f"sub-{uuid.uuid4().hex[:8]}", "f": TENANT_A})

        await session.rollback()

    # Cross-tenant UPDATE from tenant A context touches zero rows.
    async with async_session_maker() as session:
        await _as_role(session, TENANT_A)
        result = await session.execute(text(
            "UPDATE trace.cases SET jurisdiction_state = 'XX' "
            "WHERE case_id = CAST(:c AS uuid)"
        ), {"c": str(other_case)})
        assert result.rowcount == 0
        await session.rollback()


@pytest.mark.asyncio
async def test_audit_log_insert_only(_setup_db):
    async with async_session_maker() as session:
        await _as_role(session, TENANT_A)

        await session.execute(text(
            "INSERT INTO trace.audit_log (actor_type, action, resource_type, firm_id) "
            "VALUES ('SYSTEM', 'PROBE insert-only', 'probe', CAST(:f AS uuid))"
        ), {"f": TENANT_A})

        for statement in (
            "SELECT count(*) FROM trace.audit_log",
            "UPDATE trace.audit_log SET action = 'x'",
            "DELETE FROM trace.audit_log",
        ):
            with pytest.raises(ProgrammingError, match="permission denied"):
                await session.execute(text(statement))

        await session.rollback()


@pytest.mark.asyncio
async def test_missing_context_fails_closed(_setup_db):
    await _seed(TENANT_A)
    async with async_session_maker() as session:
        await _as_role(session, None)  # no tenant GUC set
        seen = (
            await session.execute(text("SELECT count(*) FROM trace.cases"))
        ).scalar_one()
        assert seen == 0
        await session.rollback()


# ── Determinism: downgrade removes, upgrade reproduces ───────────────


@pytest.mark.skipif(not GUARDS_OK, reason="guarded lane required")
def test_downgrade_upgrade_deterministic():
    env = {**os.environ}
    env["TRACE_DATABASE_URL"] = TEST_PG_URL
    # Test lane is a MIGRATION_TEST_ADMIN usage of the privileged URL (T02).
    env["TRACE_MIGRATION_DATABASE_URL"] = TEST_PG_URL
    env.pop("DATABASE_URL", None)

    def _alembic(*args: str) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            capture_output=True, text=True, env=env,
        )
        assert result.returncode == 0, result.stderr or result.stdout

    import asyncio

    from sqlalchemy import create_async_engine  # local to avoid app import order

    probe_url = TEST_PG_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

    async def _role_exists() -> bool:
        eng = create_async_engine(probe_url)
        try:
            async with eng.connect() as conn:
                return (
                    await conn.execute(text(
                        "SELECT EXISTS (SELECT FROM pg_roles WHERE rolname = :r)"
                    ), {"r": ROLE})
                ).scalar_one()
        finally:
            await eng.dispose()

    _alembic("downgrade", "0022_fnd003_rls_reconciliation")
    assert asyncio.run(_role_exists()) is False
    _alembic("upgrade", "head")
    assert asyncio.run(_role_exists()) is True
