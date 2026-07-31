"""Shared Foundation: Authority Gate Service.

Prevents software from performing attorney- or client-only actions. This is
the enforcement layer for the TrueVow Decision Authority Registry (AUTH-001
through AUTH-020). Every material action must pass through the Authority Gate
before execution.

Global Platform Reference Data:
    This entire module is global canonical reference data from the ontology.
    AuthorityClass, ActorRole, DECISION_REGISTRY, and ROLE_AUTHORITY_MAP are
    immutable platform definitions — not tenant-scoped and not tenant-modifiable.
    Tenants cannot add, remove, or modify authority classes or the decision
    registry. Jurisdiction-specific overrides are stored in PolicyRecord
    (tenant-scoped, versioned) and referenced at evaluation time.

Architecture:
    Actor -> Action -> Authority Gate -> PASS (execute) / FAIL (block + audit)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AuthorityClass(str, Enum):
    SYS_ADMIN = "SYS-ADMIN"
    FIRM_POLICY = "FIRM-POLICY"
    STAFF_AUTH = "STAFF-AUTH"
    ATTY_AUTH = "ATTY-AUTH"
    CLIENT_AUTH = "CLIENT-AUTH"
    PROHIBITED = "PROHIBITED"


class ActorRole(str, Enum):
    SYSTEM = "system"
    ADMIN = "admin"
    INTAKE_COORDINATOR = "intake_coordinator"
    LEGAL_ASSISTANT = "legal_assistant"
    CASE_MANAGER = "case_manager"
    PARALEGAL = "paralegal"
    ATTORNEY = "attorney"
    SUPERVISING_ATTORNEY = "supervising_attorney"
    MANAGING_ATTORNEY = "managing_attorney"
    FIRM_ADMINISTRATOR = "firm_administrator"
    CLIENT = "client"
    PROSPECTIVE_CLIENT = "prospective_client"


@dataclass
class GateResult:
    allowed: bool
    reason: str = ""
    required_authority: AuthorityClass = AuthorityClass.PROHIBITED
    action: str = ""
    actor_id: str = ""
    actor_role: str = ""
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ── Decision Authority Registry ──
# Machine-readable registry for every product action per the ontology.
# Format: action -> (required_authority, platform_role, description, failure_reason)

DECISION_REGISTRY: dict[str, dict[str, Any]] = {
    # ── INTAKE ──
    "intake.collect_factual_info": {
        "authority": AuthorityClass.FIRM_POLICY,
        "description": "Collect factual intake information",
        "domain": "INTAKE",
    },
    "intake.classify_practice_area": {
        "authority": AuthorityClass.FIRM_POLICY,
        "description": "Classify practice area or matter type (routing, not advice)",
        "domain": "INTAKE",
    },

    # ── RETAINER ──
    "retainer.run_conflict_search": {
        "authority": AuthorityClass.FIRM_POLICY,
        "description": "Run name-based conflict search",
        "domain": "RETAINER",
    },
    "retainer.clear_conflict": {
        "authority": AuthorityClass.ATTY_AUTH,
        "description": "Clear a potential conflict",
        "domain": "RETAINER",
    },
    "retainer.approve_representation": {
        "authority": AuthorityClass.ATTY_AUTH,
        "description": "Approve representation",
        "domain": "RETAINER",
    },
    "retainer.decline_representation": {
        "authority": AuthorityClass.ATTY_AUTH,
        "description": "Decline representation",
        "domain": "RETAINER",
    },
    "retainer.select_template": {
        "authority": AuthorityClass.FIRM_POLICY,
        "description": "Select approved template by rules",
        "domain": "RETAINER",
    },
    "retainer.create_legal_terms": {
        "authority": AuthorityClass.ATTY_AUTH,
        "description": "Create or modify substantive legal terms",
        "domain": "RETAINER",
    },
    "retainer.explain_legal_effect": {
        "authority": AuthorityClass.ATTY_AUTH,
        "description": "Explain legal effect or scope",
        "domain": "RETAINER",
    },
    "retainer.deliver_engagement_package": {
        "authority": AuthorityClass.FIRM_POLICY,
        "description": "Deliver approved engagement package",
        "domain": "RETAINER",
    },
    "retainer.consent_electronic_transaction": {
        "authority": AuthorityClass.CLIENT_AUTH,
        "description": "Consent to electronic transaction",
        "domain": "RETAINER",
    },
    "retainer.sign_for_client": {
        "authority": AuthorityClass.CLIENT_AUTH,
        "description": "Sign for client (representative capacity must be verified)",
        "domain": "RETAINER",
    },
    "retainer.activate_matter": {
        "authority": AuthorityClass.FIRM_POLICY,
        "description": "Activate represented matter after gates",
        "domain": "RETAINER",
    },

    # ── TRACE ──
    "trace.extract_facts": {
        "authority": AuthorityClass.SYS_ADMIN,
        "description": "Extract facts from medical records (automated NER)",
        "domain": "TRACE",
    },
    "trace.detect_contradictions": {
        "authority": AuthorityClass.SYS_ADMIN,
        "description": "Detect contradictions between facts (automated)",
        "domain": "TRACE",
    },
    "trace.generate_missing_evidence_signals": {
        "authority": AuthorityClass.SYS_ADMIN,
        "description": "Generate missing-evidence signals (automated)",
        "domain": "TRACE",
    },
    "trace.raise_risk_flag": {
        "authority": AuthorityClass.SYS_ADMIN,
        "description": "Raise deterministic or NLP risk flag",
        "domain": "TRACE",
    },
    "trace.state_deadline_conclusion": {
        "authority": AuthorityClass.ATTY_AUTH,
        "description": "State deadline or limitation conclusion",
        "domain": "TRACE",
    },
    "trace.build_chronology": {
        "authority": AuthorityClass.SYS_ADMIN,
        "description": "Assemble chronology from source-linked facts",
        "domain": "TRACE",
    },
    "trace.review_fact": {
        "authority": AuthorityClass.ATTY_AUTH,
        "description": "Review, confirm, dispute, or exclude a fact",
        "domain": "TRACE",
    },
    "trace.edit_fact_text": {
        "authority": AuthorityClass.ATTY_AUTH,
        "description": "Edit fact text, date, type, or provider",
        "domain": "TRACE",
    },
    "trace.resolve_contradiction": {
        "authority": AuthorityClass.ATTY_AUTH,
        "description": "Resolve a contradiction pair",
        "domain": "TRACE",
    },
    "trace.annotate_flag": {
        "authority": AuthorityClass.ATTY_AUTH,
        "description": "Annotate a risk flag",
        "domain": "TRACE",
    },
    "trace.authorize_demand": {
        "authority": AuthorityClass.ATTY_AUTH,
        "description": "Authorize demand transmission",
        "domain": "TRACE",
    },
    "trace.transmit_demand": {
        "authority": AuthorityClass.FIRM_POLICY,
        "description": "Transmit authorized demand package",
        "domain": "TRACE",
    },
    "trace.export_chronology": {
        "authority": AuthorityClass.ATTY_AUTH,
        "description": "Export demand-ready chronology",
        "domain": "TRACE",
    },
    "trace.approve_demand_ready": {
        "authority": AuthorityClass.ATTY_AUTH,
        "description": "Approve chronology as demand-ready",
        "domain": "TRACE",
    },

    # ── SETTLE ──
    "settle.recommend_settlement": {
        "authority": AuthorityClass.ATTY_AUTH,
        "description": "Provide settlement recommendation",
        "domain": "SETTLE",
    },
    "settle.accept_settlement": {
        "authority": AuthorityClass.CLIENT_AUTH,
        "description": "Accept settlement (client decision)",
        "domain": "SETTLE",
    },
    "settle.reject_settlement": {
        "authority": AuthorityClass.CLIENT_AUTH,
        "description": "Reject settlement (client decision)",
        "domain": "SETTLE",
    },
    "settle.counter_settlement": {
        "authority": AuthorityClass.CLIENT_AUTH,
        "description": "Counter settlement (client decision)",
        "domain": "SETTLE",
    },
    "settle.approve_lien_resolution": {
        "authority": AuthorityClass.ATTY_AUTH,
        "description": "Approve lien resolution",
        "domain": "SETTLE",
    },
    "settle.approve_allocation": {
        "authority": AuthorityClass.ATTY_AUTH,
        "description": "Approve settlement allocation",
        "domain": "SETTLE",
    },
    "settle.disburse_trust_funds": {
        "authority": AuthorityClass.STAFF_AUTH,
        "description": "Disburse trust funds (authorized firm user only)",
        "domain": "SETTLE",
    },

    # ── COMMAND ──
    "command.view_metrics": {
        "authority": AuthorityClass.FIRM_POLICY,
        "description": "View operational metrics",
        "domain": "COMMAND",
    },
    "command.manage_users": {
        "authority": AuthorityClass.STAFF_AUTH,
        "description": "Manage user accounts and roles",
        "domain": "COMMAND",
    },

    # ── CROSS-CUTTING ──
    "delete.confidential_matter_data": {
        "authority": AuthorityClass.FIRM_POLICY,
        "description": "Delete confidential matter data (after retention/legal-hold gates)",
        "domain": "PLATFORM",
    },
    "system.override_policy": {
        "authority": AuthorityClass.ATTY_AUTH,
        "description": "Override an automated policy decision",
        "domain": "PLATFORM",
    },
}


# ── Role -> Authority Class Mapping ──
# Defines which actor roles can satisfy which authority requirements.

ROLE_AUTHORITY_MAP: dict[ActorRole, set[AuthorityClass]] = {
    ActorRole.SYSTEM: {AuthorityClass.SYS_ADMIN},
    ActorRole.ADMIN: {AuthorityClass.SYS_ADMIN},
    ActorRole.INTAKE_COORDINATOR: {AuthorityClass.SYS_ADMIN, AuthorityClass.FIRM_POLICY},
    ActorRole.LEGAL_ASSISTANT: {AuthorityClass.SYS_ADMIN, AuthorityClass.FIRM_POLICY},
    ActorRole.CASE_MANAGER: {AuthorityClass.SYS_ADMIN, AuthorityClass.FIRM_POLICY, AuthorityClass.STAFF_AUTH},
    ActorRole.PARALEGAL: {AuthorityClass.SYS_ADMIN, AuthorityClass.FIRM_POLICY, AuthorityClass.STAFF_AUTH},
    ActorRole.ATTORNEY: {AuthorityClass.SYS_ADMIN, AuthorityClass.FIRM_POLICY, AuthorityClass.STAFF_AUTH, AuthorityClass.ATTY_AUTH},
    ActorRole.SUPERVISING_ATTORNEY: {AuthorityClass.SYS_ADMIN, AuthorityClass.FIRM_POLICY, AuthorityClass.STAFF_AUTH, AuthorityClass.ATTY_AUTH},
    ActorRole.MANAGING_ATTORNEY: {AuthorityClass.SYS_ADMIN, AuthorityClass.FIRM_POLICY, AuthorityClass.STAFF_AUTH, AuthorityClass.ATTY_AUTH},
    ActorRole.FIRM_ADMINISTRATOR: {AuthorityClass.SYS_ADMIN, AuthorityClass.FIRM_POLICY},
    ActorRole.CLIENT: {AuthorityClass.CLIENT_AUTH},
    ActorRole.PROSPECTIVE_CLIENT: {AuthorityClass.CLIENT_AUTH},
}


class AuthorityGate:
    """Enforces the decision authority registry.

    Every material action must call `evaluate()` before execution.
    Fail-closed: unknown or unregistered actions are PROHIBITED by default.
    """

    def __init__(self, registry: dict[str, dict[str, Any]] | None = None):
        self._registry = registry or DECISION_REGISTRY

    def evaluate(
        self,
        action: str,
        actor_role: ActorRole,
        actor_id: uuid.UUID | str | None = None,
        policy_version: str | None = None,
        tenant_id: uuid.UUID | None = None,
    ) -> GateResult:
        """Evaluate whether an actor may perform an action.

        Args:
            action: The action identifier (e.g. "trace.review_fact")
            actor_role: The actor's role
            actor_id: The actor's UUID (for audit)
            policy_version: The applicable policy version (for FIRM_POLICY actions)
            tenant_id: The tenant UUID

        Returns:
            GateResult with allowed=True/False and detailed reason.
        """
        actor_id_str = str(actor_id) if actor_id else "unknown"

        rule = self._registry.get(action)
        if rule is None:
            return GateResult(
                allowed=False,
                reason=f"Action '{action}' is not registered in the decision authority registry. "
                        "All material actions must be explicitly authorized.",
                required_authority=AuthorityClass.PROHIBITED,
                action=action,
                actor_id=actor_id_str,
                actor_role=actor_role.value,
            )

        required = rule["authority"]

        if required == AuthorityClass.PROHIBITED:
            return GateResult(
                allowed=False,
                reason=f"Action '{action}' is PROHIBITED. This platform must not perform it. "
                        f"Rule: {rule['description']}",
                required_authority=required,
                action=action,
                actor_id=actor_id_str,
                actor_role=actor_role.value,
            )

        if actor_role not in ROLE_AUTHORITY_MAP:
            return GateResult(
                allowed=False,
                reason=f"Actor role '{actor_role.value}' is not recognized. Cannot authorize any action.",
                required_authority=required,
                action=action,
                actor_id=actor_id_str,
                actor_role=actor_role.value,
            )

        actor_authorities = ROLE_AUTHORITY_MAP[actor_role]

        if required not in actor_authorities:
            return GateResult(
                allowed=False,
                reason=f"Actor '{actor_id_str}' with role '{actor_role.value}' lacks authority for action "
                        f"'{action}'. Required: {required.value}. "
                        f"Actor can satisfy: {', '.join(a.value for a in actor_authorities)}.",
                required_authority=required,
                action=action,
                actor_id=actor_id_str,
                actor_role=actor_role.value,
            )

        if required == AuthorityClass.FIRM_POLICY and policy_version is None:
            return GateResult(
                allowed=False,
                reason=f"Action '{action}' requires FIRM_POLICY authority but no policy version was provided. "
                        "Every FIRM_POLICY action must reference an approved policy.",
                required_authority=required,
                action=action,
                actor_id=actor_id_str,
                actor_role=actor_role.value,
            )

        return GateResult(
            allowed=True,
            reason=f"Action '{action}' authorized. Actor: {actor_id_str} ({actor_role.value}), "
                   f"Required: {required.value}",
            required_authority=required,
            action=action,
            actor_id=actor_id_str,
            actor_role=actor_role.value,
        )

    def list_actions_for_role(self, actor_role: ActorRole) -> list[str]:
        """List all actions an actor role is authorized to perform."""
        if actor_role not in ROLE_AUTHORITY_MAP:
            return []
        authorities = ROLE_AUTHORITY_MAP[actor_role]
        return [
            action for action, rule in self._registry.items()
            if rule["authority"] in authorities
        ]

    def list_actions_by_domain(self, domain: str) -> list[dict[str, Any]]:
        """List all actions for a given product domain."""
        return [
            {"action": action, **rule}
            for action, rule in self._registry.items()
            if rule.get("domain") == domain
        ]


_authority_gate: AuthorityGate | None = None


def get_authority_gate() -> AuthorityGate:
    global _authority_gate
    if _authority_gate is None:
        _authority_gate = AuthorityGate()
    return _authority_gate
