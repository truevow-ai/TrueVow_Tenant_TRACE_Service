"""FND-002-R2 — re-key utility hardening tests.

DB-free: URL project binding, mixed-key classifier, transaction plan logic,
targeted-mode guards. Guarded persistence lane: exact-match synthetic-row
cleanup semantics against the docker test database.
"""

from __future__ import annotations

import uuid

import pytest

from scripts.phi_rekey_legacy import (
    FIXED_PROJECT_REF,
    REKEY_CONFIRM,
    RekeyRefused,
    _decrypt_with,
    _encrypt_with,
    build_rekey_plan,
    classify_field,
    validate_rekey_url,
)

LEGACY_KEY = b"L" * 32
NEW_KEY = b"N" * 32
OTHER_KEY = b"O" * 32

_DIRECT_OK = f"postgresql://postgres.{FIXED_PROJECT_REF}:pw@db.{FIXED_PROJECT_REF}.supabase.co:5432/postgres"
_DIRECT_WRONG = "postgresql://postgres.wrongref:pw@db.wrongref.supabase.co:5432/postgres"
_POOLER_OK = f"postgresql://postgres.{FIXED_PROJECT_REF}:pw@aws-1-us-east-1.pooler.supabase.com:6543/postgres"
_POOLER_WRONG_PROJECT = "postgresql://postgres.wrongref:pw@aws-1-us-east-1.pooler.supabase.com:6543/postgres"
_POOLER_NO_PROJECT_USER = "postgresql://postgres:pw@aws-1-us-east-1.pooler.supabase.com:6543/postgres"


def _row(fields: dict | None = None, token: uuid.UUID | None = None) -> dict:
    row = {
        "client_token": token or uuid.uuid4(),
        "firm_id": uuid.uuid4(),
        "encrypted_name": None,
        "encrypted_dob": None,
        "encrypted_address": None,
        "encrypted_phone": None,
        "encrypted_email": None,
    }
    if fields:
        row.update(fields)
    return row


# ─────────────────────────────────────────────────────────────────────
# Blocker A: pooler/direct project binding
# ─────────────────────────────────────────────────────────────────────

class TestProjectBinding:
    def test_correct_direct_accepted(self):
        url = validate_rekey_url(_DIRECT_OK)
        assert url.startswith("postgresql://")

    def test_wrong_direct_refused(self):
        with pytest.raises(RekeyRefused):
            validate_rekey_url(_DIRECT_WRONG)

    def test_correct_pooler_with_latch_accepted(self):
        url = validate_rekey_url(_POOLER_OK, pooler_latch=REKEY_CONFIRM)
        assert url.startswith("postgresql://")

    def test_wrong_project_pooler_refused(self):
        with pytest.raises(RekeyRefused):
            validate_rekey_url(_POOLER_WRONG_PROJECT, pooler_latch=REKEY_CONFIRM)

    def test_pooler_without_latch_refused(self):
        with pytest.raises(RekeyRefused):
            validate_rekey_url(_POOLER_OK, pooler_latch="")

    def test_pooler_username_must_identify_project(self):
        with pytest.raises(RekeyRefused):
            validate_rekey_url(_POOLER_NO_PROJECT_USER, pooler_latch=REKEY_CONFIRM)

    def test_non_postgres_refused(self):
        with pytest.raises(RekeyRefused):
            validate_rekey_url("sqlite:///x.db")

    def test_project_ref_not_env_substitutable(self, monkeypatch):
        # Even if an operator exports a different ref, the fixed constant wins.
        monkeypatch.setenv("TRACE_PHI_REKEY_ALLOWED_PROJECT_REF", "evilref")
        with pytest.raises(RekeyRefused):
            validate_rekey_url(_DIRECT_WRONG)


# ─────────────────────────────────────────────────────────────────────
# Mixed-key classifier + transaction plan
# ─────────────────────────────────────────────────────────────────────

class TestMixedKeyPlan:
    def test_classify_field_states(self):
        legacy_blob = _encrypt_with(LEGACY_KEY, "x")
        new_blob = _encrypt_with(NEW_KEY, "x")
        other_blob = _encrypt_with(OTHER_KEY, "x")
        assert classify_field(legacy_blob, LEGACY_KEY, NEW_KEY) == "LEGACY"
        assert classify_field(new_blob, LEGACY_KEY, NEW_KEY) == "ALREADY_NEW"
        assert classify_field(other_blob, LEGACY_KEY, NEW_KEY) == "BLOCKED"

    def test_plan_rekeys_legacy_leaves_already_new(self):
        rows = [
            _row({"encrypted_name": _encrypt_with(LEGACY_KEY, "a")}),
            _row({"encrypted_name": _encrypt_with(NEW_KEY, "b")}),
        ]
        plan = build_rekey_plan(rows, LEGACY_KEY, NEW_KEY)
        assert plan["blocked"] is False
        assert len(plan["rekey_rows"]) == 1
        assert plan["untouched_rows"] == 1
        assert plan["blocked_fields"] == 0

    def test_plan_blocks_on_unknown_ciphertext(self):
        rows = [
            _row({"encrypted_name": _encrypt_with(LEGACY_KEY, "a")}),
            _row({"encrypted_dob": _encrypt_with(OTHER_KEY, "b")}),
        ]
        plan = build_rekey_plan(rows, LEGACY_KEY, NEW_KEY)
        assert plan["blocked"] is True
        assert plan["blocked_fields"] == 1

    def test_plan_counts_all_fields(self):
        rows = [
            _row({
                "encrypted_name": _encrypt_with(LEGACY_KEY, "a"),
                "encrypted_dob": _encrypt_with(NEW_KEY, "b"),
                "encrypted_phone": _encrypt_with(OTHER_KEY, "c"),
            }),
        ]
        plan = build_rekey_plan(rows, LEGACY_KEY, NEW_KEY)
        assert plan["blocked"] is True
        assert plan["blocked_fields"] == 1
        # Row contains a LEGACY field but is excluded from rekey because blocked.
        assert plan["rekey_rows"] == []

    def test_rekey_roundtrip_helpers(self):
        blob = _encrypt_with(LEGACY_KEY, "roundtrip")
        assert _decrypt_with(LEGACY_KEY, blob) == "roundtrip"


# ─────────────────────────────────────────────────────────────────────
# Blocker B: exact-match synthetic cleanup (guarded persistence lane)
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cleanup_absent_token_is_safe_noop():
    from scripts.phi_rekey_legacy import cleanup_synthetic_row
    from app.core.database import phi_engine

    outcome = await cleanup_synthetic_row(
        phi_engine, str(uuid.uuid4()), str(uuid.uuid4())
    )
    assert outcome == "already-absent"


@pytest.mark.asyncio
async def test_cleanup_exact_match_deletes_exactly_one():
    from sqlalchemy import text

    from app.core.database import phi_engine
    from scripts.phi_rekey_legacy import cleanup_synthetic_row

    token = uuid.uuid4()
    firm = uuid.uuid4()
    async with phi_engine.begin() as conn:
        await conn.execute(text(
            "INSERT INTO clients (client_token, firm_id, encrypted_name) "
            "VALUES (CAST(:t AS uuid), CAST(:f AS uuid), 'x')"
        ), {"t": str(token), "f": str(firm)})

    outcome = await cleanup_synthetic_row(phi_engine, str(token), str(firm))
    assert outcome == "deleted"

    async with phi_engine.connect() as conn:
        remaining = (await conn.execute(text(
            "SELECT count(*) FROM clients WHERE client_token = CAST(:t AS uuid)"
        ), {"t": str(token)})).scalar()
    assert remaining == 0


@pytest.mark.asyncio
async def test_cleanup_wrong_firm_refuses_zero_delete():
    from sqlalchemy import text

    from app.core.database import phi_engine
    from scripts.phi_rekey_legacy import cleanup_synthetic_row

    token = uuid.uuid4()
    actual_firm = uuid.uuid4()
    wrong_firm = uuid.uuid4()
    async with phi_engine.begin() as conn:
        await conn.execute(text(
            "INSERT INTO clients (client_token, firm_id, encrypted_name) "
            "VALUES (CAST(:t AS uuid), CAST(:f AS uuid), 'x')"
        ), {"t": str(token), "f": str(actual_firm)})

    with pytest.raises(RekeyRefused):
        await cleanup_synthetic_row(phi_engine, str(token), str(wrong_firm))

    async with phi_engine.connect() as conn:
        remaining = (await conn.execute(text(
            "SELECT count(*) FROM clients WHERE client_token = CAST(:t AS uuid)"
        ), {"t": str(token)})).scalar()
    assert remaining == 1  # nothing deleted
