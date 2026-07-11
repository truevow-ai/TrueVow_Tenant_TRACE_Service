#!/usr/bin/env python3
"""Simulate a client signing the DocuSeal package.

Fires a valid DocuSeal webhook to advance the case from
PENDING_SIGNATURE to INITIALIZATION. Generates a valid HMAC
signature using DOCUSEAL_WEBHOOK_SECRET from environment.

Usage:
    python scripts/simulate_client_signing.py --case-id <uuid>
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
import uuid
from datetime import datetime, timezone


def simulate_signing_webhook(case_id: uuid.UUID) -> dict:
    """Fire a simulated DocuSeal signing-complete webhook."""
    secret = os.getenv("DOCUSEAL_WEBHOOK_SECRET", "dev-webhook-secret-test")
    submission_id = f"synth-{case_id.hex[:12]}"

    payload = {
        "event_id": f"evt_{case_id.hex[:8]}",
        "submission_id": submission_id,
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    raw_body = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()

    from httpx import AsyncClient, ASGITransport
    from app.main import app

    async def _send():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/trace/webhooks/docuseal/signing-complete",
                content=raw_body,
                headers={
                    "Content-Type": "application/json",
                    "X-Docuseal-Signature": signature,
                },
            )
            return response.status_code, response.json()

    import asyncio

    status, body = asyncio.run(_send())
    return {"status": status, "body": body, "submission_id": submission_id}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate client signing webhook")
    parser.add_argument("--case-id", required=True, help="Synthetic case UUID")
    args = parser.parse_args()

    try:
        case_id = uuid.UUID(args.case_id)
    except ValueError as exc:
        print(f"Invalid case ID: {exc}", file=sys.stderr)
        sys.exit(1)

    result = simulate_signing_webhook(case_id)
    print(f"Status: {result['status']}")
    print(f"Body: {json.dumps(result['body'], indent=2)}")
    print(f"Submission: {result['submission_id']}")
