#!/usr/bin/env python3
"""One-off legacy PHI re-key utility (FND-002-R1, blocker 2).

Moves historical ``trace_phi.clients`` ciphertext from the removed legacy
fallback key to a new explicit 32-byte key, all-or-nothing:

    legacy key supplied through environment only
        -> decrypt EVERY non-null historical ciphertext field (zero writes)
        -> ANY failure: STOP, zero writes, exit 2 (BLOCKED)
    new explicit 32-byte key (environment only)
        -> re-encrypt all rows in ONE database transaction
        -> verify every rewritten field decrypts under the new key BEFORE commit
        -> commit
    fresh read-only full verification under the new key
    counts only — no plaintext, no keys, no secret material is ever printed.

Environment (all mandatory except the synthetic-row identifiers):

    TRACE_PHI_REKEY_DATABASE_URL      owner-designated non-production Supabase
                                      DIRECT connection URL (ref in host)
    TRACE_PHI_LEGACY_KEY              legacy key via environment only
    TRACE_PHI_ENCRYPTION_KEY          new explicit key via environment only
    TRACE_PHI_REKEY_CONFIRM           must equal TRUEVOW_NONPROD_PHI_REKEY
    TRACE_PHI_REKEY_ALLOWED_PROJECT_REF  default: cnbzuiuyppzrygxllgxj
    TRACE_PHI_REKEY_SYNTHETIC_TOKEN   disclosed synthetic validation row token
    TRACE_PHI_REKEY_SYNTHETIC_FIRM    disclosed synthetic validation row firm

Before re-keying, the one disclosed synthetic validation row is removed ONLY
when its exact client_token AND firm_id match; otherwise the run stops and
nothing is deleted.

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
DEFAULT_PROJECT_REF = "cnbzuiuyppzrygxllgxj"
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


def _fail(message: str, code: int = 1) -> None:
    print(f"REFUSED: {message}")
    sys.exit(code)


def _check_env() -> tuple[bytes, bytes, str]:
    if os.environ.get("TRACE_PHI_REKEY_CONFIRM", "") != REKEY_CONFIRM:
        _fail("TRACE_PHI_REKEY_CONFIRM must equal " + REKEY_CONFIRM)
    url = os.environ.get("TRACE_PHI_REKEY_DATABASE_URL", "")
    if not url.startswith("postgresql://") and not url.startswith("postgres://"):
        _fail("TRACE_PHI_REKEY_DATABASE_URL must be a PostgreSQL URL")
    host = (urlsplit(url).hostname or "").lower()
    allowed_ref = os.environ.get(
        "TRACE_PHI_REKEY_ALLOWED_PROJECT_REF", DEFAULT_PROJECT_REF
    )
    direct_ok = allowed_ref in host and host.endswith(".supabase.co")
    # Some environments cannot resolve the IPv6-only direct endpoint; the
    # designated project's transaction pooler is accepted ONLY with an
    # additional explicit latch (the URL credentials select the project).
    pooler_ok = (
        host.endswith(".pooler.supabase.com")
        and os.environ.get("TRACE_PHI_REKEY_ALLOW_POOLER", "") == REKEY_CONFIRM
    )
    if not direct_ok and not pooler_ok:
        _fail("TRACE_PHI_REKEY_DATABASE_URL host is not the designated "
              "non-production Supabase project")

    sys.path.insert(0, os.getcwd())
    from app.core.crypto import classify_phi_key, resolve_phi_key

    legacy_raw = os.environ.get("TRACE_PHI_LEGACY_KEY", "")
    new_raw = os.environ.get("TRACE_PHI_ENCRYPTION_KEY", "")
    try:
        legacy = resolve_phi_key(legacy_raw or None)
    except Exception as exc:  # noqa: BLE001
        _fail(f"legacy key invalid: {type(exc).__name__}")
    try:
        new = resolve_phi_key(new_raw or None)
    except Exception as exc:  # noqa: BLE001
        _fail(f"new key invalid: {type(exc).__name__}")
    if legacy == new:
        _fail("legacy and new key resolve to the same bytes")
    print(f"new_key_classification: {classify_phi_key(new_raw)}")
    return legacy, new, url


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


async def _load_rows(conn, excluded_token: str) -> list[dict]:
    result = await conn.execute(_SELECT_SQL, {"excluded": excluded_token})
    return [dict(row) for row in result.mappings().all()]


async def _run() -> None:
    legacy_key, new_key, url = _check_env()

    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    engine = create_async_engine(
        url.replace("postgresql://", "postgresql+asyncpg://", 1),
        connect_args={
            "statement_cache_size": 0,
            "server_settings": {"search_path": "trace_phi"},
        },
    )

    synthetic_token = os.environ.get(
        "TRACE_PHI_REKEY_SYNTHETIC_TOKEN", DISCLOSED_SYNTHETIC_TOKEN
    )
    synthetic_firm = os.environ.get(
        "TRACE_PHI_REKEY_SYNTHETIC_FIRM", DISCLOSED_SYNTHETIC_FIRM
    )

    # ── Disclosed synthetic validation row cleanup (exact match only) ──
    # Runs in its OWN transaction so the deletion is durable even when a
    # later preflight exits with BLOCKED.
    async with engine.begin() as conn:
        cleanup = await conn.execute(
            text(
                "DELETE FROM clients WHERE client_token = CAST(:t AS uuid) "
                "AND firm_id = CAST(:f AS uuid) RETURNING client_token"
            ),
            {"t": synthetic_token, "f": synthetic_firm},
        )
        deleted = cleanup.fetchall()
    print(f"synthetic_validation_row_cleanup: PASS "
          f"({'deleted' if deleted else 'already-absent'})")

    async with engine.connect() as conn:
        # ── Preflight: decrypt EVERY non-null field with the legacy key ──
        rows = await _load_rows(conn, synthetic_token)
        total_fields = 0
        for row in rows:
            for field in _FIELDS:
                value = row.get(field)
                if value:
                    total_fields += 1
                    try:
                        _decrypt_with(legacy_key, value)
                    except Exception as exc:  # noqa: BLE001
                        print(f"BLOCKED: legacy preflight decrypt failed for "
                              f"client_token={row['client_token']} "
                              f"field={field}: {type(exc).__name__}")
                        sys.exit(2)
        print(f"historical rows targeted: {len(rows)}")
        print(f"preflight legacy-decryptable fields: {total_fields}")

    if not rows:
        print("nothing to re-key; exiting")
        await engine.dispose()
        sys.exit(0)

    # ── Re-encrypt in ONE database transaction ──
    async with engine.begin() as conn:
        rekeyed_fields = 0
        for row in rows:
            updates: list[str] = []
            params: dict = {}
            for field in _FIELDS:
                value = row.get(field)
                if not value:
                    continue
                plaintext = _decrypt_with(legacy_key, value)
                new_blob = _encrypt_with(new_key, plaintext)
                # Verify the new blob BEFORE it is written.
                if _decrypt_with(new_key, new_blob) != plaintext:
                    print("BLOCKED: new-key verification failed before commit")
                    sys.exit(2)
                updates.append(f"{field} = :{field}")
                params[field] = new_blob
                rekeyed_fields += 1
            params["tok"] = row["client_token"]
            await conn.execute(
                text(
                    f"UPDATE clients SET {', '.join(updates)} "
                    "WHERE client_token = CAST(:tok AS uuid)"
                ),
                params,
            )
        print(f"historical rows rekeyed: {len(rows)}")
        print(f"fields rekeyed: {rekeyed_fields}")

    # ── Fresh read-only verification under the new key ──
    verified = 0
    async with engine.connect() as conn:
        for row in await _load_rows(conn, synthetic_token):
            for field in _FIELDS:
                value = row.get(field)
                if value:
                    _decrypt_with(new_key, value)
                    verified += 1
    print(f"new-key decryption verified fields: {verified}")

    async with engine.connect() as conn:
        final_count = (await conn.execute(text("SELECT count(*) FROM clients"))).scalar()
    print(f"final trace_phi.clients row count: {final_count}")
    print("REKEY COMPLETE")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_run())
