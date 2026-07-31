"""Shared Foundation: Webhook Signature Verification.

HMAC-based webhook authentication replacing simple shared-secret headers.
Implements the TrueVow cross-service webhook security model.

Headers:
    X-TrueVow-Key-Id      — identifies which signing key (supports rotation)
    X-TrueVow-Timestamp    — Unix timestamp of request (30 min tolerance)
    X-TrueVow-Signature    — HMAC-SHA256 over timestamp:method:path:body_hash

Security properties:
    - Short timestamp tolerance (default 5 min, configurable)
    - Constant-time comparison
    - Secret rotation via key_id -> secret mapping
    - Replay rejection via timestamp window
    - Per-environment keys (dev, staging, production)
    - No secret values in logs (secrets never serialized)

This is designed for extraction to a shared TrueVow foundation package.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class VerifyStatus(str, Enum):
    OK = "OK"
    MISSING_HEADERS = "MISSING_HEADERS"
    UNKNOWN_KEY = "UNKNOWN_KEY"
    EXPIRED_TIMESTAMP = "EXPIRED_TIMESTAMP"
    FUTURE_TIMESTAMP = "FUTURE_TIMESTAMP"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"


@dataclass
class VerifyResult:
    status: VerifyStatus
    detail: str = ""


class KeyStore(Protocol):
    """Protocol for key retrieval. Implementations can fetch from env, DB, vault."""

    def get_secret(self, key_id: str) -> str | None: ...


class EnvKeyStore:
    """Default key store: reads keys from environment variables.

    Primary format (matches SaaS Admin convention):
        TRUEVOW_WEBHOOK_KEY_ID=<key_id>
        TRUEVOW_WEBHOOK_SECRET=<secret>

    Rotation format (additional keys):
        TRUEVOW_WEBHOOK_SECONDARY_KEYS=[{"key_id":"tv-secondary","secret":"..."}]

    Also supports prefix convention for backward compatibility:
        TRUEVOW_WEBHOOK_KEY_<key_id>=<secret>
    """

    def get_secret(self, key_id: str) -> str | None:
        primary_key_id = os.environ.get("TRUEVOW_WEBHOOK_KEY_ID", "")
        primary_secret = os.environ.get("TRUEVOW_WEBHOOK_SECRET", "")
        if key_id == primary_key_id and primary_secret:
            return primary_secret

        env_key = f"TRUEVOW_WEBHOOK_KEY_{key_id}"
        env_secret = os.environ.get(env_key)
        if env_secret:
            return env_secret

        secondary_json = os.environ.get("TRUEVOW_WEBHOOK_SECONDARY_KEYS", "")
        if secondary_json:
            try:
                import json
                secondary_keys = json.loads(secondary_json)
                for entry in secondary_keys:
                    if entry.get("key_id") == key_id:
                        return entry.get("secret")
            except (json.JSONDecodeError, TypeError):
                pass

        return None


class WebhookVerifier:
    """HMAC signature verifier for cross-service webhooks.

    Usage:
        verifier = WebhookVerifier(key_store=EnvKeyStore(), tolerance_seconds=300)

        result = verifier.verify(
            key_id="prod_1",
            timestamp_str="1699123456",
            signature="hmac_hex...",
            method="POST",
            path="/webhooks/matter-activated",
            raw_body=b'{"event_id": "..."}',
        )

        if result.status != VerifyStatus.OK:
            raise HTTPException(401, result.detail)
    """

    def __init__(
        self,
        key_store: KeyStore | None = None,
        tolerance_seconds: int = 300,
    ):
        self._key_store = key_store or EnvKeyStore()
        self._tolerance_seconds = tolerance_seconds
        self._seen_timestamps: set[tuple[str, str]] = set()

    def verify(
        self,
        key_id: str | None,
        timestamp_str: str | None,
        signature: str | None,
        method: str,
        path: str,
        raw_body: bytes,
    ) -> VerifyResult:
        """Verify a webhook request signature. Fail-closed."""
        if not key_id:
            return VerifyResult(VerifyStatus.MISSING_HEADERS, "Missing X-TrueVow-Key-Id header")
        if not timestamp_str:
            return VerifyResult(VerifyStatus.MISSING_HEADERS, "Missing X-TrueVow-Timestamp header")
        if not signature:
            return VerifyResult(VerifyStatus.MISSING_HEADERS, "Missing X-TrueVow-Signature header")

        secret = self._key_store.get_secret(key_id)
        if secret is None:
            return VerifyResult(VerifyStatus.UNKNOWN_KEY, f"Unknown key ID: {key_id}")

        try:
            timestamp = int(timestamp_str)
        except (ValueError, TypeError):
            return VerifyResult(VerifyStatus.INVALID_SIGNATURE, "Timestamp is not a valid integer")

        now = int(time.time())
        age = now - timestamp
        if age < -self._tolerance_seconds:
            return VerifyResult(VerifyStatus.FUTURE_TIMESTAMP,
                               f"Timestamp is {abs(age)}s in the future (tolerance: {self._tolerance_seconds}s)")
        if age > self._tolerance_seconds:
            return VerifyResult(VerifyStatus.EXPIRED_TIMESTAMP,
                               f"Timestamp is {age}s old (tolerance: {self._tolerance_seconds}s)")

        replay_key = (key_id, timestamp_str)
        if replay_key in self._seen_timestamps:
            return VerifyResult(VerifyStatus.EXPIRED_TIMESTAMP, "Replay detected: timestamp already used")
        self._seen_timestamps.add(replay_key)

        body_hash = hashlib.sha256(raw_body).hexdigest()
        canonical_string = f"{timestamp_str}:{method}:{path}:{body_hash}"

        expected = hmac.new(
            secret.encode("utf-8"),
            canonical_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not _constant_time_compare(expected, signature):
            return VerifyResult(VerifyStatus.INVALID_SIGNATURE,
                               "Signature does not match")

        return VerifyResult(VerifyStatus.OK)

    def verify_from_request(
        self,
        method: str,
        path: str,
        raw_body: bytes,
        key_id: str | None,
        timestamp: str | None,
        signature: str | None,
    ) -> VerifyResult:
        """Convenience method matching FastAPI header parameter names."""
        return self.verify(key_id, timestamp, signature, method, path, raw_body)


def _constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return result == 0


_verifier: WebhookVerifier | None = None


def get_webhook_verifier(tolerance_seconds: int = 300) -> WebhookVerifier:
    global _verifier
    if _verifier is None:
        _verifier = WebhookVerifier(tolerance_seconds=tolerance_seconds)
    return _verifier
