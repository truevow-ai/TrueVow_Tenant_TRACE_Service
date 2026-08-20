"""FND-002-R2/R3 — re-key utility hardening tests.

DB-free: exact project-identity binding, mixed-key classifier, field-level
transaction plan. Guarded persistence lane: field-level re-key execution
(byte-for-byte preservation of ALREADY_NEW fields) and exact-match
synthetic-row cleanup semantics.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from scripts.phi_rekey_legacy import (
    EXACT_DIRECT_HOST,
    EXACT_POOLER_USERNAME,
    FIXED_PROJECT_REF,
    REKEY_CONFIRM,
    RekeyRefused,
    _decrypt_with,
    _encrypt_with,
    _rekey_rows_tx,
    build_rekey_plan,
    classify_field,
    validate_rekey_url,
)

LEGACY_KEY = b"L" * 32
NEW_KEY = b"N" * 32
OTHER_KEY = b"O" * 32

_DIRECT_OK = f"postgresql://{EXACT_POOLER_USERNAME}:pw@{EXACT_DIRECT_HOST}:5432/postgres"
_DIRECT_WRONG = "postgresql://postgres.wrongref:pw@db.wrongref.supabase.co:5432/postgres"
_DIRECT_SUPERSET = f"postgresql://{EXACT_POOLER_USERNAME}:pw@db.{FIXED_PROJECT_REF}evil.supabase.co:5432/postgres"
_POOLER_OK = f"postgresql://{EXACT_POOLER_USERNAME}:pw@aws-1-us-east-1.pooler.supabase.com:6543/postgres"
_POOLER_WRONG_PROJECT = "postgresql://postgres.wrongref:pw@aws-1-us-east-1.pooler.supabase.com:6543/postgres"
_POOLER_SUPERSET_USER1 = f"postgresql://evil{EXACT_POOLER_USERNAME}:pw@aws-1-us-east-1.pooler.supabase.com:6543/postgres"
_POOLER_SUPERSET_USER2 = f"postgresql://{EXACT_POOLER_USERNAME}evil:pw@aws-1-us-east-1.pooler.supabase.com:6543/postgres"
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
# Exact project-identity binding (R3 tightening)
# ─────────────────────────────────────────────────────────────────────

class TestProjectBinding:
    def test_correct_direct_accepted(self):
        assert validate_rekey_url(_DIRECT_OK).startswith("postgresql://")

    def test_wrong_direct_refused(self):
        with pytest.raises(RekeyRefused):
            validate_rekey_url(_DIRECT_WRONG)

    def test_direct_superset_host_refused(self):
        with pytest.raises(RekeyRefused):
            validate_rekey_url(_DIRECT_SUPERSET)

    def test_correct_pooler_with_latch_accepted(self):
        assert validate_rekey_url(_POOLER_OK, pooler_latch=REKEY_CONFIRM)

    def test_wrong_project_pooler_refused(self):
        with pytest.raises(RekeyRefused):
            validate_rekey_url(_POOLER_WRONG_PROJECT, pooler_latch=REKEY_CONFIRM)

    def test_pooler_without_latch_refused(self):
        with pytest.raises(RekeyRefused):
            validate_rekey_url(_POOLER_OK, pooler_latch="")

    def test_pooler_superset_username_refused(self):
        with pytest.raises(RekeyRefused):
            validate_rekey_url(_POOLER_SUPERSET_USER1, pooler_latch=REKEY_CONFIRM)
        with pytest.raises(RekeyRefused):
            validate_rekey_url(_POOLER_SUPERSET_USER2, pooler_latch=REKEY_CONFIRM)

    def test_pooler_username_must_identify_project(self):
        with pytest.raises(RekeyRefused):
            validate_rekey_url(_POOLER_NO_PROJECT_USER, pooler_latch=REKEY_CONFIRM)

    def test_non_postgres_refused(self):
        with pytest.raises(RekeyRefused):
            validate_rekey_url("sqlite:///x.db")

    def test_project_ref_not_env_substitutable(self, monkeypatch):
        monkeypatch.setenv("TRACE_PHI_REKEY_ALLOWED_PROJECT_REF", "evilref")
        with pytest.raises(RekeyRefused):
            validate_rekey_url(_DIRECT_WRONG)


# ─────────────────────────────────────────────────────────────────────
# Mixed-key classifier + field-level transaction plan
# ─────────────────────────────────────────────────────────────────────

class TestMixedKeyPlan:
    def test_classify_field_states(self):
        assert classify_field(_encrypt_with(LEGACY_KEY, "x"), LEGACY_KEY, NEW_KEY) == "LEGACY"
        assert classify_field(_encrypt_with(NEW_KEY, "x"), LEGACY_KEY, NEW_KEY) == "ALREADY_NEW"
        assert classify_field(_encrypt_with(OTHER_KEY, "x"), LEGACY_KEY, NEW_KEY) == "BLOCKED"

    def test_plan_rekeys_legacy_leaves_already_new_rows(self):
        rows = [
            _row({"encrypted_name": _encrypt_with(LEGACY_KEY, "a")}),
            _row({"encrypted_name": _encrypt_with(NEW_KEY, "b")}),
        ]
        plan = build_rekey_plan(rows, LEGACY_KEY, NEW_KEY)
        assert plan["blocked"] is False
        assert len(plan["rekey_entries"]) == 1
        assert plan["rekey_entries"][0]["legacy_fields"] == ["encrypted_name"]
        assert plan["rekey_entries"][0]["already_new_fields"] == []
        assert plan["untouched_rows"] == 1

    def test_plan_mixed_legacy_and_already_new_same_row(self):
        """R3-required: one row, LEGACY + ALREADY_NEW, no BLOCKED."""
        rows = [_row({
            "encrypted_name": _encrypt_with(LEGACY_KEY, "a"),
            "encrypted_dob": _encrypt_with(NEW_KEY, "b"),
        })]
        plan = build_rekey_plan(rows, LEGACY_KEY, NEW_KEY)
        assert plan["blocked"] is False
        assert len(plan["rekey_entries"]) == 1
        entry = plan["rekey_entries"][0]
        assert entry["legacy_fields"] == ["encrypted_name"]
        assert entry["already_new_fields"] == ["encrypted_dob"]

    def test_plan_blocks_on_unknown_ciphertext(self):
        rows = [
            _row({"encrypted_name": _encrypt_with(LEGACY_KEY, "a")}),
            _row({"encrypted_dob": _encrypt_with(OTHER_KEY, "b")}),
        ]
        plan = build_rekey_plan(rows, LEGACY_KEY, NEW_KEY)
        assert plan["blocked"] is True
        assert plan["blocked_fields"] == 1

    def test_plan_legacy_already_new_and_blocked_zero_writes(self):
        rows = [_row({
            "encrypted_name": _encrypt_with(LEGACY_KEY, "a"),
            "encrypted_dob": _encrypt_with(NEW_KEY, "b"),
            "encrypted_phone": _encrypt_with(OTHER_KEY, "c"),
        })]
        plan = build_rekey_plan(rows, LEGACY_KEY, NEW_KEY)
        assert plan["blocked"] is True
        assert plan["blocked_fields"] == 1
        assert plan["rekey_entries"] == []  # zero re-key writes

    def test_rekey_roundtrip_helpers(self):
        blob = _encrypt_with(LEGACY_KEY, "roundtrip")
        assert _decrypt_with(LEGACY_KEY, blob) == "roundtrip"


# ─────────────────────────────────────────────────────────────────────
# Field-level execution (guarded persistence lane)
# ─────────────────────────────────────────────────────────────────────

async def _insert_row(token: uuid.UUID, firm: uuid.UUID, fields: dict) -> None:
    from app.core.database import phi_engine

    columns = ["client_token", "firm_id", *fields.keys()]
    placeholders = ", ".join(f":{c}" for c in columns)
    params = {"client_token": token, "firm_id": firm, **fields}
    async with phi_engine.begin() as conn:
        await conn.execute(
            text(f"INSERT INTO clients ({', '.join(columns)}) VALUES ({placeholders})"),
            params,
        )


async def _read_row(token: uuid.UUID) -> dict:
    from app.core.database import phi_engine

    async with phi_engine.connect() as conn:
        row = (await conn.execute(text(
            "SELECT encrypted_name, encrypted_dob, encrypted_address, "
            "encrypted_phone, encrypted_email FROM clients "
            "WHERE client_token = CAST(:t AS uuid)"
        ), {"t": str(token)})).mappings().first()
    return dict(row) if row else {}


@pytest.mark.asyncio
async def test_mixed_row_field_level_updates_and_preservation():
    from app.core.database import phi_engine

    token = uuid.uuid4()
    legacy_blob = _encrypt_with(LEGACY_KEY, "legacy-name")
    new_blob = _encrypt_with(NEW_KEY, "new-dob")
    await _insert_row(token, uuid.uuid4(), {
        "encrypted_name": legacy_blob,
        "encrypted_dob": new_blob,
    })

    row = _row({
        "client_token": token,
        "encrypted_name": legacy_blob,
        "encrypted_dob": new_blob,
    })
    plan = build_rekey_plan([row], LEGACY_KEY, NEW_KEY)
    assert plan["blocked"] is False

    async with phi_engine.begin() as conn:
        await _rekey_rows_tx(conn, plan["rekey_entries"], LEGACY_KEY, NEW_KEY)

    after = await _read_row(token)
    # LEGACY field rewritten under the new key.
    assert after["encrypted_name"] != legacy_blob
    assert _decrypt_with(NEW_KEY, after["encrypted_name"]) == "legacy-name"
    # ALREADY_NEW field preserved byte-for-byte.
    assert after["encrypted_dob"] == new_blob
    assert _decrypt_with(NEW_KEY, after["encrypted_dob"]) == "new-dob"


@pytest.mark.asyncio
async def test_already_new_row_untouched_byte_for_byte():
    from app.core.database import phi_engine

    token = uuid.uuid4()
    new_blob = _encrypt_with(NEW_KEY, "untouched")
    await _insert_row(token, uuid.uuid4(), {"encrypted_name": new_blob})

    row = _row({"client_token": token, "encrypted_name": new_blob})
    plan = build_rekey_plan([row], LEGACY_KEY, NEW_KEY)
    assert plan["blocked"] is False
    assert plan["rekey_entries"] == []
    assert plan["untouched_rows"] == 1

    async with phi_engine.begin() as conn:
        await _rekey_rows_tx(conn, plan["rekey_entries"], LEGACY_KEY, NEW_KEY)

    after = await _read_row(token)
    assert after["encrypted_name"] == new_blob  # byte-for-byte unchanged
    assert _decrypt_with(NEW_KEY, after["encrypted_name"]) == "untouched"


@pytest.mark.asyncio
async def test_all_legacy_row_fully_rekeyed():
    from app.core.database import phi_engine

    token = uuid.uuid4()
    legacy_blob = _encrypt_with(LEGACY_KEY, "full-legacy")
    await _insert_row(token, uuid.uuid4(), {"encrypted_name": legacy_blob})

    row = _row({"client_token": token, "encrypted_name": legacy_blob})
    plan = build_rekey_plan([row], LEGACY_KEY, NEW_KEY)
    assert plan["blocked"] is False

    async with phi_engine.begin() as conn:
        await _rekey_rows_tx(conn, plan["rekey_entries"], LEGACY_KEY, NEW_KEY)

    after = await _read_row(token)
    assert after["encrypted_name"] != legacy_blob
    assert _decrypt_with(NEW_KEY, after["encrypted_name"]) == "full-legacy"


@pytest.mark.asyncio
async def test_multiple_rows_mixed_updates():
    from app.core.database import phi_engine

    t1, t2 = uuid.uuid4(), uuid.uuid4()
    l1 = _encrypt_with(LEGACY_KEY, "r1-legacy")
    n2 = _encrypt_with(NEW_KEY, "r2-new")
    await _insert_row(t1, uuid.uuid4(), {"encrypted_name": l1})
    await _insert_row(t2, uuid.uuid4(), {"encrypted_dob": n2})

    rows = [
        _row({"client_token": t1, "encrypted_name": l1}),
        _row({"client_token": t2, "encrypted_dob": n2}),
    ]
    plan = build_rekey_plan(rows, LEGACY_KEY, NEW_KEY)
    assert plan["blocked"] is False
    assert len(plan["rekey_entries"]) == 1

    async with phi_engine.begin() as conn:
        await _rekey_rows_tx(conn, plan["rekey_entries"], LEGACY_KEY, NEW_KEY)

    after1 = await _read_row(t1)
    after2 = await _read_row(t2)
    assert _decrypt_with(NEW_KEY, after1["encrypted_name"]) == "r1-legacy"
    assert after2["encrypted_dob"] == n2  # untouched byte-for-byte
    assert _decrypt_with(NEW_KEY, after2["encrypted_dob"]) == "r2-new"


# ─────────────────────────────────────────────────────────────────────
# Exact-match synthetic cleanup (guarded persistence lane)
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cleanup_absent_token_is_safe_noop():
    from app.core.database import phi_engine
    from scripts.phi_rekey_legacy import cleanup_synthetic_row

    outcome = await cleanup_synthetic_row(
        phi_engine, str(uuid.uuid4()), str(uuid.uuid4())
    )
    assert outcome == "already-absent"


@pytest.mark.asyncio
async def test_cleanup_exact_match_deletes_exactly_one():
    from app.core.database import phi_engine
    from scripts.phi_rekey_legacy import cleanup_synthetic_row

    token = uuid.uuid4()
    firm = uuid.uuid4()
    await _insert_row(token, firm, {"encrypted_name": "x"})

    outcome = await cleanup_synthetic_row(phi_engine, str(token), str(firm))
    assert outcome == "deleted"

    async with phi_engine.connect() as conn:
        remaining = (await conn.execute(text(
            "SELECT count(*) FROM clients WHERE client_token = CAST(:t AS uuid)"
        ), {"t": str(token)})).scalar()
    assert remaining == 0


@pytest.mark.asyncio
async def test_cleanup_wrong_firm_refuses_zero_delete():
    from app.core.database import phi_engine
    from scripts.phi_rekey_legacy import cleanup_synthetic_row

    token = uuid.uuid4()
    actual_firm = uuid.uuid4()
    wrong_firm = uuid.uuid4()
    await _insert_row(token, actual_firm, {"encrypted_name": "x"})

    with pytest.raises(RekeyRefused):
        await cleanup_synthetic_row(phi_engine, str(token), str(wrong_firm))

    async with phi_engine.connect() as conn:
        remaining = (await conn.execute(text(
            "SELECT count(*) FROM clients WHERE client_token = CAST(:t AS uuid)"
        ), {"t": str(token)})).scalar()
    assert remaining == 1  # nothing deleted
