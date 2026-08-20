"""FND-002 — PHI encryption key / store fail-closed tests.

DB-free key-contract tests use monkeypatched settings; store/readiness tests
require the guarded persistence lane. Tests always use explicit synthetic
keys — there is no fallback key in the suite.
"""

from __future__ import annotations

import base64
import uuid

import pytest

from app.core import crypto
from app.core.config import settings
from app.core.crypto import (
    PhiKeyError,
    classify_phi_key,
    decrypt,
    encrypt,
    resolve_phi_key,
)

RAW32 = "0123456789abcdef0123456789abcdef"  # exactly 32 bytes
RAW31 = "0123456789abcdef0123456789abcde"   # 31 bytes
RAW33 = "0123456789abcdef0123456789abcdeff"  # 33 bytes
OTHER32 = "abcdef0123456789abcdef0123456789"  # a different valid key
B64_32 = base64.b64encode(RAW32.encode()).decode()  # 44 chars -> 32 bytes


@pytest.fixture
def set_key(monkeypatch):
    def _set(value: str | None) -> None:
        monkeypatch.setattr(settings, "trace_phi_encryption_key", value or "")
    return _set


# ─────────────────────────────────────────────────────────────────────
# DB-free key contract
# ─────────────────────────────────────────────────────────────────────

class TestKeyContract:
    def test_missing_key_rejected(self, set_key):
        set_key(None)
        with pytest.raises(PhiKeyError):
            resolve_phi_key(settings.trace_phi_encryption_key)
        with pytest.raises(PhiKeyError):
            encrypt("x")
        with pytest.raises(PhiKeyError):
            decrypt(base64.b64encode(b"012345678901").decode())

    def test_empty_key_rejected(self, set_key):
        for bad in ("", "   "):
            set_key(bad)
            with pytest.raises(PhiKeyError):
                resolve_phi_key(settings.trace_phi_encryption_key)

    def test_short_raw_rejected(self, set_key):
        set_key(RAW31)
        with pytest.raises(PhiKeyError):
            resolve_phi_key(settings.trace_phi_encryption_key)

    def test_long_raw_rejected(self, set_key):
        set_key(RAW33)
        with pytest.raises(PhiKeyError):
            resolve_phi_key(settings.trace_phi_encryption_key)

    def test_malformed_input_rejected(self, set_key):
        for bad in ("!!!not-base64!!!", "a" * 44, "short"):
            set_key(bad)
            with pytest.raises(PhiKeyError):
                resolve_phi_key(settings.trace_phi_encryption_key)

    def test_valid_raw_32_accepted(self, set_key):
        set_key(RAW32)
        assert resolve_phi_key(settings.trace_phi_encryption_key) == RAW32.encode()
        assert classify_phi_key(settings.trace_phi_encryption_key) == "VALID_RAW_32"

    def test_valid_base64_32_accepted(self, set_key):
        set_key(B64_32)
        assert resolve_phi_key(settings.trace_phi_encryption_key) == RAW32.encode()
        assert classify_phi_key(settings.trace_phi_encryption_key) == "VALID_BASE64_32"

    def test_base64_precedence_over_raw(self, set_key):
        # Value that is BOTH valid base64 of 32 bytes AND raw of another
        # length: base64 interpretation must win.
        set_key(B64_32)
        assert classify_phi_key(settings.trace_phi_encryption_key) == "VALID_BASE64_32"
        assert resolve_phi_key(settings.trace_phi_encryption_key) == RAW32.encode()

    def test_no_dev_key_fallback_remains(self):
        assert not hasattr(crypto, "_DEV_KEY")
        with pytest.raises(PhiKeyError):
            resolve_phi_key(None)


class TestCryptoBehavior:
    def test_aes_gcm_round_trip(self, set_key):
        set_key(RAW32)
        encoded = encrypt("Jane Q. Public 1985-04-12")
        assert decrypt(encoded) == "Jane Q. Public 1985-04-12"

    def test_nonce_randomness(self, set_key):
        set_key(RAW32)
        a = encrypt("same plaintext")
        b = encrypt("same plaintext")
        assert a != b

    def test_tampered_ciphertext_fails(self, set_key):
        from cryptography.exceptions import InvalidTag

        set_key(RAW32)
        blob = bytearray(base64.b64decode(encrypt("tamper me")))
        blob[-1] ^= 0x01
        with pytest.raises(InvalidTag):
            decrypt(base64.b64encode(bytes(blob)).decode())

    def test_wrong_valid_key_cannot_decrypt(self, set_key):
        from cryptography.exceptions import InvalidTag

        set_key(RAW32)
        encoded = encrypt("secret")
        set_key(OTHER32)
        with pytest.raises(InvalidTag):
            decrypt(encoded)

    def test_classifications(self):
        assert classify_phi_key(None) == "MISSING"
        assert classify_phi_key("") == "MISSING"
        assert classify_phi_key("short") == "INVALID"


# ─────────────────────────────────────────────────────────────────────
# PHI store behavior (guarded persistence lane)
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_store_rejects_missing_key_without_partial_row(monkeypatch):
    from sqlalchemy import select

    from app.core.database import phi_session_maker
    from app.models.client import Client
    from app.services.phi_store import store_client

    monkeypatch.setattr(settings, "trace_phi_encryption_key", "")
    with pytest.raises(PhiKeyError):
        await store_client(
            name="No", dob="1980-01-01", address="X", phone="1",
            firm_id=uuid.uuid4(),
        )
    async with phi_session_maker() as session:
        count = len((await session.execute(select(Client))).scalars().all())
    assert count == 0


@pytest.mark.asyncio
async def test_failed_write_leaves_no_partial_row(monkeypatch):
    from sqlalchemy import select

    from app.core.database import phi_session_maker
    from app.models.client import Client
    from app.services import phi_store as phi_store_module

    real_encrypt = phi_store_module.encrypt
    calls = {"n": 0}

    def failing_encrypt(plaintext: str) -> str:
        calls["n"] += 1
        if calls["n"] >= 2:
            raise PhiKeyError("injected mid-write failure")
        return real_encrypt(plaintext)

    monkeypatch.setattr(phi_store_module, "encrypt", failing_encrypt)
    with pytest.raises(PhiKeyError):
        await phi_store_module.store_client(
            name="Partial", dob="1980-01-01", address="X", phone="1",
            firm_id=uuid.uuid4(),
        )
    async with phi_session_maker() as session:
        count = len((await session.execute(select(Client))).scalars().all())
    assert count == 0


@pytest.mark.asyncio
async def test_decryption_failure_is_controlled(monkeypatch):
    from app.services.phi_store import get_client, store_client

    token = await store_client(
        name="Controlled", dob="1980-01-01", address="X", phone="1",
        firm_id=uuid.uuid4(),
    )
    # Wrong valid key: decryption must fail closed to None, never garbage.
    monkeypatch.setattr(settings, "trace_phi_encryption_key", OTHER32)
    assert await get_client(token) is None


# ─────────────────────────────────────────────────────────────────────
# /ready PHI-key check (guarded persistence lane)
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ready_phi_key_ok_with_valid_key(client):
    resp = await client.get("/ready")
    body = resp.json()
    assert body["checks"].get("phi_key") == "ok"
    assert body["status"] == "ready"
    assert "phi_key" not in body["failed"]


@pytest.mark.asyncio
async def test_ready_phi_key_fails_closed_on_missing_key(client, monkeypatch):
    monkeypatch.setattr(settings, "trace_phi_encryption_key", "")
    resp = await client.get("/ready")
    body = resp.json()
    assert body["checks"]["phi_key"].startswith("fail")
    assert body["status"] == "not_ready"
    assert "phi_key" in body["failed"]
    # Non-secret: the response must never contain key material.
    assert RAW32 not in resp.text
    assert B64_32 not in resp.text
