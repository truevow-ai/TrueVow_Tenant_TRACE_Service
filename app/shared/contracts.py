"""Frozen Contract Versions — canonical version constants for cross-service contracts.

Each contract version is frozen here. Incompatible changes require a new
version constant and a corresponding test fixture update. Fields in existing
versions must not be renamed in place.

Frozen contracts (BP-00):
    EventEnvelope             v1.0.1
    MatterActivatedPayload    v1.0
    ActivationEvidenceManifest v1.0
    WebhookSignature          v1.0
    AuthorityClass Registry   v1.0
    Ontology Registry         v1.0
"""

EVENT_ENVELOPE_VERSION = "1.0.1"
MATTER_ACTIVATED_PAYLOAD_VERSION = "1.0"
ACTIVATION_EVIDENCE_MANIFEST_VERSION = "1.0"
WEBHOOK_SIGNATURE_VERSION = "1.0"
AUTHORITY_CLASS_REGISTRY_VERSION = "1.0"
ONTOLOGY_REGISTRY_VERSION = "1.0"

FROZEN_CONTRACTS: dict[str, str] = {
    "event_envelope": EVENT_ENVELOPE_VERSION,
    "matter_activated_payload": MATTER_ACTIVATED_PAYLOAD_VERSION,
    "activation_evidence_manifest": ACTIVATION_EVIDENCE_MANIFEST_VERSION,
    "webhook_signature": WEBHOOK_SIGNATURE_VERSION,
    "authority_class_registry": AUTHORITY_CLASS_REGISTRY_VERSION,
    "ontology_registry": ONTOLOGY_REGISTRY_VERSION,
}
