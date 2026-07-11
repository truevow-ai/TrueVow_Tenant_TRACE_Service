"""Application-level AES-256-GCM encryption for PHI columns.

Encrypting in the application (rather than pgcrypto in the DB) keeps the key out
of the database entirely — it comes from KMS/Secrets Manager — which matches the
spec's "keys managed via KMS, never stored in the database" requirement and stays
portable across the operational Postgres and the SQLite test fallback.

Ciphertext is stored as base64-encoded Text in ``trace_phi.clients``.
Wire format: ``nonce(12) || ciphertext+tag``, then base64-encoded.
"""

from __future__ import annotations

import base64
import binascii
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings

_NONCE_BYTES = 12
_DEV_KEY = b"trace-dev-insecure-phi-key-32byt"  # exactly 32 bytes; dev/test only


def _key() -> bytes:
    raw = settings.trace_phi_encryption_key
    if not raw:
        return _DEV_KEY
    try:
        decoded = base64.b64decode(raw, validate=True)
    except (ValueError, binascii.Error):
        decoded = raw.encode("utf-8")
    if len(decoded) < 32:
        decoded = decoded.ljust(32, b"0")
    return decoded[:32]


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
