"""FND-001A — PostgreSQL baseline reconciliation tests.

Covers the two drift roots:

    DRIFT-01  audit_log.ip_address INET: IPv4 / IPv6 persistence and
              invalid-IP -> NULL normalization (targeted DB tests plus a
              DB-free normalization unit test).
    DRIFT-02  providers.extraction_confidence VARCHAR(32): the longest
              application-contract values must persist.

DB-touching tests require the guarded persistence lane (TRACE_TEST_PG_URL +
TRACE_TEST_ALLOW_DESTRUCTIVE) with migration 0019_baseline_reconcile applied.
"""

from __future__ import annotations

import datetime
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.audit import normalize_ip, write_audit
from app.core.database import async_session_maker
from app.main import app
from app.models.audit import AuditLog
from app.models.case import Case
from app.models.provider import Provider
from tests.conftest import auth_header


# ─────────────────────────────────────────────────────────────────────
# DB-free unit tests (normalization logic)
# ─────────────────────────────────────────────────────────────────────

class TestNormalizeIp:
    def test_ipv4_normalized(self):
        assert normalize_ip("127.0.0.1") == "127.0.0.1"

    def test_ipv6_normalized(self):
        assert normalize_ip("2001:db8::1") == "2001:db8::1"

    def test_invalid_ip_becomes_none(self):
        assert normalize_ip("not-an-ip") is None

    def test_missing_ip_becomes_none(self):
        assert normalize_ip(None) is None
        assert normalize_ip("") is None


# ─────────────────────────────────────────────────────────────────────
# DRIFT-01: audit INET persistence (guarded persistence lane)
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_ipv4_persisted():
    firm = str(uuid.uuid4())
    async with async_session_maker() as session:
        case = Case(
            client_token=uuid.uuid4(),
            firm_id=uuid.UUID(firm),
            intake_record_id=uuid.uuid4(),
            incident_date=datetime.date(2026, 1, 15),
            jurisdiction_state="CA",
        )
        session.add(case)
        await session.commit()
        case_id = str(case.case_id)

    transport = ASGITransport(app=app, client=("127.0.0.1", 123))
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        resp = await ac.get(f"/api/v1/trace/cases/{case_id}", headers=auth_header(firm_id=firm))
    assert resp.status_code == 200

    async with async_session_maker() as session:
        row = (await session.execute(
            select(AuditLog).order_by(AuditLog.timestamp.desc())
        )).scalars().first()
    assert row is not None
    assert str(row.ip_address) == "127.0.0.1"


@pytest.mark.asyncio
async def test_audit_ipv6_persisted():
    firm = str(uuid.uuid4())
    async with async_session_maker() as session:
        case = Case(
            client_token=uuid.uuid4(),
            firm_id=uuid.UUID(firm),
            intake_record_id=uuid.uuid4(),
            incident_date=datetime.date(2026, 1, 15),
            jurisdiction_state="CA",
        )
        session.add(case)
        await session.commit()
        case_id = str(case.case_id)

    transport = ASGITransport(app=app, client=("::1", 123))
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        resp = await ac.get(f"/api/v1/trace/cases/{case_id}", headers=auth_header(firm_id=firm))
    assert resp.status_code == 200

    async with async_session_maker() as session:
        row = (await session.execute(
            select(AuditLog).order_by(AuditLog.timestamp.desc())
        )).scalars().first()
    assert row is not None
    assert str(row.ip_address) == "::1"


@pytest.mark.asyncio
async def test_audit_invalid_ip_writes_null():
    await write_audit(
        actor_id=uuid.uuid4(),
        actor_type="SYSTEM",
        action="fnd001a.invalid_ip_test",
        resource_type="test",
        ip_address="not-an-ip",
    )
    async with async_session_maker() as session:
        row = (await session.execute(
            select(AuditLog).where(AuditLog.action == "fnd001a.invalid_ip_test")
        )).scalar_one()
    assert row.ip_address is None


# ─────────────────────────────────────────────────────────────────────
# DRIFT-02: provider extraction_confidence width (VARCHAR(32))
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_provider_confidence_longest_values_persist():
    async with async_session_maker() as session:
        case = Case(
            client_token=uuid.uuid4(),
            firm_id=uuid.uuid4(),
            intake_record_id=uuid.uuid4(),
            incident_date=datetime.date(2026, 1, 15),
            jurisdiction_state="CA",
        )
        session.add(case)
        await session.flush()
        session.add(Provider(
            case_id=case.case_id,
            provider_name="High Confidence Clinic",
            extraction_confidence="HIGH_CONFIDENCE",
        ))
        session.add(Provider(
            case_id=case.case_id,
            provider_name="Needs Confirmation Clinic",
            extraction_confidence="NEEDS_CLIENT_CONFIRMATION",
        ))
        await session.commit()

    async with async_session_maker() as session:
        rows = (await session.execute(
            select(Provider.extraction_confidence).where(
                Provider.extraction_confidence.isnot(None)
            )
        )).scalars().all()
    assert "HIGH_CONFIDENCE" in rows
    assert "NEEDS_CLIENT_CONFIRMATION" in rows
