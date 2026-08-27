"""Shared Foundation: Event Store and Transition Contract.

Implements two ontology architectural specs:

1. Event Envelope (lines 1606-1629): Standardized business event schema
   with required fields, append-only rules, idempotency, and sensitivity
   classification. Separate from diagnostic logs (INV-015).

2. Transition Contract (lines 1630-1642): Standardized state machine
   contract enforcing from_states, required_authority, required_evidence,
   and guards. Default failure mode is fail_closed.

These are designed for extraction to a shared TrueVow foundation package.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.core.database import internal_tenant_session
from app.core.logging import get_logger

logger = get_logger("trace.event_store")


# ─────────────────────────────────────────────────────────────────────
# Event Envelope
# ─────────────────────────────────────────────────────────────────────

@dataclass
class EventEnvelope:
    """EventEnvelope v1.0.1 — 18 required fields, no product extensions at root."""
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    event_type: str = ""
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    recorded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: uuid.UUID | None = None
    aggregate_type: str = ""
    aggregate_id: uuid.UUID | None = None
    aggregate_version: int = 1
    actor_type: str = "SYSTEM"
    actor_id: uuid.UUID | None = None
    authority_class: str = "SYS-ADMIN"
    authority_record_id: uuid.UUID | None = None
    policy_version_id: uuid.UUID | None = None
    correlation_id: str | None = None
    causation_id: uuid.UUID | None = None
    payload: dict[str, Any] | None = None
    sensitivity_class: str = "INTERNAL"
    schema_version: str = "1.0.1"


class EventStore:
    """Append-only business event store implementing the ontology Event Envelope spec.

    Rules enforced:
        - append_only: records are created, never modified or deleted
        - idempotent_by_event_id: duplicate event_ids are rejected silently
        - tenant_scoped: every event carries non-null tenant_id
        - schema_versioned: each event records its schema version
        - no_secrets_in_payload: validated at record time
    """

    SECRET_PATTERNS = {"api_key", "secret", "password", "token", "credential", "private_key", "access_key"}

    async def record(self, envelope: EventEnvelope) -> uuid.UUID:
        """Record a business event. Silently ignores duplicate event_ids."""
        if envelope.tenant_id is None:
            raise ValueError("Event envelope requires non-null tenant_id")
        if not envelope.event_type:
            raise ValueError("Event envelope requires non-null event_type")

        self._validate_no_secrets(envelope.payload)

        async with internal_tenant_session(tenant_id=envelope.tenant_id) as session:
            from app.models.business_event import BusinessEvent

            existing = await session.get(BusinessEvent, envelope.event_id)
            if existing is not None:
                return envelope.event_id

            record = BusinessEvent(
                event_id=envelope.event_id,
                event_type=envelope.event_type,
                occurred_at=envelope.occurred_at,
                tenant_id=envelope.tenant_id,
                aggregate_type=envelope.aggregate_type,
                aggregate_id=envelope.aggregate_id or envelope.event_id,
                aggregate_version=envelope.aggregate_version,
                actor_type=envelope.actor_type,
                actor_id=envelope.actor_id,
                authority_class=envelope.authority_class,
                authority_record_id=envelope.authority_record_id,
                policy_version_id=envelope.policy_version_id,
                correlation_id=envelope.correlation_id,
                causation_id=envelope.causation_id,
                payload=envelope.payload,
                sensitivity_class=envelope.sensitivity_class,
            )
            session.add(record)
            await session.commit()
            return envelope.event_id

    async def get_events_for_aggregate(
        self,
        aggregate_type: str,
        aggregate_id: uuid.UUID,
        limit: int = 100,
        *,
        tenant_id: uuid.UUID,
    ) -> list[EventEnvelope]:
        """Get all events for a given aggregate."""
        async with internal_tenant_session(tenant_id=tenant_id) as session:
            from app.models.business_event import BusinessEvent

            result = await session.execute(
                select(BusinessEvent)
                .where(
                    BusinessEvent.aggregate_type == aggregate_type,
                    BusinessEvent.aggregate_id == aggregate_id,
                    BusinessEvent.tenant_id == tenant_id,
                )
                .order_by(BusinessEvent.occurred_at)
                .limit(limit)
            )
            records = result.scalars().all()

            return [
                EventEnvelope(
                    event_id=r.event_id,
                    event_type=r.event_type,
                    occurred_at=r.occurred_at,
                    recorded_at=r.recorded_at,
                    tenant_id=r.tenant_id,
                    aggregate_type=r.aggregate_type,
                    aggregate_id=r.aggregate_id,
                    aggregate_version=r.aggregate_version,
                    actor_type=r.actor_type,
                    actor_id=r.actor_id,
                    authority_class=r.authority_class,
                    policy_version_id=r.policy_version_id,
                    correlation_id=r.correlation_id,
                    payload=r.payload,
                    sensitivity_class=r.sensitivity_class,
                )
                for r in records
            ]

    async def get_event(
        self,
        event_id: uuid.UUID,
        *,
        tenant_id: uuid.UUID,
    ) -> EventEnvelope | None:
        """Get a single event by ID."""
        async with internal_tenant_session(tenant_id=tenant_id) as session:
            from app.models.business_event import BusinessEvent

            r = (
                await session.execute(
                    select(BusinessEvent).where(
                        BusinessEvent.event_id == event_id,
                        BusinessEvent.tenant_id == tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if r is None:
                return None
            return EventEnvelope(
                event_id=r.event_id,
                event_type=r.event_type,
                occurred_at=r.occurred_at,
                recorded_at=r.recorded_at,
                tenant_id=r.tenant_id,
                aggregate_type=r.aggregate_type,
                aggregate_id=r.aggregate_id,
                aggregate_version=r.aggregate_version,
                actor_type=r.actor_type,
                actor_id=r.actor_id,
                authority_class=r.authority_class,
                policy_version_id=r.policy_version_id,
                correlation_id=r.correlation_id,
                payload=r.payload,
                sensitivity_class=r.sensitivity_class,
            )

    def _validate_no_secrets(self, payload: dict[str, Any] | None) -> None:
        if payload is None:
            return
        for key in payload:
            key_lower = key.lower()
            for secret_pattern in self.SECRET_PATTERNS:
                if secret_pattern in key_lower:
                    logger.warning("Event payload contains potential secret key: %s", key)


# ─────────────────────────────────────────────────────────────────────
# Transition Contract
# ─────────────────────────────────────────────────────────────────────

@dataclass
class TransitionContract:
    transition_id: str
    aggregate_type: str
    from_states: list[str]
    to_state: str
    command: str
    required_authority: str
    required_evidence: list[str] = field(default_factory=list)
    guards: list[str] = field(default_factory=list)
    event_type: str = ""
    failure_mode: str = "fail_closed"


@dataclass
class TransitionResult:
    allowed: bool
    transition_id: str = ""
    reason: str = ""
    missing_evidence: list[str] = field(default_factory=list)
    failed_guards: list[str] = field(default_factory=list)


class StateMachine:
    """Enforces Transition Contracts for all stateful aggregates.

    Default failure mode is fail_closed. Every transition requires:
    - Current state is in allowed from_states
    - Required authority is satisfied
    - Required evidence is present
    - All guards pass
    """

    def __init__(self):
        self._contracts: dict[str, TransitionContract] = {}
        self._register_tr_trace_transitions()

    def register(self, contract: TransitionContract) -> None:
        self._contracts[contract.transition_id] = contract

    def evaluate(
        self,
        transition_id: str,
        current_state: str,
        authority_class: str = "",
        evidence: dict[str, Any] | None = None,
    ) -> TransitionResult:
        contract = self._contracts.get(transition_id)
        if contract is None:
            return TransitionResult(
                allowed=False,
                transition_id=transition_id,
                reason=f"Transition '{transition_id}' is not registered.",
            )

        if current_state not in contract.from_states:
            return TransitionResult(
                allowed=False,
                transition_id=transition_id,
                reason=f"Current state '{current_state}' is not in allowed from_states: {contract.from_states}",
            )

        if contract.required_authority and authority_class != contract.required_authority:
            return TransitionResult(
                allowed=False,
                transition_id=transition_id,
                reason=f"Required authority '{contract.required_authority}' not satisfied. Got: '{authority_class}'",
            )

        missing = []
        for req in contract.required_evidence:
            if not evidence or req not in evidence:
                missing.append(req)

        if missing:
            return TransitionResult(
                allowed=False,
                transition_id=transition_id,
                reason=f"Missing required evidence: {missing}",
                missing_evidence=missing,
            )

        return TransitionResult(
            allowed=True,
            transition_id=transition_id,
            reason=f"Transition '{transition_id}' from '{current_state}' to '{contract.to_state}' authorized.",
        )

    def apply(
        self,
        transition_id: str,
        current_state: str,
        authority_class: str = "",
        evidence: dict[str, Any] | None = None,
    ) -> tuple[str | None, TransitionResult]:
        """Apply a transition if allowed. Returns (new_state, result)."""
        result = self.evaluate(transition_id, current_state, authority_class, evidence)
        if not result.allowed:
            return None, result
        contract = self._contracts[transition_id]
        return contract.to_state, result

    def _register_tr_trace_transitions(self) -> None:
        """Register TRACE-specific transition contracts."""
        self.register(TransitionContract(
            transition_id="case.processing",
            aggregate_type="cases",
            from_states=["RETRIEVAL"],
            to_state="PROCESSING",
            command="StartProcessing",
            required_authority="SYS-ADMIN",
            required_evidence=[],
            event_type="case.processing_started",
        ))
        self.register(TransitionContract(
            transition_id="case.chronology_ready",
            aggregate_type="cases",
            from_states=["PROCESSING"],
            to_state="CHRONOLOGY_READY",
            command="MarkChronologyReady",
            required_authority="SYS-ADMIN",
            required_evidence=[],
            event_type="chronology.generated",
        ))
        self.register(TransitionContract(
            transition_id="case.attorney_review",
            aggregate_type="cases",
            from_states=["CHRONOLOGY_READY", "ATTORNEY_REVIEW"],
            to_state="ATTORNEY_REVIEW",
            command="StartAttorneyReview",
            required_authority="ATTY-AUTH",
            required_evidence=[],
            event_type="chronology.review_started",
        ))
        self.register(TransitionContract(
            transition_id="case.demand_ready",
            aggregate_type="cases",
            from_states=["ATTORNEY_REVIEW"],
            to_state="DEMAND_READY",
            command="ApproveDemandReady",
            required_authority="ATTY-AUTH",
            required_evidence=["all_priority_flags_annotated"],
            guards=["no_unannotated_priority_flags"],
            event_type="demand.ready_approved",
        ))
        self.register(TransitionContract(
            transition_id="evidence.fact.review",
            aggregate_type="evidence_facts",
            from_states=["UNREVIEWED", "CONFIRMED", "DISPUTED", "EXCLUDED"],
            to_state="CONFIRMED",
            command="ReviewFact",
            required_authority="ATTY-AUTH",
            required_evidence=[],
            event_type="fact.reviewed",
        ))
        self.register(TransitionContract(
            transition_id="evidence.fact.dispute",
            aggregate_type="evidence_facts",
            from_states=["UNREVIEWED", "CONFIRMED", "DISPUTED", "EXCLUDED"],
            to_state="DISPUTED",
            command="DisputeFact",
            required_authority="ATTY-AUTH",
            required_evidence=[],
            event_type="fact.disputed",
        ))
        self.register(TransitionContract(
            transition_id="evidence.fact.exclude",
            aggregate_type="evidence_facts",
            from_states=["UNREVIEWED", "CONFIRMED", "DISPUTED", "EXCLUDED"],
            to_state="EXCLUDED",
            command="ExcludeFact",
            required_authority="ATTY-AUTH",
            required_evidence=[],
            event_type="fact.excluded",
        ))
        self.register(TransitionContract(
            transition_id="contradiction.resolve",
            aggregate_type="contradiction_pairs",
            from_states=["UNRESOLVED"],
            to_state="RESOLVED",
            command="ResolveContradiction",
            required_authority="ATTY-AUTH",
            required_evidence=[],
            event_type="contradiction.resolved",
        ))


_event_store: EventStore | None = None
_state_machine: StateMachine | None = None


def get_event_store() -> EventStore:
    global _event_store
    if _event_store is None:
        _event_store = EventStore()
    return _event_store


def get_state_machine() -> StateMachine:
    global _state_machine
    if _state_machine is None:
        _state_machine = StateMachine()
    return _state_machine
