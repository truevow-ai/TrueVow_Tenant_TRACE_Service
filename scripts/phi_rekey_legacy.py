#!/usr/bin/env python3
"""One-off legacy PHI re-key utility (FND-002-R2, hardened).

Moves historical ``trace_phi.clients`` ciphertext from the removed legacy
fallback key to a new explicit 32-byte key, all-or-nothing, with mixed-key
classification:

    every non-null encrypted field is classified:
        LEGACY      — decrypts with the supplied legacy key
        ALREADY_NEW — fails legacy but decrypts with the supplied new key
        BLOCKED     — decrypts with neither
    BLOCKED > 0  -> STOP before any re-key write (exit 2)
    BLOCKED = 0  -> re-key the LEGACY cohort only (rows containing any
                    LEGACY field), in ONE database transaction, every new
                    blob verified decryptable BEFORE commit; ALREADY_NEW rows
                    are left untouched; fresh post-commit verification of all
                    remaining rows under the new key.

Targeted mode (TRACE_PHI_REKEY_TARGET_TOKEN) re-keys exactly one row using
the legacy key; it touches no other row and requires every non-null field of
that row to decrypt with the supplied legacy key.

Project binding is fixed: the designated project is
``cnbzuiuyppzrygxllgxj`` and cannot be substituted via environment. Direct
URLs must carry the ref in the host; pooler URLs additionally require the
explicit pooler latch AND a pooler username identifying the project
(standard Supabase pooler username: postgres.<project_ref>).

Synthetic-row cleanup first SELECTs by exact token: absent -> already-absent;
present with a DIFFERENT firm -> REFUSE and delete nothing; exact token+firm
match -> delete exactly one row (asserted).

Environment (mandatory): TRACE_PHI_REKEY_DATABASE_URL, TRACE_PHI_LEGACY_KEY,
TRACE_PHI_ENCRYPTION_KEY, TRACE_PHI_REKEY_CONFIRM=TRUEVOW_NONPROD_PHI_REKEY.
Optional: TRACE_PHI_REKEY_ALLOW_POOLER, TRACE_PHI_REKEY_TARGET_TOKEN,
TRACE_PHI_REKEY_SYNTHETIC_TOKEN / _FIRM (bulk mode cleanup).

Counts only are printed — no plaintext, no keys, no secret material.
Exit codes: 0 success, 2 preflight BLOCKED, 1 refused/misconfigured.
"""

from __future__ import annotations

import asyncio
import base64
import os
import sys
from urllib.parse import urlsplit

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

REKEY_CONFIRM = "TRUEVOW_NONPROD_PHI_REKEY"
FIXED_PROJECT_REF = "cnbzuiuyppzrygxllgxj"
EXACT_DIRECT_HOST = f"db.{FIXED_PROJECT_REF}.supabase.co"
EXACT_POOLER_USERNAME = f"postgres.{FIXED_PROJECT_REF}"
DISCLOSED_SYNTHETIC_TOKEN = "cf8c5919-f2fa-4534-9272-16ac706fa3b0"
DISCLOSED_SYNTHETIC_FIRM = "6de57278-c6ce-4f19-a34f-ece2ce24b43b"

_NONCE_BYTES = 12

_FIELDS = ("encrypted_name", "encrypted_dob", "encrypted_address",
           "encrypted_phone", "encrypted_email")

_SELECT_SQL = text(
    "SELECT client_token, firm_id, encrypted_name, encrypted_dob, "
    "encrypted_address, encrypted_phone, encrypted_email "
    "FROM clients WHERE client_token <> CAST(:excluded AS uuid)"
)
_SELECT_ONE_SQL = text(
    "SELECT client_token, firm_id, encrypted_name, encrypted_dob, "
    "encrypted_address, encrypted_phone, encrypted_email "
    "FROM clients WHERE client_token = CAST(:token AS uuid)"
)


class RekeyRefused(Exception):
    """Guards refused the operation (exit 1)."""


class RekeyBlocked(Exception):
    """Preflight found undecryptable data — zero writes (exit 2)."""


# ─────────────────────────────────────────────────────────────────────
# Pure, testable helpers
# ─────────────────────────────────────────────────────────────────────

def validate_rekey_url(url: str, pooler_latch: str = "") -> str:
    """Validate the re-key URL against EXACT designated-project identity.

    Direct: host must be exactly db.<ref>.supabase.co. Pooler: host must end
    .pooler.supabase.com, the explicit latch must match, and the parsed
    username must be exactly postgres.<ref>. No substring matching anywhere.

    Returns the normalized postgresql:// URL or raises RekeyRefused.
    """
    if not url or not (
        url.startswith("postgresql://") or url.startswith("postgres://")
    ):
        raise RekeyRefused("TRACE_PHI_REKEY_DATABASE_URL must be a PostgreSQL URL")
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    username = parsed.username or ""
    direct_ok = host == EXACT_DIRECT_HOST
    pooler_ok = (
        host.endswith(".pooler.supabase.com")
        and pooler_latch == REKEY_CONFIRM
        and username == EXACT_POOLER_USERNAME
    )
    if not direct_ok and not pooler_ok:
        raise RekeyRefused(
            "TRACE_PHI_REKEY_DATABASE_URL does not exactly identify the "
            f"designated project ({FIXED_PROJECT_REF})"
        )
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def _try_decrypt(key: bytes, encoded: str) -> bool:
    try:
        blob = base64.b64decode(encoded)
        aesgcm = AESGCM(key)
        nonce, ciphertext = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
        aesgcm.decrypt(nonce, ciphertext, None)
        return True
    except Exception:
        return False


def _encrypt_with(key: bytes, plaintext: str) -> str:
    aesgcm = AESGCM(key)
    nonce = os.urandom(_NONCE_BYTES)
    blob = nonce + aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(blob).decode()


def _decrypt_with(key: bytes, encoded: str) -> str:
    blob = base64.b64decode(encoded)
    aesgcm = AESGCM(key)
    nonce, ciphertext = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


def classify_field(value: str, legacy_key: bytes, new_key: bytes) -> str:
    """Classify one non-null ciphertext field: LEGACY / ALREADY_NEW / BLOCKED."""
    if _try_decrypt(legacy_key, value):
        return "LEGACY"
    if _try_decrypt(new_key, value):
        return "ALREADY_NEW"
    return "BLOCKED"


def build_rekey_plan(rows: list[dict], legacy_key: bytes, new_key: bytes) -> dict:
    """Mixed-key transaction plan with FIELD-LEVEL state.

    Each row entry records exactly which fields are LEGACY (to be re-encrypted
    with the new key) and which are ALREADY_NEW (left byte-for-byte
    untouched). Rows containing only ALREADY_NEW fields are not touched at
    all. Any BLOCKED field anywhere makes the whole plan blocked (zero
    writes).
    """
    rekey_entries: list[dict] = []
    untouched_rows = 0
    blocked_fields = 0
    for row in rows:
        legacy_fields: list[str] = []
        already_new_fields: list[str] = []
        has_blocked = False
        for field in _FIELDS:
            value = row.get(field)
            if not value:
                continue
            state = classify_field(value, legacy_key, new_key)
            if state == "BLOCKED":
                has_blocked = True
                blocked_fields += 1
            elif state == "LEGACY":
                legacy_fields.append(field)
            else:
                already_new_fields.append(field)
        if has_blocked:
            continue  # counted; plan stays blocked
        if legacy_fields:
            rekey_entries.append({
                "row": row,
                "legacy_fields": legacy_fields,
                "already_new_fields": already_new_fields,
            })
        else:
            untouched_rows += 1
    return {
        "rekey_entries": rekey_entries,
        "untouched_rows": untouched_rows,
        "blocked_fields": blocked_fields,
        "blocked": blocked_fields > 0,
    }


# ─────────────────────────────────────────────────────────────────────
# Database steps
# ─────────────────────────────────────────────────────────────────────

async def cleanup_synthetic_row(engine, token_str: str, firm_str: str) -> str:
    """Exact-match synthetic-row cleanup.

    Returns "deleted" or "already-absent"; raises RekeyRefused when the token
    exists under a different firm (nothing is deleted).
    """
    async with engine.begin() as conn:
        existing = (await conn.execute(
            text("SELECT firm_id FROM clients WHERE client_token = CAST(:t AS uuid)"),
            {"t": token_str},
        )).fetchone()
        if existing is None:
            return "already-absent"
        if str(existing[0]).lower() != firm_str.strip().lower():
            raise RekeyRefused(
                "synthetic token exists under a different firm; refusing to delete"
            )
        deleted = (await conn.execute(
            text(
                "DELETE FROM clients WHERE client_token = CAST(:t AS uuid) "
                "AND firm_id = CAST(:f AS uuid) RETURNING client_token"
            ),
            {"t": token_str, "f": firm_str},
        )).fetchall()
        if len(deleted) != 1:
            raise RekeyRefused("expected exactly one synthetic row deletion")
    return "deleted"


async def _load_rows(conn, excluded_token: str | None = None) -> list[dict]:
    if excluded_token is None:
        result = await conn.execute(text(
            "SELECT client_token, firm_id, encrypted_name, encrypted_dob, "
            "encrypted_address, encrypted_phone, encrypted_email FROM clients"
        ))
    else:
        result = await conn.execute(_SELECT_SQL, {"excluded": excluded_token})
    return [dict(row) for row in result.mappings().all()]


async def _rekey_rows_tx(
    conn,
    rekey_entries: list[dict],
    legacy_key: bytes,
    new_key: bytes,
) -> int:
    """Field-level re-key inside ONE transaction.

    Only LEGACY fields are rewritten (decrypt legacy -> encrypt new, verified
    decryptable before write). ALREADY_NEW fields are left byte-for-byte
    untouched (excluded from the UPDATE entirely) but are verified decryptable
    under the new key before commit.
    """
    rekeyed_fields = 0
    for entry in rekey_entries:
        row = entry["row"]
        updates: list[str] = []
        params: dict = {}
        for field in entry["legacy_fields"]:
            plaintext = _decrypt_with(legacy_key, row[field])
            new_blob = _encrypt_with(new_key, plaintext)
            if _decrypt_with(new_key, new_blob) != plaintext:
                raise RekeyBlocked("new-key verification failed before commit")
            updates.append(f"{field} = :{field}")
            params[field] = new_blob
            rekeyed_fields += 1
        for field in entry["already_new_fields"]:
            if not _try_decrypt(new_key, row[field]):
                raise RekeyBlocked(
                    "already-new field failed pre-commit verification"
                )
        if not updates:
            continue
        params["tok"] = row["client_token"]
        await conn.execute(
            text(
                f"UPDATE clients SET {', '.join(updates)} "
                "WHERE client_token = CAST(:tok AS uuid)"
            ),
            params,
        )
    return rekeyed_fields


async def _run() -> None:
    try:
        await _run_guarded()
    except RekeyRefused as exc:
        print(f"REFUSED: {exc}")
        sys.exit(1)
    except RekeyBlocked as exc:
        print(f"BLOCKED: {exc}")
        sys.exit(2)


async def _run_guarded() -> None:
    if os.environ.get("TRACE_PHI_REKEY_CONFIRM", "") != REKEY_CONFIRM:
        raise RekeyRefused("TRACE_PHI_REKEY_CONFIRM must equal " + REKEY_CONFIRM)

    sys.path.insert(0, os.getcwd())
    from app.core.crypto import classify_phi_key, resolve_phi_key

    legacy_raw = os.environ.get("TRACE_PHI_LEGACY_KEY", "")
    new_raw = os.environ.get("TRACE_PHI_ENCRYPTION_KEY", "")
    try:
        legacy_key = resolve_phi_key(legacy_raw or None)
    except Exception as exc:  # noqa: BLE001
        raise RekeyRefused(f"legacy key invalid: {type(exc).__name__}") from exc
    try:
        new_key = resolve_phi_key(new_raw or None)
    except Exception as exc:  # noqa: BLE001
        raise RekeyRefused(f"new key invalid: {type(exc).__name__}") from exc
    if legacy_key == new_key:
        raise RekeyRefused("legacy and new key resolve to the same bytes")
    print(f"new_key_classification: {classify_phi_key(new_raw)}")

    url = validate_rekey_url(
        os.environ.get("TRACE_PHI_REKEY_DATABASE_URL", ""),
        pooler_latch=os.environ.get("TRACE_PHI_REKEY_ALLOW_POOLER", ""),
    )
    engine = create_async_engine(
        url.replace("postgresql://", "postgresql+asyncpg://", 1),
        connect_args={
            "statement_cache_size": 0,
            "server_settings": {"search_path": "trace_phi"},
        },
    )

    target_token = os.environ.get("TRACE_PHI_REKEY_TARGET_TOKEN", "").strip()

    if target_token:
        await _run_targeted(engine, target_token, legacy_key, new_key)
        await engine.dispose()
        return

    synthetic_token = os.environ.get(
        "TRACE_PHI_REKEY_SYNTHETIC_TOKEN", DISCLOSED_SYNTHETIC_TOKEN
    )
    synthetic_firm = os.environ.get(
        "TRACE_PHI_REKEY_SYNTHETIC_FIRM", DISCLOSED_SYNTHETIC_FIRM
    )
    outcome = await cleanup_synthetic_row(engine, synthetic_token, synthetic_firm)
    print(f"synthetic_validation_row_cleanup: PASS ({outcome})")

    async with engine.connect() as conn:
        rows = await _load_rows(conn, excluded_token=synthetic_token)

    plan = build_rekey_plan(rows, legacy_key, new_key)
    print(f"total rows considered: {len(rows)}")
    print(f"legacy cohort rows: {len(plan['rekey_entries'])}")
    print(f"already-new rows (untouched): {plan['untouched_rows']}")
    print(f"blocked fields: {plan['blocked_fields']}")

    if plan["blocked"]:
        raise RekeyBlocked(
            f"{plan['blocked_fields']} ciphertext field(s) decrypt with neither key"
        )

    async with engine.begin() as conn:
        rekeyed_fields = await _rekey_rows_tx(
            conn, plan["rekey_entries"], legacy_key, new_key
        )
    print(f"rows rekeyed: {len(plan['rekey_entries'])}")
    print(f"fields rekeyed: {rekeyed_fields}")

    # Fresh post-commit verification of ALL remaining rows under the new key.
    verified = 0
    async with engine.connect() as conn:
        for row in await _load_rows(conn, excluded_token=synthetic_token):
            for field in _FIELDS:
                value = row.get(field)
                if value:
                    if not _try_decrypt(new_key, value):
                        raise RekeyBlocked("post-commit verification failed")
                    verified += 1
    print(f"new-key decryption verified fields: {verified}")

    async with engine.connect() as conn:
        final_count = (await conn.execute(text("SELECT count(*) FROM clients"))).scalar()
    print(f"final trace_phi.clients row count: {final_count}")
    print("REKEY COMPLETE")
    await engine.dispose()


async def _run_targeted(engine, target_token: str, legacy_key: bytes, new_key: bytes) -> None:
    async with engine.connect() as conn:
        result = await conn.execute(_SELECT_ONE_SQL, {"token": target_token})
        rows = [dict(r) for r in result.mappings().all()]
    if len(rows) != 1:
        raise RekeyRefused(
            f"target token must match exactly one row (matched {len(rows)})"
        )
    row = rows[0]

    # Preflight: EVERY non-null field must decrypt with the legacy key.
    non_null_fields: list[str] = []
    for field in _FIELDS:
        value = row.get(field)
        if value and not _try_decrypt(legacy_key, value):
            raise RekeyBlocked(
                f"target row preflight failed for field={field} under legacy key"
            )
        if value:
            non_null_fields.append(field)

    entry = {"row": row, "legacy_fields": non_null_fields, "already_new_fields": []}
    async with engine.begin() as conn:
        rekeyed_fields = await _rekey_rows_tx(conn, [entry], legacy_key, new_key)

    async with engine.connect() as conn:
        verify = (await conn.execute(_SELECT_ONE_SQL, {"token": target_token})).mappings().all()
    for field in _FIELDS:
        value = verify[0].get(field)
        if value and not _try_decrypt(new_key, value):
            raise RekeyBlocked("target row post-commit verification failed")

    print(f"targeted re-key complete: token={target_token} fields={rekeyed_fields}")


if __name__ == "__main__":
    asyncio.run(_run())
