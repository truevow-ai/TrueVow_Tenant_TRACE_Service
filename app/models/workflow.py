"""Demand Package, Issue, Readiness Assessment — attorney review workflow models.

Ontology alignment:
    ENT-077 Issue — question or problem requiring investigation or judgment
    ENT-080 ReadinessAssessment — review of defined prerequisites
    ENT-081 DemandPackage — versioned set of demand materials
    ENT-082 DemandDraft — draft advocacy document requiring attorney review
    ENT-046 LiabilityTheory — attorney-authored theory connecting facts to responsibility
    ENT-047 InsurancePolicy — coverage instrument
    ENT-048 InsuranceClaim — carrier-specific claim record
    ENT-049 CoveragePosition — carrier or attorney interpretation of coverage
    ENT-066 RecordCompletenessAssessment — scope-specific assessment
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

ISSUE_SEVERITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL")
ISSUE_STATUSES = ("OPEN", "IN_REVIEW", "RESOLVED", "DISMISSED", "ESCALATED")

READINESS_STATUSES = ("NOT_STARTED", "IN_PROGRESS", "PASSED", "FAILED", "WAIVED")

DEMAND_STATUSES = (
    "ASSEMBLING", "DRAFTING", "ATTORNEY_REVIEW",
    "REVISION_REQUIRED", "AUTHORIZED", "SENT",
    "SUPERSEDED", "WITHDRAWN",
)

COVERAGE_STATUSES = ("CONFIRMED", "DISPUTED", "RESERVATION_OF_RIGHTS", "DENIED", "PENDING")


class Issue(Base):
    """Question or problem requiring investigation, judgment, or action (ENT-077).

    Issues are the structured work items for attorney review. They can be
    created automatically (by flags) or manually. Each issue has an owner,
    severity, and must be resolved before the demand-ready gate passes.
    """
    __tablename__ = "issues"

    issue_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    source_flag_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("event_nodes.node_id"), nullable=True)
    source_fact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("evidence_facts.fact_id"), nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocks_demand_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class DemandDraft(Base):
    """Draft advocacy document requiring attorney review and authorization (ENT-082).

    May be generated but not sent without authority. Versioned with revision
    history. Attorney must review and authorize before transmission.
    """
    __tablename__ = "demand_drafts"

    draft_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFTING")
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    narrative_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_by: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    authorized_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revision_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class DemandPackage(Base):
    """Versioned set of demand materials authorized for transmission (ENT-081).

    Becomes immutable upon authorization. Contains the demand draft with
    referenced evidence attachments. Transmission locks a specific version.
    """
    __tablename__ = "demand_packages"

    package_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    draft_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("demand_drafts.draft_id"), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ASSEMBLING")
    total_demanded: Mapped[float | None] = mapped_column(Float, nullable=True)
    authorized_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_to: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    transmission_method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    draft = relationship("DemandDraft", lazy="selectin", foreign_keys=[draft_id])


class ReadinessAssessment(Base):
    """Review of defined prerequisites for a business milestone (ENT-080).

    Does not itself make a reserved legal decision. Records what was checked,
    whether each check passed, and who reviewed it.
    """
    __tablename__ = "readiness_assessments"

    assessment_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    milestone: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NOT_STARTED")
    total_checks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed_checks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_checks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    waived_checks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked_by_issues: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked_by_flags: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class RecordCompletenessAssessment(Base):
    """Scope-specific assessment of whether expected materials were received (ENT-066).

    Defines expected set, received set, gaps, and reviewer. Used to track
    record retrieval progress and signal missing evidence.
    """
    __tablename__ = "record_completeness_assessments"

    assessment_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    provider_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("providers.provider_id"), nullable=True)
    scope_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_record_types: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_date_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    expected_date_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_expected_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_received_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_missing_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completeness_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class InsurancePolicy(Base):
    """Coverage instrument associated with a party or incident (ENT-047)."""
    __tablename__ = "insurance_policies"

    policy_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("claims.claim_id"), nullable=True)
    carrier_name: Mapped[str] = mapped_column(String(200), nullable=False)
    policy_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    policy_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    insured_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    policy_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    umbrella_excess_limit: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class InsuranceClaim(Base):
    """Carrier-specific claim record and identifier (ENT-048)."""
    __tablename__ = "insurance_claims"

    insurance_claim_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    policy_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("insurance_policies.policy_id"), nullable=True)
    claim_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("claims.claim_id"), nullable=True)
    carrier_claim_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    adjuster_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    adjuster_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    adjuster_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    coverage_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    policy = relationship("InsurancePolicy", lazy="selectin", foreign_keys=[policy_id])


class CoveragePosition(Base):
    """Carrier or attorney interpretation of coverage status (ENT-049).

    Versioned and source-attributed. Never automatically derived — must
    be reviewed. Preserves different interpretations if they conflict.
    """
    __tablename__ = "coverage_positions"

    position_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    insurance_claim_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("insurance_claims.insurance_claim_id"), nullable=True)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    coverage_status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class LiabilityTheory(Base):
    """Attorney-authored or approved theory connecting facts to responsibility (ENT-046).

    References supporting and contradicting evidence. Must be attorney-reviewed
    or attributed to an approved legal source. Versioned.
    """
    __tablename__ = "liability_theories"

    theory_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("cases.case_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("claims.claim_id"), nullable=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    theory_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    legal_basis: Mapped[str | None] = mapped_column(String(200), nullable=True)
    supporting_facts: Mapped[str | None] = mapped_column(Text, nullable=True)
    contradicting_facts: Mapped[str | None] = mapped_column(Text, nullable=True)
    authored_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
