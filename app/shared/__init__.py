"""Shared Foundation — TrueVow platform services.

Designed for extraction to a shared TrueVow foundation package when the
ecosystem supports cross-service Python imports.

Global Platform Reference Data (immutable, not tenant-scoped):
    AuthorityClass, ActorRole, DECISION_REGISTRY, ROLE_AUTHORITY_MAP —
    these are canonical ontology definitions that do not carry tenant_id.
    They are maintained as module-level constants and versioned with the
    platform release. Tenants cannot modify or duplicate them.

Tenant-Scoped Data (every record carries non-null tenant_id):
    PolicyRecord, ConsentRecord, BusinessEvent, Case, etc. —
    these are firm-specific operational data. Every record is tenant-
    isolated at the application level and (in Postgres) via RLS.

Services:
    AuthorityGate   — Enforces the Decision Authority Registry (AUTH-001 to AUTH-020)
    ConsentLedger   — Append-only consent event store (HIPAA, e-sign, SMS, recording)
    PolicyRegistry  — Versioned tenant policy and jurisdiction profile store
    EventStore      — Append-only business event store (EventEnvelope v1.0.1, 18 fields)
    StateMachine    — Transition Contract enforcement (fail_closed default)
    WebhookVerifier — HMAC-SHA256 webhook authentication (X-TrueVow headers)
"""

from app.shared.authority_gate import (
    ActorRole,
    AuthorityClass,
    AuthorityGate,
    DECISION_REGISTRY,
    GateResult,
    ROLE_AUTHORITY_MAP,
    get_authority_gate,
)
from app.shared.consent_ledger import (
    ConsentEvent,
    ConsentLedger,
    ConsentState,
    ConsentType,
    get_consent_ledger,
)
from app.shared.event_store import (
    EventEnvelope,
    EventStore,
    StateMachine,
    TransitionContract,
    TransitionResult,
    get_event_store,
    get_state_machine,
)
from app.shared.policy_registry import (
    PolicyReference,
    PolicyRegistry,
    get_policy_registry,
)

from app.shared.webhook_auth import (
    VerifyResult,
    VerifyStatus,
    WebhookVerifier,
    get_webhook_verifier,
)

__all__ = [
    "ActorRole",
    "AuthorityClass",
    "AuthorityGate",
    "ConsentEvent",
    "ConsentLedger",
    "ConsentState",
    "ConsentType",
    "DECISION_REGISTRY",
    "EventEnvelope",
    "EventStore",
    "GateResult",
    "PolicyReference",
    "PolicyRegistry",
    "ROLE_AUTHORITY_MAP",
    "StateMachine",
    "TransitionContract",
    "TransitionResult",
    "VerifyResult",
    "VerifyStatus",
    "WebhookVerifier",
    "get_authority_gate",
    "get_consent_ledger",
    "get_event_store",
    "get_policy_registry",
    "get_state_machine",
    "get_webhook_verifier",
]
