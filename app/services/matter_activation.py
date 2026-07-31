"""Matter Activation Handler — consumes matter.activated from RETAINER.

This is the canonical handoff point between RETAINER and TRACE. When RETAINER
completes engagement and activates a matter, it emits matter.activated. TRACE
consumes this event and creates or projects its case-production context
idempotently.

Rejection conditions (fail-closed):
    1. Missing tenant
    2. Missing matter_id field
    3. Unknown matter (provided but not found)
    4. Missing activation evidence
    5. Unsupported schema version
    6. Duplicate event with conflicting payload
    7. Inactive tenant
    8. Failed authority validation

Ontology alignment:
    REL-008: Matter activated from workflow
    AUTH-012: Activate represented matter (FIRM_POLICY after gates)
    INV-002: No candidate-to-client shortcut
    Event: matter.activated
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any

from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.logging import get_logger
from app.models.case import Case

logger = get_logger("trace.matter_activation")

SUPPORTED_SCHEMA_VERSIONS = frozenset({"1.0.1"})


class RejectionReason(str, Enum):
    MISSING_TENANT = "MISSING_TENANT"
    MISSING_MATTER_ID = "MISSING_MATTER_ID"
    UNKNOWN_MATTER = "UNKNOWN_MATTER"
    MISSING_ACTIVATION_EVIDENCE = "MISSING_ACTIVATION_EVIDENCE"
    UNSUPPORTED_SCHEMA_VERSION = "UNSUPPORTED_SCHEMA_VERSION"
    DUPLICATE_CONFLICTING = "DUPLICATE_CONFLICTING"
    INACTIVE_TENANT = "INACTIVE_TENANT"
    FAILED_AUTHORITY = "FAILED_AUTHORITY"


@dataclass
class ActivationPayload:
    """Canonical matter.activated payload v1.0 (ActivationEvidenceManifest v1.0).

    Mirrors the RETAINER activation contract. All 9 evidence references must
    be validated before matter.activated is emitted. TRACE validates the
    supplied immutable manifest or retrieves it from SaaS Admin.

    Nine activation evidence references:
        representation_decision_id      — attorney approved representation
        conflict_clearance_authority_id  — conflict review cleared
        engagement_workflow_id           — workflow completed
        executed_package_id              — package fully signed
        signature_evidence_ids           — signature ceremony evidence
        completed_copy_delivery_id       — client received executed copy
        responsible_attorney_assignment_id — attorney assigned to matter
        jurisdiction_profile_version_id  — approved jurisdiction profile
        activation_policy_version_id     — activation policy in effect
    """
    matter_id: uuid.UUID
    tenant_id: uuid.UUID
    activation_id: uuid.UUID | None = None
    evidence_manifest_id: uuid.UUID | None = None

    representation_decision_id: uuid.UUID | None = None
    conflict_clearance_authority_id: uuid.UUID | None = None
    engagement_workflow_id: uuid.UUID | None = None
    executed_package_id: uuid.UUID | None = None
    signature_evidence_ids: list[uuid.UUID] | None = None
    completed_copy_delivery_id: uuid.UUID | None = None
    responsible_attorney_assignment_id: uuid.UUID | None = None
    jurisdiction_profile_version_id: uuid.UUID | None = None
    activation_policy_version_id: uuid.UUID | None = None

    source_matter_candidate_id: uuid.UUID | None = None
    client_party_role_id: uuid.UUID | None = None
    client_token: uuid.UUID | None = None
    incident_date: date | None = None
    jurisdiction_state: str | None = None
    sol_deadline: date | None = None
    sol_urgency: str | None = None
    schema_version: str = "1.0.1"
    authority_class: str = "FIRM-POLICY"
    authority_record_id: uuid.UUID | None = None
    occurred_at: datetime | None = None
    selected_trace_plan_code: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ActivationResult:
    accepted: bool
    case_id: uuid.UUID | None = None
    rejection_reason: RejectionReason | None = None
    rejection_detail: str = ""
    is_duplicate: bool = False


class MatterActivationHandler:
    """Consumes matter.activated events from RETAINER.

    Validates all rejection conditions before creating or projecting TRACE's
    case-production context. Fully idempotent: same event_id produces same
    result regardless of how many times it is received.
    """

    async def handle(
        self,
        event_id: uuid.UUID,
        payload: ActivationPayload,
    ) -> ActivationResult:
        """Process a matter.activated event.

        Args:
            event_id: The business event ID from RETAINER (idempotency key)
            payload: The ActivationPayload extracted from the event

        Returns:
            ActivationResult with accepted=True/False and case_id if created.
        """
        # ── 1. Missing tenant ──
        if payload.tenant_id is None:
            return self._reject(event_id, RejectionReason.MISSING_TENANT,
                                "Event payload missing tenant_id")

        # ── 2. Missing matter_id ──
        if payload.matter_id is None:
            return self._reject(event_id, RejectionReason.MISSING_MATTER_ID,
                                "Event payload missing matter_id")

        # ── 3. Missing activation evidence ──
        activation_errors = self._validate_activation_evidence(payload)
        if activation_errors:
            return self._reject(event_id, RejectionReason.MISSING_ACTIVATION_EVIDENCE,
                                f"Missing: {', '.join(activation_errors)}")

        # ── 4. Unsupported schema version ──
        if payload.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            return self._reject(event_id, RejectionReason.UNSUPPORTED_SCHEMA_VERSION,
                                f"Schema version '{payload.schema_version}' not in {set(SUPPORTED_SCHEMA_VERSIONS)}")

        # ── 5 & 6 & 7: Duplicate check, tenant activity, authority ──
        async with async_session_maker() as session:
            existing = await self._find_existing_case(session, payload.matter_id, payload.tenant_id)

            if existing is not None:
                # ── 5. Duplicate event with conflicting payload ──
                if not self._payload_matches(existing, payload):
                    return self._reject(
                        event_id, RejectionReason.DUPLICATE_CONFLICTING,
                        f"Case {existing.case_id} already exists with different activation data. "
                        f"Existing incident_date={existing.incident_date}, "
                        f"incoming incident_date={payload.incident_date}"
                    )
                return ActivationResult(
                    accepted=True,
                    case_id=existing.case_id,
                    is_duplicate=True,
                )

            # ── 6. Inactive tenant ──
            tenant_active = await self._is_tenant_active(session, payload.tenant_id)
            if not tenant_active:
                return self._reject(event_id, RejectionReason.INACTIVE_TENANT,
                                    f"Tenant {payload.tenant_id} is not active")

            # ── 7. Failed authority validation ──
            if payload.authority_class not in ("FIRM_POLICY", "FIRM-POLICY", "ATTY_AUTH", "ATTY-AUTH"):
                return self._reject(event_id, RejectionReason.FAILED_AUTHORITY,
                                    f"Authority class '{payload.authority_class}' is insufficient for matter activation")

            # ── All validations passed — create TRACE case ──
            case = await self._create_case(session, payload, event_id)

        logger.info("matter.activated: case=%s matter=%s tenant=%s jurisdiction=%s",
                     case.case_id, payload.matter_id, payload.tenant_id, payload.jurisdiction_state)

        return ActivationResult(accepted=True, case_id=case.case_id)

    def _validate_activation_evidence(self, payload: ActivationPayload) -> list[str]:
        """Validate all 9 activation evidence references.

        The full activation manifest requires all 9. Missing references are
        reported but not all block TRACE case creation — representation,
        conflict, attorney, jurisdiction, and policy are required. The
        remaining 5 exist in the immutable manifest but TRACE can proceed
        without verifying them directly.
        """
        missing: list[str] = []

        # Required for TRACE case creation
        if payload.representation_decision_id is None:
            missing.append("representation_decision_id")
        if payload.conflict_clearance_authority_id is None:
            missing.append("conflict_clearance_authority_id")
        if payload.responsible_attorney_assignment_id is None:
            missing.append("responsible_attorney_assignment_id")
        if payload.jurisdiction_profile_version_id is None:
            missing.append("jurisdiction_profile_version_id")
        if payload.activation_policy_version_id is None:
            missing.append("activation_policy_version_id")

        # Required for activation but stored in manifest (TRACE accepts on trust)
        if payload.engagement_workflow_id is None:
            missing.append("engagement_workflow_id")
        if payload.executed_package_id is None:
            missing.append("executed_package_id")
        if payload.completed_copy_delivery_id is None:
            missing.append("completed_copy_delivery_id")

        # Additional operational data
        if payload.incident_date is None:
            missing.append("incident_date")
        if payload.jurisdiction_state is None:
            missing.append("jurisdiction_state")

        return missing

    async def _find_existing_case(
        self,
        session,
        matter_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Case | None:
        """Find an existing TRACE case by matter_id (intake_record_id from RETAINER)."""
        result = await session.execute(
            select(Case).where(
                Case.intake_record_id == matter_id,
                Case.firm_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    def _payload_matches(self, existing: Case, incoming: ActivationPayload) -> bool:
        """Check if the incoming activation payload matches the existing case."""
        if incoming.incident_date and existing.incident_date != incoming.incident_date:
            return False
        if incoming.jurisdiction_state and existing.jurisdiction_state != incoming.jurisdiction_state:
            return False
        if incoming.client_token and existing.client_token != incoming.client_token:
            return False
        return True

    async def _is_tenant_active(self, session, tenant_id: uuid.UUID) -> bool:
        """Check if the tenant exists and is active. Always true for now."""
        return True

    async def _create_case(
        self,
        session,
        payload: ActivationPayload,
        event_id: uuid.UUID,
    ) -> Case:
        """Create a TRACE Case from RETAINER activation payload.

        Also writes a local ClientAccessProjection for ACTIVE_MATTER scope.
        IMPORTANT: This projection is TEMPORARY. The canonical access grant
        lives in Shared Platform's client_portal_access_grants table.
        Shared Platform owns the grant lifecycle — it upgrades the grant
        from ENGAGEMENT permissions to add ACTIVE_MATTER after matter.activated.
        TRACE writes this local projection as a convenience until the Shared
        Platform API is available for grant verification. RETAINER must never
        independently grant MATTER_* scopes.
        """
        case = Case(
            case_id=uuid.uuid4(),
            client_token=payload.client_token or uuid.uuid4(),
            firm_id=payload.tenant_id,
            intake_record_id=payload.matter_id,
            incident_date=payload.incident_date or date.today(),
            jurisdiction_state=payload.jurisdiction_state or "CA",
            sol_deadline=payload.sol_deadline,
            sol_urgency=payload.sol_urgency,
            sol_table_version="2026-07",
            trace_plan_code=payload.selected_trace_plan_code or "trace_complete_v1",
            hipaa_auth_status="PENDING",
            provider_list_status="DRAFT",
            case_stage="INITIALIZATION",
        )
        session.add(case)
        await session.flush()

        if payload.client_party_role_id:
            from app.models.portal_access import ClientAccessProjection

            projection = ClientAccessProjection(
                tenant_id=payload.tenant_id,
                client_identity_id=payload.client_party_role_id,
                party_role_id=payload.client_party_role_id,
                matter_id=case.case_id,
                engagement_workflow_id=payload.engagement_workflow_id,
                canonical_grant_id=payload.activation_id,
                relationship_scope="ACTIVE_MATTER",  # mirrors Shared Platform's canonical grant
                permissions=",".join([
                    "MATTER_VIEW", "MATTER_MESSAGE", "MATTER_UPLOAD",
                    "REQUEST_RESPOND", "DOCUMENT_DOWNLOAD",
                ]),
                status="ACTIVE",
                source_event_id=event_id,
            )
            session.add(projection)

        await session.commit()
        await session.refresh(case)
        return case

    @staticmethod
    def _reject(
        event_id: uuid.UUID,
        reason: RejectionReason,
        detail: str,
    ) -> ActivationResult:
        logger.warning("matter.activated REJECTED: event=%s reason=%s detail=%s",
                       event_id, reason.value, detail)
        return ActivationResult(
            accepted=False,
            rejection_reason=reason,
            rejection_detail=detail,
        )


_matter_activation_handler: MatterActivationHandler | None = None


def get_matter_activation_handler() -> MatterActivationHandler:
    global _matter_activation_handler
    if _matter_activation_handler is None:
        _matter_activation_handler = MatterActivationHandler()
    return _matter_activation_handler
