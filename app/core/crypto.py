"""Application-level AES-256-GCM encryption for PHI columns.

FND-002 — fail-closed key handling:

  - no hard-coded development key exists in executable code;
  - ``TRACE_PHI_ENCRYPTION_KEY`` must be valid base64 decoding to exactly
    32 bytes, or raw UTF-8 of exactly 32 bytes (base64 is checked first);
  - missing, empty, short, long, or malformed keys raise ``PhiKeyError`` —
    keys are never padded, truncated, generated, or silently reinterpreted;
  - the ciphertext format (``nonce(12) || ciphertext+tag``, then base64) is
    unchanged, so ciphertext produced with a valid 32-byte key remains
    decryptable;
  - key material is never logged and never appears in responses; readiness
    reports only ok/fail.

Ciphertext is stored as base64-encoded Text in ``trace_phi.clients``.
"""

from __future__ import annotations

import base64
import binascii
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

_NONCE_BYTES = 12
_KEY_BYTES = 32


class PhiKeyError(Exception):
    """PHI encryption key is missing or malformed (fail closed)."""


class PhiDecryptError(Exception):
    """Ciphertext exists but cannot be authenticated/decrypted."""


def resolve_phi_key(raw: str | None) -> bytes:
    """Resolve ``TRACE_PHI_ENCRYPTION_KEY`` to exactly 32 bytes.

    Precedence: valid base64 -> exactly 32 bytes first, then raw UTF-8 of
    exactly 32 bytes. Everything else raises ``PhiKeyError``.

    Error messages are sanitized: they never disclose supplied key lengths
    or any key-derived detail.
    """
    if not raw or not raw.strip():
        raise PhiKeyError("TRACE_PHI_ENCRYPTION_KEY is not configured.")

    try:
        decoded = base64.b64decode(raw, validate=True)
    except (ValueError, binascii.Error):
        decoded = b""
    if len(decoded) == _KEY_BYTES:
        return decoded

    as_raw = raw.encode("utf-8")
    if len(as_raw) == _KEY_BYTES:
        return as_raw

    raise PhiKeyError(
        "TRACE_PHI_ENCRYPTION_KEY is malformed: it must be valid base64 "
        "decoding to exactly 32 bytes, or raw UTF-8 of exactly 32 bytes."
    )


def classify_phi_key(raw: str | None) -> str:
    """Non-secret classification of a key value for validation reporting."""
    if not raw or not raw.strip():
        return "MISSING"
    try:
        key = resolve_phi_key(raw)
    except PhiKeyError:
        return "INVALID"
    try:
        decoded = base64.b64decode(raw, validate=True)
    except (ValueError, binascii.Error):
        decoded = b""
    return "VALID_BASE64_32" if decoded == key else "VALID_RAW_32"


def _key() -> bytes:
    return resolve_phi_key(settings.trace_phi_encryption_key)


def validate_phi_key() -> None:
    """Structural readiness check: raises ``PhiKeyError`` when unusable."""
    _key()


def encrypt(plaintext: str) -> str:
    aesgcm = AESGCM(_key())
    nonce = os.urandom(_NONCE_BYTES)
    blob = nonce + aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(blob).decode()


def decrypt(encoded: str) -> str:
    blob = base64.b64decode(encoded)
    aesgcm = AESGCM(_key())
    nonce, ciphertext = blob[:_NONCE_BYTES], blob[_NONCE_BYTES:]
    return aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
