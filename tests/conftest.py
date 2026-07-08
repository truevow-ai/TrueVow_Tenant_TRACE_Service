"""Test configuration.

Runs the whole suite against in-memory SQLite (the platform's ``conftest``
pattern) so Phase 1A acceptance criteria are verifiable without live cloud.
Environment is set BEFORE importing the app so settings pick it up.
"""

from __future__ import annotations

import datetime
import os
import uuid

# --- Environment must be set before importing app modules ---
os.environ["ENVIRONMENT"] = "development"
os.environ["AUTH_MODE"] = "local"
os.environ["LOCAL_JWT_SECRET"] = "test-secret-at-least-32-bytes-long-000"
os.environ.pop("TRACE_DATABASE_URL", None)
os.environ.pop("DATABASE_URL", None)

import jwt  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import async_session_maker, engine, phi_engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.case import Case  # noqa: E402
from app.models.client import PHIBase  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def _setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with phi_engine.begin() as conn:
        await conn.run_sync(PHIBase.metadata.create_all)
    yield
    async with phi_engine.begin() as conn:
        await conn.run_sync(PHIBase.metadata.drop_all)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


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


async def seed_case(firm_id: str) -> str:
    async with async_session_maker() as session:
        case = Case(
            client_token=uuid.uuid4(),
            firm_id=uuid.UUID(firm_id),
            intake_record_id=uuid.uuid4(),
            incident_date=datetime.date(2026, 1, 15),
            jurisdiction_state="CA",
        )
        session.add(case)
        await session.commit()
        return str(case.case_id)


async def fetch_audit_rows() -> list[AuditLog]:
    from sqlalchemy import select

    async with async_session_maker() as session:
        result = await session.execute(select(AuditLog))
        return list(result.scalars().all())
