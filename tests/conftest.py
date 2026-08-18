"""Test configuration.

TRACE persists only to Supabase/PostgreSQL (INV-TRACE-001). There is no
SQLite test path.

- Pure unit tests may run without any database: the app imports with a
  placeholder Postgres URL (engines are lazy — no connection is attempted
  unless a test touches the database).
- Persistence/integration tests require ``TRACE_TEST_PG_URL`` (a designated
  NON-PRODUCTION Postgres). The schema is created with Alembic
  (``alembic upgrade head``), never ``metadata.create_all()``, and all tables
  are truncated between tests.
"""

from __future__ import annotations

import datetime
import os
import subprocess
import sys
import uuid

# --- Environment must be set before importing app modules ---
os.environ["ENVIRONMENT"] = "test"
os.environ["AUTH_MODE"] = "local"
os.environ["LOCAL_JWT_SECRET"] = "test-secret-at-least-32-bytes-long-000"

TEST_PG_URL = os.environ.get("TRACE_TEST_PG_URL") or os.environ.get("TRACE_DATABASE_URL") or ""
_PLACEHOLDER_URL = "postgresql+asyncpg://unit:unit@127.0.0.1:1/unit"  # never connectable

if TEST_PG_URL:
    os.environ["TRACE_DATABASE_URL"] = TEST_PG_URL
    os.environ["TRACE_PHI_DATABASE_URL"] = os.environ.get("TRACE_PHI_DATABASE_URL") or TEST_PG_URL
else:
    os.environ["TRACE_DATABASE_URL"] = _PLACEHOLDER_URL
    os.environ["TRACE_PHI_DATABASE_URL"] = _PLACEHOLDER_URL
os.environ.pop("DATABASE_URL", None)
os.environ.pop("PHI_DATABASE_URL", None)

import jwt  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import async_session_maker, engine, phi_engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.case import Case  # noqa: E402

DB_AVAILABLE = bool(TEST_PG_URL)


@pytest.fixture(scope="session", autouse=True)
def _migrate_schema():
    """Bring the designated non-production Postgres to the expected revision.

    Uses Alembic — acceptance schema is never created from SQLAlchemy
    metadata (FND001-INV-07). Skips silently only when no test database is
    configured (pure unit runs); any DB-touching test then fails loudly.
    """
    if not DB_AVAILABLE:
        return
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.exit(
            f"alembic upgrade head failed against the designated test database.\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )


async def _truncate_schema_tables() -> None:
    """Truncate every table in the trace and trace_phi schemas (test DB only)."""
    async with engine.begin() as conn:
        await conn.execute(text(
            "DO $$ DECLARE t record; BEGIN "
            "FOR t IN SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'trace' AND tablename <> 'alembic_version' LOOP "
            "EXECUTE 'TRUNCATE TABLE trace.' || quote_ident(t.tablename) || ' CASCADE'; "
            "END LOOP; END $$;"
        ))
    async with phi_engine.begin() as conn:
        await conn.execute(text(
            "DO $$ DECLARE t record; BEGIN "
            "FOR t IN SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'trace_phi' LOOP "
            "EXECUTE 'TRUNCATE TABLE trace_phi.' || quote_ident(t.tablename) || ' CASCADE'; "
            "END LOOP; END $$;"
        ))


@pytest_asyncio.fixture(autouse=True)
async def _setup_db():
    if DB_AVAILABLE:
        # Drop pooled asyncpg connections so each test creates connections in
        # its own event loop (module-level engines + per-test loops are safe
        # this way regardless of pytest-asyncio loop scoping).
        await engine.dispose()
        await phi_engine.dispose()
        await _truncate_schema_tables()
    yield
    if DB_AVAILABLE:
        await engine.dispose()
        await phi_engine.dispose()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


def make_token(firm_id: str | None = None, user_id: str | None = None, role: str = "attorney") -> str:
    payload = {
        "sub": user_id or str(uuid.uuid4()),
        "firm_id": firm_id or str(uuid.uuid4()),
        "role": role,
        "mfa": True,
    }
    return jwt.encode(payload, settings.local_jwt_secret, algorithm="HS256")


def auth_header(firm_id: str | None = None, user_id: str | None = None) -> dict:
    return {"Authorization": f"Bearer {make_token(firm_id=firm_id, user_id=user_id)}"}


async def seed_case(firm_id: str, *, signing_complete: bool = False) -> str:
    async with async_session_maker() as session:
        case = Case(
            client_token=uuid.uuid4(),
            firm_id=uuid.UUID(firm_id),
            intake_record_id=uuid.uuid4(),
            incident_date=datetime.date(2026, 1, 15),
            jurisdiction_state="CA",
        )
        if signing_complete:
            case.case_stage = "INITIALIZATION"
            case.hipaa_auth_status = "SIGNED"
            case.signing_completed_at = datetime.datetime(2026, 1, 15, tzinfo=datetime.timezone.utc)
        session.add(case)
        await session.commit()
        return str(case.case_id)


async def fetch_audit_rows() -> list[AuditLog]:
    from sqlalchemy import select

    async with async_session_maker() as session:
        result = await session.execute(select(AuditLog))
        return list(result.scalars().all())
