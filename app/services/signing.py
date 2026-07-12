"""DocuSeal SigningService — self-hosted e-signature gateway.

ADR-002 §6: handles `send_signing_package()` and `handle_signing_webhook()`.
DocuSeal runs self-hosted on Fly.io within the same HIPAA boundary — no
separate BAA, no cloud docuseal.com usage.

Key rules:
- Client contact retrieved from PHI store just-in-time, never cached
- Webhook signature verified on raw request body before JSON parsing
- Replay protection via unique constraint on docuseal_submission_id
- Case advances from PENDING_SIGNATURE → INITIALIZATION only on webhook
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from dataclasses import dataclass

import httpx

from app.core.logging import get_logger

logger = get_logger("trace.signing")

DOCUSEAL_SIGNING_LINK_EXPIRY_DAYS = int(os.getenv("DOCUSEAL_SIGNING_LINK_EXPIRY_DAYS", "7"))


@dataclass
class SigningPackageResult:
    submission_id: str
    signing_url: str
    expires_at: str


@dataclass
class SigningWebhookPayload:
    event_id: str
    submission_id: str
    status: str
    completed_at: str | None = None


class WebhookSignatureError(Exception):
    pass


class SigningService:
    def __init__(self) -> None:
        self._api_url = os.getenv("DOCUSEAL_API_URL", "")
        self._api_token = os.getenv("DOCUSEAL_API_TOKEN", "")
        self._webhook_secret = os.getenv("DOCUSEAL_WEBHOOK_SECRET", "")

    @property
    def configured(self) -> bool:
        return bool(self._api_url and self._api_token)

    async def send_signing_package(
        self,
        client_name: str,
        client_email: str,
        client_phone: str,
        firm_id: uuid.UUID,
        matter_reference: str,
    ) -> SigningPackageResult:
        if not self.configured:
            raise RuntimeError("DocuSeal is not configured. Set DOCUSEAL_API_URL, DOCUSEAL_API_TOKEN, DOCUSEAL_WEBHOOK_SECRET.")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._api_url}/api/submissions",
                headers={
                    "X-Auth-Token": self._api_token,
                    "Content-Type": "application/json",
                },
                json={
                    "template_id": str(firm_id),
                    "send_email": True,
                    "send_sms": True,
                    "submitters": [
                        {
                            "role": "Client",
                            "name": client_name,
                            "email": client_email,
                            "phone": client_phone,
                        }
                    ],
                    "metadata": {"matter_reference": matter_reference},
                },
            )
            response.raise_for_status()
            data = response.json()
            return SigningPackageResult(
                submission_id=data["submission_id"],
                signing_url=data.get("signing_url", ""),
                expires_at=data.get("expire_at", ""),
            )

    async def verify_webhook_signature(self, raw_body: bytes, signature: str) -> None:
        expected = hmac.new(
            self._webhook_secret.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(signature, expected):
            logger.warning(
                "DocuSeal webhook signature verification failed",
                extra={"signature_received": signature[:8] + "..."},
            )
            raise WebhookSignatureError("Invalid webhook signature")

    def parse_webhook_payload(self, raw_body: bytes) -> SigningWebhookPayload:
        data = json.loads(raw_body)
        return SigningWebhookPayload(
            event_id=data.get("event_id", ""),
            submission_id=data.get("submission_id", ""),
            status=data.get("status", ""),
            completed_at=data.get("completed_at"),
        )

    async def resend_reminder(self, submission_id: str) -> None:
        if not self.configured:
            return
        async with httpx.AsyncClient(timeout=15.0) as client:
            await client.post(
                f"{self._api_url}/api/submissions/{submission_id}/remind",
                headers={"X-Auth-Token": self._api_token},
            )
