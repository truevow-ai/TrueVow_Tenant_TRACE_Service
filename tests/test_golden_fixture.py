"""Golden Fixture Test — cross-repository contract validation (BP-00).

Every service in the cross-product spine must validate the same 18-field
EventEnvelope and compute the same HMAC over the same raw fixture. This
test serves as the TRACE-side proof that contracts are honored.

Golden fixture: the canonical matter.activated event that every service
in the pipeline (SaaS Admin, INTAKE, RETAINER, TRACE, SETTLE) must
validate identically.
"""

import hashlib
import hmac
import json

from app.shared.event_store import EventEnvelope


GOLDEN_EVENT_ID = "e1a2b3c4-0001-4000-8000-000000000001"
GOLDEN_TENANT_ID = "11111111-1111-4111-8111-111111111111"
GOLDEN_MATTER_ID = "d379ee9b-19f7-4871-a86e-9684c69a11c3"
GOLDEN_TIMESTAMP = "1712345678000"  # milliseconds per WebhookSignature v1.0
GOLDEN_KEY_ID = "test_key_v1"
GOLDEN_KEY_SECRET = "test-secret-at-least-32-bytes-long-000"
GOLDEN_METHOD = "POST"
GOLDEN_PATH = "/api/v1/trace/webhooks/matter-activated"

GOLDEN_ENVELOPE_JSON = json.dumps({
    "event_id": GOLDEN_EVENT_ID,
    "event_type": "matter.activated",
    "occurred_at": "2026-07-29T12:00:00Z",
    "recorded_at": "2026-07-29T12:00:01Z",
    "tenant_id": GOLDEN_TENANT_ID,
    "aggregate_type": "matters",
    "aggregate_id": GOLDEN_MATTER_ID,
    "aggregate_version": 1,
    "actor_type": "RETAINER",
    "actor_id": "00000000-0000-0000-0000-000000000001",
    "authority_class": "FIRM-POLICY",
    "authority_record_id": "00000000-0000-0000-0000-000000000002",
    "policy_version_id": "00000000-0000-0000-0000-000000000003",
    "correlation_id": "corr-abc-123",
    "causation_id": "00000000-0000-0000-0000-000000000004",
    "payload": {
        "matter_id": GOLDEN_MATTER_ID,
        "activation_id": "00000000-0000-0000-0000-000000000005",
        "evidence_manifest_id": "00000000-0000-0000-0000-000000000006",
        "source_matter_candidate_id": "00000000-0000-0000-0000-000000000007",
        "client_party_role_id": "00000000-0000-0000-0000-000000000008",
        "responsible_attorney_assignment_id": "00000000-0000-0000-0000-000000000009",
        "jurisdiction_profile_version_id": "00000000-0000-0000-0000-000000000010",
        "activation_policy_version_id": "00000000-0000-0000-0000-000000000011",
        "engagement_workflow_id": "00000000-0000-0000-0000-000000000012",
        "executed_package_id": "00000000-0000-0000-0000-000000000013",
        "signature_evidence_ids": [
            "00000000-0000-0000-0000-000000000014",
            "00000000-0000-0000-0000-000000000015"
        ],
        "completed_copy_delivery_id": "00000000-0000-0000-0000-000000000016",
        "representation_decision_id": "00000000-0000-0000-0000-000000000017",
        "conflict_clearance_authority_id": "00000000-0000-0000-0000-000000000018",
        "jurisdiction_state": "CA",
        "incident_date": "2026-07-01",
        "sol_urgency": "NORMAL"
    },
    "sensitivity_class": "CONFIDENTIAL",
    "schema_version": "1.0.1"
})


def compute_golden_hmac(
    key_id: str,
    secret: str,
    timestamp: str,
    method: str,
    path: str,
    raw_body: bytes,
) -> str:
    body_hash = hashlib.sha256(raw_body).hexdigest()
    canonical = f"{timestamp}:{method}:{path}:{body_hash}"
    return hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()


GOLDEN_RAW_BODY = GOLDEN_ENVELOPE_JSON.encode("utf-8")
GOLDEN_HMAC = compute_golden_hmac(
    GOLDEN_KEY_ID, GOLDEN_KEY_SECRET, GOLDEN_TIMESTAMP,
    GOLDEN_METHOD, GOLDEN_PATH, GOLDEN_RAW_BODY,
)


class TestGoldenFixture:
    """Cross-repository contract validation for BP-00 frozen contracts."""

    def test_envelope_has_18_fields(self):
        """EventEnvelope v1.0.1 must have exactly 18 fields."""
        fields = [f for f in EventEnvelope.__dataclass_fields__]
        assert len(fields) == 18, f"Expected 18 fields, got {len(fields)}: {fields}"

    def test_schema_version_is_1_0_1(self):
        """Default schema_version must be 1.0.1."""
        envelope = EventEnvelope()
        assert envelope.schema_version == "1.0.1"

    def test_golden_envelope_deserializes(self):
        """The golden fixture must deserialize into a valid EventEnvelope."""
        data = json.loads(GOLDEN_ENVELOPE_JSON)

        assert data["event_id"] == GOLDEN_EVENT_ID
        assert data["event_type"] == "matter.activated"
        assert data["tenant_id"] == GOLDEN_TENANT_ID
        assert data["schema_version"] == "1.0.1"
        assert data["sensitivity_class"] == "CONFIDENTIAL"

        # All 9 evidence references present in payload
        payload = data["payload"]
        assert payload["representation_decision_id"] is not None
        assert payload["conflict_clearance_authority_id"] is not None
        assert payload["engagement_workflow_id"] is not None
        assert payload["executed_package_id"] is not None
        assert len(payload["signature_evidence_ids"]) == 2
        assert payload["completed_copy_delivery_id"] is not None
        assert payload["responsible_attorney_assignment_id"] is not None
        assert payload["jurisdiction_profile_version_id"] is not None
        assert payload["activation_policy_version_id"] is not None

    def test_golden_hmac_is_deterministic(self):
        """Same inputs must produce the same HMAC every time."""
        hmac1 = compute_golden_hmac(
            GOLDEN_KEY_ID, GOLDEN_KEY_SECRET, GOLDEN_TIMESTAMP,
            GOLDEN_METHOD, GOLDEN_PATH, GOLDEN_RAW_BODY,
        )
        hmac2 = compute_golden_hmac(
            GOLDEN_KEY_ID, GOLDEN_KEY_SECRET, GOLDEN_TIMESTAMP,
            GOLDEN_METHOD, GOLDEN_PATH, GOLDEN_RAW_BODY,
        )
        assert hmac1 == hmac2
        assert hmac1 == GOLDEN_HMAC

    def test_golden_hmac_rejects_wrong_body(self):
        """Modified body must produce different HMAC."""
        bad_body = GOLDEN_ENVELOPE_JSON.replace("1.0.1", "1.0.0").encode("utf-8")
        bad_hmac = compute_golden_hmac(
            GOLDEN_KEY_ID, GOLDEN_KEY_SECRET, GOLDEN_TIMESTAMP,
            GOLDEN_METHOD, GOLDEN_PATH, bad_body,
        )
        assert bad_hmac != GOLDEN_HMAC

    def test_golden_hmac_rejects_wrong_path(self):
        """Different path must produce different HMAC."""
        other_hmac = compute_golden_hmac(
            GOLDEN_KEY_ID, GOLDEN_KEY_SECRET, GOLDEN_TIMESTAMP,
            GOLDEN_METHOD, "/api/v1/settle/webhooks/matter-activated", GOLDEN_RAW_BODY,
        )
        assert other_hmac != GOLDEN_HMAC

    def test_webhook_verifier_accepts_golden(self):
        """WebhookVerifier must accept the golden fixture."""
        import os
        os.environ["TRUEVOW_WEBHOOK_KEY_ID"] = GOLDEN_KEY_ID
        os.environ["TRUEVOW_WEBHOOK_SECRET"] = GOLDEN_KEY_SECRET

        from app.shared.webhook_auth import VerifyStatus, WebhookVerifier

        verifier = WebhookVerifier(tolerance_seconds=999999999)
        result = verifier.verify(
            key_id=GOLDEN_KEY_ID,
            timestamp_str=GOLDEN_TIMESTAMP,
            signature=GOLDEN_HMAC,
            method=GOLDEN_METHOD,
            path=GOLDEN_PATH,
            raw_body=GOLDEN_RAW_BODY,
        )
        assert result.status == VerifyStatus.OK, f"Expected OK, got {result.status}: {result.detail}"

    def test_webhook_verifier_rejects_bad_signature(self):
        """WebhookVerifier must reject tampered signatures."""
        import os
        os.environ["TRUEVOW_WEBHOOK_KEY_ID"] = GOLDEN_KEY_ID
        os.environ["TRUEVOW_WEBHOOK_SECRET"] = GOLDEN_KEY_SECRET

        from app.shared.webhook_auth import VerifyStatus, WebhookVerifier

        verifier = WebhookVerifier(tolerance_seconds=999999999)
        result = verifier.verify(
            key_id=GOLDEN_KEY_ID,
            timestamp_str=GOLDEN_TIMESTAMP,
            signature="bad_signature",
            method=GOLDEN_METHOD,
            path=GOLDEN_PATH,
            raw_body=GOLDEN_RAW_BODY,
        )
        assert result.status == VerifyStatus.INVALID_SIGNATURE

    def test_contracts_module_frozen(self):
        """All frozen contracts must be present."""
        from app.shared.contracts import FROZEN_CONTRACTS

        assert "event_envelope" in FROZEN_CONTRACTS
        assert "matter_activated_payload" in FROZEN_CONTRACTS
        assert "webhook_signature" in FROZEN_CONTRACTS
        assert "authority_class_registry" in FROZEN_CONTRACTS
        assert "ontology_registry" in FROZEN_CONTRACTS
        assert FROZEN_CONTRACTS["event_envelope"] == "1.0.1"

    def test_verifier_rejects_missing_headers(self):
        """Must reject when any required header is absent."""
        import os
        os.environ["TRUEVOW_WEBHOOK_KEY_ID"] = GOLDEN_KEY_ID
        os.environ["TRUEVOW_WEBHOOK_SECRET"] = GOLDEN_KEY_SECRET

        from app.shared.webhook_auth import VerifyStatus, WebhookVerifier

        verifier = WebhookVerifier(tolerance_seconds=999999999)

        result = verifier.verify(None, GOLDEN_TIMESTAMP, GOLDEN_HMAC,
                                  GOLDEN_METHOD, GOLDEN_PATH, GOLDEN_RAW_BODY)
        assert result.status == VerifyStatus.MISSING_HEADERS

        result = verifier.verify(GOLDEN_KEY_ID, None, GOLDEN_HMAC,
                                  GOLDEN_METHOD, GOLDEN_PATH, GOLDEN_RAW_BODY)
        assert result.status == VerifyStatus.MISSING_HEADERS

        result = verifier.verify(GOLDEN_KEY_ID, GOLDEN_TIMESTAMP, None,
                                  GOLDEN_METHOD, GOLDEN_PATH, GOLDEN_RAW_BODY)
        assert result.status == VerifyStatus.MISSING_HEADERS

    def test_verifier_rejects_unknown_key(self):
        """Must reject unknown key IDs."""
        import os
        os.environ["TRUEVOW_WEBHOOK_KEY_ID"] = GOLDEN_KEY_ID
        os.environ["TRUEVOW_WEBHOOK_SECRET"] = GOLDEN_KEY_SECRET

        from app.shared.webhook_auth import VerifyStatus, WebhookVerifier

        verifier = WebhookVerifier(tolerance_seconds=999999999)
        result = verifier.verify("unknown_key", GOLDEN_TIMESTAMP, GOLDEN_HMAC,
                                  GOLDEN_METHOD, GOLDEN_PATH, GOLDEN_RAW_BODY)
        assert result.status == VerifyStatus.UNKNOWN_KEY

    def test_verifier_rejects_malformed_timestamp(self):
        """Must reject non-integer timestamps."""
        import os
        os.environ["TRUEVOW_WEBHOOK_KEY_ID"] = GOLDEN_KEY_ID
        os.environ["TRUEVOW_WEBHOOK_SECRET"] = GOLDEN_KEY_SECRET

        from app.shared.webhook_auth import VerifyStatus, WebhookVerifier

        verifier = WebhookVerifier(tolerance_seconds=999999999)
        result = verifier.verify(GOLDEN_KEY_ID, "not_a_number", GOLDEN_HMAC,
                                  GOLDEN_METHOD, GOLDEN_PATH, GOLDEN_RAW_BODY)
        assert result.status == VerifyStatus.INVALID_SIGNATURE

    def test_verifier_rejects_expired_timestamp(self):
        """Must reject timestamps outside tolerance window."""
        import os
        import time
        os.environ["TRUEVOW_WEBHOOK_KEY_ID"] = GOLDEN_KEY_ID
        os.environ["TRUEVOW_WEBHOOK_SECRET"] = GOLDEN_KEY_SECRET

        from app.shared.webhook_auth import VerifyStatus, WebhookVerifier

        verifier = WebhookVerifier(tolerance_seconds=300)
        expired = str(int(time.time() * 1000) - 600_000)  # 10 min ago in ms
        result = verifier.verify(GOLDEN_KEY_ID, expired, GOLDEN_HMAC,
                                  GOLDEN_METHOD, GOLDEN_PATH, GOLDEN_RAW_BODY)
        assert result.status == VerifyStatus.EXPIRED_TIMESTAMP

    def test_verifier_rejects_wrong_method(self):
        """Must reject different HTTP method."""
        import os
        os.environ["TRUEVOW_WEBHOOK_KEY_ID"] = GOLDEN_KEY_ID
        os.environ["TRUEVOW_WEBHOOK_SECRET"] = GOLDEN_KEY_SECRET

        from app.shared.webhook_auth import VerifyStatus, WebhookVerifier

        verifier = WebhookVerifier(tolerance_seconds=999999999)
        result = verifier.verify(GOLDEN_KEY_ID, GOLDEN_TIMESTAMP, GOLDEN_HMAC,
                                  "GET", GOLDEN_PATH, GOLDEN_RAW_BODY)
        assert result.status == VerifyStatus.INVALID_SIGNATURE

    def test_verifier_rejects_trailing_slash(self):
        """Must reject trailing-slash path mismatch."""
        import os
        os.environ["TRUEVOW_WEBHOOK_KEY_ID"] = GOLDEN_KEY_ID
        os.environ["TRUEVOW_WEBHOOK_SECRET"] = GOLDEN_KEY_SECRET

        from app.shared.webhook_auth import VerifyStatus, WebhookVerifier

        verifier = WebhookVerifier(tolerance_seconds=999999999)
        result = verifier.verify(GOLDEN_KEY_ID, GOLDEN_TIMESTAMP, GOLDEN_HMAC,
                                  GOLDEN_METHOD, GOLDEN_PATH + "/", GOLDEN_RAW_BODY)
        assert result.status == VerifyStatus.INVALID_SIGNATURE

    def test_idempotency_rejects_replay(self):
        """is_replay must return True for already-consumed event_id."""
        import os
        os.environ["TRUEVOW_WEBHOOK_KEY_ID"] = GOLDEN_KEY_ID
        os.environ["TRUEVOW_WEBHOOK_SECRET"] = GOLDEN_KEY_SECRET

        from app.shared.webhook_auth import WebhookVerifier

        verifier = WebhookVerifier(tolerance_seconds=999999999)
        assert not verifier.is_replay(GOLDEN_EVENT_ID)
        verifier.mark_consumed(GOLDEN_EVENT_ID)
        assert verifier.is_replay(GOLDEN_EVENT_ID)

    def test_secondary_key_rotation(self):
        """EnvKeyStore must resolve keys from TRUEVOW_WEBHOOK_SECONDARY_KEYS."""
        import os
        import json
        os.environ["TRUEVOW_WEBHOOK_KEY_ID"] = "tv-primary"
        os.environ["TRUEVOW_WEBHOOK_SECRET"] = GOLDEN_KEY_SECRET
        os.environ["TRUEVOW_WEBHOOK_SECONDARY_KEYS"] = json.dumps([
            {"key_id": "tv-secondary", "secret": "secondary-secret-for-testing"}
        ])

        from app.shared.webhook_auth import EnvKeyStore

        store = EnvKeyStore()
        assert store.get_secret("tv-primary") == GOLDEN_KEY_SECRET
        assert store.get_secret("tv-secondary") == "secondary-secret-for-testing"
        assert store.get_secret("unknown-key") is None
