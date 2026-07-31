"""Phase 2A: Evidence, workflow, and client portal schema for TRACE.

Revision ID: 0017
Revises: 0016_firm_users
Create Date: 2026-07-31

Creates 31 new tables in dependency order across these layers:
  1. Global platform reference (no FKs to TRACE tables)
  2. Tenant-scoped standalone tables
  3. Source-linked evidence (depends on documents, providers)
  4. Matter structure (depends on cases)
  5. Workflow and workflow-supporting tables
  6. Dependent tables referencing the above

All tables belong to the trace schema (set by search_path in connection URL).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = '0017'
down_revision: str | None = '0016_firm_users'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ═══════════════════════════════════════════════════════════════════
    # Layer 1: Global platform reference tables (no tenant_id, no FKs)
    # ═══════════════════════════════════════════════════════════════════

    op.create_table('jurisdiction_profiles',
        sa.Column('profile_id', sa.Uuid(), nullable=False),
        sa.Column('jurisdiction', sa.String(length=2), nullable=False),
        sa.Column('version', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('superseded_by', sa.Uuid(), nullable=True),
        sa.Column('ruleset', sa.JSON(), nullable=True),
        sa.Column('required_disclosures', sa.JSON(), nullable=True),
        sa.Column('signature_requirements', sa.JSON(), nullable=True),
        sa.Column('supported_workflows', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('profile_id'),
    )

    # ═══════════════════════════════════════════════════════════════════
    # Layer 2: Tenant-scoped standalone tables
    # ═══════════════════════════════════════════════════════════════════

    op.create_table('business_events',
        sa.Column('event_id', sa.Uuid(), nullable=False),
        sa.Column('event_type', sa.String(length=200), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('aggregate_type', sa.String(length=100), nullable=False),
        sa.Column('aggregate_id', sa.Uuid(), nullable=False),
        sa.Column('aggregate_version', sa.Integer(), nullable=False),
        sa.Column('actor_type', sa.String(length=50), nullable=False),
        sa.Column('actor_id', sa.Uuid(), nullable=True),
        sa.Column('authority_class', sa.String(length=30), nullable=False),
        sa.Column('authority_record_id', sa.Uuid(), nullable=True),
        sa.Column('policy_version_id', sa.Uuid(), nullable=True),
        sa.Column('correlation_id', sa.String(length=100), nullable=True),
        sa.Column('causation_id', sa.Uuid(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('sensitivity_class', sa.String(length=20), nullable=False),
        sa.Column('schema_version', sa.String(length=10), nullable=False),
        sa.PrimaryKeyConstraint('event_id'),
    )
    op.create_index('ix_business_events_event_type', 'business_events', ['event_type'])
    op.create_index('ix_business_events_tenant_id', 'business_events', ['tenant_id'])
    op.create_index('ix_business_events_correlation_id', 'business_events', ['correlation_id'])
    op.create_index('ix_business_events_aggregate', 'business_events', ['aggregate_type', 'aggregate_id'])
    op.create_index('ix_business_events_tenant_time', 'business_events', ['tenant_id', 'occurred_at'])

    op.create_table('policy_records',
        sa.Column('policy_id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('category', sa.String(length=30), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('previous_version_id', sa.Uuid(), nullable=True),
        sa.Column('jurisdiction', sa.String(length=2), nullable=True),
        sa.Column('effective_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expiration_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('approved_by', sa.Uuid(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('policy_content', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('policy_id'),
    )
    op.create_index('ix_policy_records_tenant_id', 'policy_records', ['tenant_id'])

    op.create_table('consent_records',
        sa.Column('consent_id', sa.Uuid(), nullable=False),
        sa.Column('person_id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.Column('matter_id', sa.Uuid(), nullable=True),
        sa.Column('consent_type', sa.String(length=50), nullable=False),
        sa.Column('state', sa.String(length=20), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('previous_version_id', sa.Uuid(), nullable=True),
        sa.Column('granted_by', sa.String(length=200), nullable=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('disclosure_version', sa.String(length=50), nullable=True),
        sa.Column('expiration_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('event_metadata', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('consent_id'),
    )
    op.create_index('ix_consent_records_person_id', 'consent_records', ['person_id'])

    # ═══════════════════════════════════════════════════════════════════
    # Layer 3: Source-linked evidence (depends on existing tables)
    # ═══════════════════════════════════════════════════════════════════

    op.create_table('source_locations',
        sa.Column('location_id', sa.Uuid(), nullable=False),
        sa.Column('document_id', sa.Uuid(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('bbox_x1', sa.Float(), nullable=True),
        sa.Column('bbox_y1', sa.Float(), nullable=True),
        sa.Column('bbox_x2', sa.Float(), nullable=True),
        sa.Column('bbox_y2', sa.Float(), nullable=True),
        sa.Column('text_snippet', sa.Text(), nullable=True),
        sa.Column('extraction_method', sa.String(length=30), nullable=False),
        sa.Column('extraction_confidence', sa.Float(), nullable=True),
        sa.Column('extraction_model_version', sa.String(length=30), nullable=True),
        sa.Column('extracted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.document_id']),
        sa.PrimaryKeyConstraint('location_id'),
    )

    op.create_table('evidence_facts',
        sa.Column('fact_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('fact_type', sa.String(length=30), nullable=False),
        sa.Column('fact_date', sa.Date(), nullable=True),
        sa.Column('fact_text', sa.Text(), nullable=False),
        sa.Column('provider_id', sa.Uuid(), nullable=True),
        sa.Column('source_location_id', sa.Uuid(), nullable=False),
        sa.Column('review_status', sa.String(length=20), nullable=False),
        sa.Column('reviewed_by', sa.Uuid(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('previous_version_id', sa.Uuid(), nullable=True),
        sa.Column('is_contradicted', sa.Boolean(), nullable=False),
        sa.Column('is_duplicate', sa.Boolean(), nullable=False),
        sa.Column('duplicate_of_fact_id', sa.Uuid(), nullable=True),
        sa.Column('quality_flags', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.provider_id']),
        sa.ForeignKeyConstraint(['source_location_id'], ['source_locations.location_id']),
        sa.ForeignKeyConstraint(['previous_version_id'], ['evidence_facts.fact_id']),
        sa.ForeignKeyConstraint(['duplicate_of_fact_id'], ['evidence_facts.fact_id']),
        sa.PrimaryKeyConstraint('fact_id'),
    )
    op.create_index('ix_evidence_facts_case_id', 'evidence_facts', ['case_id'])

    op.create_table('fact_versions',
        sa.Column('version_id', sa.Uuid(), nullable=False),
        sa.Column('fact_id', sa.Uuid(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('previous_fact_text', sa.Text(), nullable=True),
        sa.Column('previous_fact_date', sa.Date(), nullable=True),
        sa.Column('previous_fact_type', sa.String(length=30), nullable=True),
        sa.Column('previous_review_status', sa.String(length=20), nullable=True),
        sa.Column('previous_provider_id', sa.Uuid(), nullable=True),
        sa.Column('changed_by', sa.Uuid(), nullable=True),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['fact_id'], ['evidence_facts.fact_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('version_id'),
    )
    op.create_index('ix_fact_versions_fact_id', 'fact_versions', ['fact_id'])

    op.create_table('contradiction_pairs',
        sa.Column('contradiction_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('fact_a_id', sa.Uuid(), nullable=False),
        sa.Column('fact_b_id', sa.Uuid(), nullable=False),
        sa.Column('contradiction_type', sa.String(length=30), nullable=False),
        sa.Column('resolution_status', sa.String(length=30), nullable=False),
        sa.Column('resolved_by', sa.Uuid(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attorney_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['fact_a_id'], ['evidence_facts.fact_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['fact_b_id'], ['evidence_facts.fact_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('contradiction_id'),
        sa.UniqueConstraint('fact_a_id', 'fact_b_id', name='uq_contradiction_pair'),
    )
    op.create_index('ix_contradiction_pairs_case_id', 'contradiction_pairs', ['case_id'])

    op.create_table('missing_evidence_signals',
        sa.Column('signal_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('signal_type', sa.String(length=40), nullable=False),
        sa.Column('source_fact_id', sa.Uuid(), nullable=True),
        sa.Column('expected_record_type', sa.String(length=50), nullable=True),
        sa.Column('expected_from_provider_id', sa.Uuid(), nullable=True),
        sa.Column('expected_date_range_start', sa.Date(), nullable=True),
        sa.Column('expected_date_range_end', sa.Date(), nullable=True),
        sa.Column('days_overdue', sa.Integer(), nullable=False),
        sa.Column('resolved', sa.Boolean(), nullable=True),
        sa.Column('resolved_by', sa.Uuid(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['expected_from_provider_id'], ['providers.provider_id']),
        sa.ForeignKeyConstraint(['source_fact_id'], ['evidence_facts.fact_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('signal_id'),
    )
    op.create_index('ix_missing_evidence_signals_case_id', 'missing_evidence_signals', ['case_id'])

    # ═══════════════════════════════════════════════════════════════════
    # Layer 4: Matter structure
    # ═══════════════════════════════════════════════════════════════════

    op.create_table('incidents',
        sa.Column('incident_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('incident_type', sa.String(length=40), nullable=False),
        sa.Column('incident_date', sa.Date(), nullable=False),
        sa.Column('incident_time', sa.String(length=10), nullable=True),
        sa.Column('location_address', sa.Text(), nullable=True),
        sa.Column('location_city', sa.String(length=100), nullable=True),
        sa.Column('location_state', sa.String(length=2), nullable=True),
        sa.Column('location_zip', sa.String(length=10), nullable=True),
        sa.Column('mechanism', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('police_report_number', sa.String(length=50), nullable=True),
        sa.Column('police_agency', sa.String(length=100), nullable=True),
        sa.Column('weather_conditions', sa.String(length=100), nullable=True),
        sa.Column('road_conditions', sa.String(length=100), nullable=True),
        sa.Column('source_fact_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_fact_id'], ['evidence_facts.fact_id']),
        sa.PrimaryKeyConstraint('incident_id'),
    )
    op.create_index('ix_incidents_case_id', 'incidents', ['case_id'])

    op.create_table('claims',
        sa.Column('claim_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('incident_id', sa.Uuid(), nullable=True),
        sa.Column('claim_type', sa.String(length=30), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('claimed_amount', sa.Float(), nullable=True),
        sa.Column('settled_amount', sa.Float(), nullable=True),
        sa.Column('adverse_party_name', sa.String(length=200), nullable=True),
        sa.Column('adverse_party_type', sa.String(length=30), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['incident_id'], ['incidents.incident_id']),
        sa.PrimaryKeyConstraint('claim_id'),
    )
    op.create_index('ix_claims_case_id', 'claims', ['case_id'])

    # ═══════════════════════════════════════════════════════════════════
    # Layer 5: Medical and treatment
    # ═══════════════════════════════════════════════════════════════════

    op.create_table('injuries',
        sa.Column('injury_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('body_region', sa.String(length=30), nullable=False),
        sa.Column('injury_type', sa.String(length=30), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('onset_date', sa.Date(), nullable=True),
        sa.Column('mechanism', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('resolution_date', sa.Date(), nullable=True),
        sa.Column('is_permanent', sa.Boolean(), nullable=False),
        sa.Column('source_fact_id', sa.Uuid(), nullable=True),
        sa.Column('attorney_annotation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_fact_id'], ['evidence_facts.fact_id']),
        sa.PrimaryKeyConstraint('injury_id'),
    )
    op.create_index('ix_injuries_case_id', 'injuries', ['case_id'])

    op.create_table('symptoms',
        sa.Column('symptom_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('injury_id', sa.Uuid(), nullable=True),
        sa.Column('body_region', sa.String(length=30), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('onset_date', sa.Date(), nullable=True),
        sa.Column('frequency', sa.String(length=30), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('source_fact_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['injury_id'], ['injuries.injury_id']),
        sa.ForeignKeyConstraint(['source_fact_id'], ['evidence_facts.fact_id']),
        sa.PrimaryKeyConstraint('symptom_id'),
    )
    op.create_index('ix_symptoms_case_id', 'symptoms', ['case_id'])

    op.create_table('diagnoses',
        sa.Column('diagnosis_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('injury_id', sa.Uuid(), nullable=True),
        sa.Column('provider_id', sa.Uuid(), nullable=True),
        sa.Column('diagnosis_code', sa.String(length=20), nullable=True),
        sa.Column('diagnosis_code_system', sa.String(length=20), nullable=True),
        sa.Column('diagnosis_text', sa.Text(), nullable=False),
        sa.Column('diagnosis_date', sa.Date(), nullable=True),
        sa.Column('source_fact_id', sa.Uuid(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['injury_id'], ['injuries.injury_id']),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.provider_id']),
        sa.ForeignKeyConstraint(['source_fact_id'], ['evidence_facts.fact_id']),
        sa.PrimaryKeyConstraint('diagnosis_id'),
    )
    op.create_index('ix_diagnoses_case_id', 'diagnoses', ['case_id'])

    op.create_table('treatment_episodes',
        sa.Column('episode_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('injury_id', sa.Uuid(), nullable=True),
        sa.Column('provider_id', sa.Uuid(), nullable=True),
        sa.Column('episode_type', sa.String(length=40), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('facility_name', sa.String(length=200), nullable=True),
        sa.Column('treating_provider_name', sa.String(length=200), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['injury_id'], ['injuries.injury_id']),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.provider_id']),
        sa.PrimaryKeyConstraint('episode_id'),
    )
    op.create_index('ix_treatment_episodes_case_id', 'treatment_episodes', ['case_id'])

    # ═══════════════════════════════════════════════════════════════════
    # Layer 6: Damages, insurance, liability
    # ═══════════════════════════════════════════════════════════════════

    op.create_table('damages_categories',
        sa.Column('category_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('claim_id', sa.Uuid(), nullable=True),
        sa.Column('category_type', sa.String(length=30), nullable=False),
        sa.Column('total_claimed', sa.Float(), nullable=False),
        sa.Column('total_supported', sa.Float(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.claim_id']),
        sa.PrimaryKeyConstraint('category_id'),
    )
    op.create_index('ix_damages_categories_case_id', 'damages_categories', ['case_id'])

    op.create_table('damages_items',
        sa.Column('item_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('category_id', sa.Uuid(), nullable=True),
        sa.Column('claim_id', sa.Uuid(), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('source_fact_id', sa.Uuid(), nullable=True),
        sa.Column('source_document_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('date_incurred', sa.Date(), nullable=True),
        sa.Column('certainty', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['damages_categories.category_id']),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.claim_id']),
        sa.ForeignKeyConstraint(['source_document_id'], ['documents.document_id']),
        sa.ForeignKeyConstraint(['source_fact_id'], ['evidence_facts.fact_id']),
        sa.PrimaryKeyConstraint('item_id'),
    )
    op.create_index('ix_damages_items_case_id', 'damages_items', ['case_id'])

    op.create_table('insurance_policies',
        sa.Column('policy_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('claim_id', sa.Uuid(), nullable=True),
        sa.Column('carrier_name', sa.String(length=200), nullable=False),
        sa.Column('policy_number', sa.String(length=100), nullable=True),
        sa.Column('policy_type', sa.String(length=50), nullable=True),
        sa.Column('insured_name', sa.String(length=200), nullable=True),
        sa.Column('policy_limit', sa.Float(), nullable=True),
        sa.Column('effective_date', sa.Date(), nullable=True),
        sa.Column('expiration_date', sa.Date(), nullable=True),
        sa.Column('umbrella_excess_limit', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.claim_id']),
        sa.PrimaryKeyConstraint('policy_id'),
    )
    op.create_index('ix_insurance_policies_case_id', 'insurance_policies', ['case_id'])

    op.create_table('insurance_claims',
        sa.Column('insurance_claim_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('policy_id', sa.Uuid(), nullable=True),
        sa.Column('claim_id', sa.Uuid(), nullable=True),
        sa.Column('carrier_claim_number', sa.String(length=100), nullable=True),
        sa.Column('adjuster_name', sa.String(length=200), nullable=True),
        sa.Column('adjuster_phone', sa.String(length=20), nullable=True),
        sa.Column('adjuster_email', sa.String(length=200), nullable=True),
        sa.Column('coverage_status', sa.String(length=30), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['policy_id'], ['insurance_policies.policy_id']),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.claim_id']),
        sa.PrimaryKeyConstraint('insurance_claim_id'),
    )
    op.create_index('ix_insurance_claims_case_id', 'insurance_claims', ['case_id'])

    op.create_table('coverage_positions',
        sa.Column('position_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('insurance_claim_id', sa.Uuid(), nullable=True),
        sa.Column('source', sa.String(length=30), nullable=False),
        sa.Column('coverage_status', sa.String(length=30), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('received_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['insurance_claim_id'], ['insurance_claims.insurance_claim_id']),
        sa.PrimaryKeyConstraint('position_id'),
    )
    op.create_index('ix_coverage_positions_case_id', 'coverage_positions', ['case_id'])

    op.create_table('liability_theories',
        sa.Column('theory_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('claim_id', sa.Uuid(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('theory_text', sa.Text(), nullable=True),
        sa.Column('legal_basis', sa.String(length=200), nullable=True),
        sa.Column('supporting_facts', sa.Text(), nullable=True),
        sa.Column('contradicting_facts', sa.Text(), nullable=True),
        sa.Column('authored_by', sa.Uuid(), nullable=True),
        sa.Column('approved_by', sa.Uuid(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['claim_id'], ['claims.claim_id']),
        sa.PrimaryKeyConstraint('theory_id'),
    )
    op.create_index('ix_liability_theories_case_id', 'liability_theories', ['case_id'])

    # ═══════════════════════════════════════════════════════════════════
    # Layer 7: Workflow and operations
    # ═══════════════════════════════════════════════════════════════════

    op.create_table('issues',
        sa.Column('issue_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('assigned_to', sa.Uuid(), nullable=True),
        sa.Column('source_flag_id', sa.Uuid(), nullable=True),
        sa.Column('source_fact_id', sa.Uuid(), nullable=True),
        sa.Column('resolved_by', sa.Uuid(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('blocks_demand_ready', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_flag_id'], ['event_nodes.node_id']),
        sa.ForeignKeyConstraint(['source_fact_id'], ['evidence_facts.fact_id']),
        sa.PrimaryKeyConstraint('issue_id'),
    )
    op.create_index('ix_issues_case_id', 'issues', ['case_id'])

    op.create_table('demand_drafts',
        sa.Column('draft_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('narrative_body', sa.Text(), nullable=True),
        sa.Column('generated_by', sa.String(length=30), nullable=True),
        sa.Column('reviewed_by', sa.Uuid(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('authorized_by', sa.Uuid(), nullable=True),
        sa.Column('authorized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revision_notes', sa.Text(), nullable=True),
        sa.Column('superseded_by', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('draft_id'),
    )
    op.create_index('ix_demand_drafts_case_id', 'demand_drafts', ['case_id'])

    op.create_table('demand_packages',
        sa.Column('package_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('draft_id', sa.Uuid(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('total_demanded', sa.Float(), nullable=True),
        sa.Column('authorized_by', sa.Uuid(), nullable=True),
        sa.Column('authorized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_to', sa.String(length=200), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('transmission_method', sa.String(length=30), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['draft_id'], ['demand_drafts.draft_id']),
        sa.PrimaryKeyConstraint('package_id'),
    )
    op.create_index('ix_demand_packages_case_id', 'demand_packages', ['case_id'])

    op.create_table('readiness_assessments',
        sa.Column('assessment_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('milestone', sa.String(length=30), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('total_checks', sa.Integer(), nullable=False),
        sa.Column('passed_checks', sa.Integer(), nullable=False),
        sa.Column('failed_checks', sa.Integer(), nullable=False),
        sa.Column('waived_checks', sa.Integer(), nullable=False),
        sa.Column('blocked_by_issues', sa.Integer(), nullable=False),
        sa.Column('blocked_by_flags', sa.Integer(), nullable=False),
        sa.Column('reviewed_by', sa.Uuid(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('assessment_id'),
    )
    op.create_index('ix_readiness_assessments_case_id', 'readiness_assessments', ['case_id'])

    op.create_table('record_completeness_assessments',
        sa.Column('assessment_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('provider_id', sa.Uuid(), nullable=True),
        sa.Column('scope_description', sa.Text(), nullable=True),
        sa.Column('expected_record_types', sa.Text(), nullable=True),
        sa.Column('expected_date_start', sa.Date(), nullable=True),
        sa.Column('expected_date_end', sa.Date(), nullable=True),
        sa.Column('total_expected_items', sa.Integer(), nullable=False),
        sa.Column('total_received_items', sa.Integer(), nullable=False),
        sa.Column('total_missing_items', sa.Integer(), nullable=False),
        sa.Column('completeness_pct', sa.Float(), nullable=False),
        sa.Column('reviewed_by', sa.Uuid(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['provider_id'], ['providers.provider_id']),
        sa.PrimaryKeyConstraint('assessment_id'),
    )
    op.create_index('ix_record_completeness_assessments_case_id', 'record_completeness_assessments', ['case_id'])

    # ═══════════════════════════════════════════════════════════════════
    # Layer 8: Evidence integrity and access
    # ═══════════════════════════════════════════════════════════════════

    op.create_table('chain_of_custody_events',
        sa.Column('event_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('document_id', sa.Uuid(), nullable=False),
        sa.Column('event_type', sa.String(length=30), nullable=False),
        sa.Column('from_custodian', sa.String(length=200), nullable=True),
        sa.Column('to_custodian', sa.String(length=200), nullable=True),
        sa.Column('actor_id', sa.Uuid(), nullable=True),
        sa.Column('actor_role', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('integrity_hash_before', sa.String(length=64), nullable=True),
        sa.Column('integrity_hash_after', sa.String(length=64), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.document_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('event_id'),
    )
    op.create_index('ix_chain_of_custody_events_case_id', 'chain_of_custody_events', ['case_id'])

    op.create_table('witnesses',
        sa.Column('witness_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=False),
        sa.Column('witness_type', sa.String(length=30), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=200), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('relationship_to_client', sa.String(length=100), nullable=True),
        sa.Column('credibility_notes', sa.Text(), nullable=True),
        sa.Column('is_deposed', sa.Boolean(), nullable=True),
        sa.Column('deposition_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('witness_id'),
    )
    op.create_index('ix_witnesses_case_id', 'witnesses', ['case_id'])

    op.create_table('witness_statements',
        sa.Column('statement_id', sa.Uuid(), nullable=False),
        sa.Column('case_id', sa.Uuid(), nullable=False),
        sa.Column('witness_id', sa.Uuid(), nullable=False),
        sa.Column('statement_type', sa.String(length=30), nullable=False),
        sa.Column('statement_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('full_text', sa.Text(), nullable=True),
        sa.Column('source_document_id', sa.Uuid(), nullable=True),
        sa.Column('source_page_number', sa.Integer(), nullable=True),
        sa.Column('recorded_by', sa.Uuid(), nullable=True),
        sa.Column('under_oath', sa.Boolean(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['case_id'], ['cases.case_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['witness_id'], ['witnesses.witness_id']),
        sa.ForeignKeyConstraint(['source_document_id'], ['documents.document_id']),
        sa.PrimaryKeyConstraint('statement_id'),
    )
    op.create_index('ix_witness_statements_case_id', 'witness_statements', ['case_id'])

    # ═══════════════════════════════════════════════════════════════════
    # Layer 9: Client portal access projection + jurisdiction activation
    # ═══════════════════════════════════════════════════════════════════

    op.create_table('trace_client_access_projections',
        sa.Column('projection_id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('client_identity_id', sa.Uuid(), nullable=False),
        sa.Column('party_role_id', sa.Uuid(), nullable=True),
        sa.Column('matter_id', sa.Uuid(), nullable=True),
        sa.Column('engagement_workflow_id', sa.Uuid(), nullable=True),
        sa.Column('canonical_grant_id', sa.Uuid(), nullable=True),
        sa.Column('relationship_scope', sa.String(length=40), nullable=False),
        sa.Column('permissions', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_event_id', sa.Uuid(), nullable=True),
        sa.Column('projected_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['matter_id'], ['cases.case_id']),
        sa.PrimaryKeyConstraint('projection_id'),
    )
    op.create_index('ix_trace_client_access_projections_tenant_id', 'trace_client_access_projections', ['tenant_id'])
    op.create_index('ix_trace_client_access_projections_client_identity_id', 'trace_client_access_projections', ['client_identity_id'])

    op.create_table('jurisdiction_activations',
        sa.Column('activation_id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('profile_id', sa.Uuid(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('activated_by', sa.Uuid(), nullable=True),
        sa.Column('deactivated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tenant_override_config', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['profile_id'], ['jurisdiction_profiles.profile_id']),
        sa.PrimaryKeyConstraint('activation_id'),
    )
    op.create_index('ix_jurisdiction_activations_tenant_id', 'jurisdiction_activations', ['tenant_id'])


def downgrade() -> None:
    op.drop_table('jurisdiction_activations')
    op.drop_table('trace_client_access_projections')
    op.drop_table('witness_statements')
    op.drop_table('witnesses')
    op.drop_table('chain_of_custody_events')
    op.drop_table('record_completeness_assessments')
    op.drop_table('readiness_assessments')
    op.drop_table('demand_packages')
    op.drop_table('demand_drafts')
    op.drop_table('issues')
    op.drop_table('coverage_positions')
    op.drop_table('insurance_claims')
    op.drop_table('insurance_policies')
    op.drop_table('liability_theories')
    op.drop_table('damages_items')
    op.drop_table('damages_categories')
    op.drop_table('treatment_episodes')
    op.drop_table('diagnoses')
    op.drop_table('symptoms')
    op.drop_table('injuries')
    op.drop_table('claims')
    op.drop_table('incidents')
    op.drop_table('missing_evidence_signals')
    op.drop_table('contradiction_pairs')
    op.drop_table('fact_versions')
    op.drop_table('evidence_facts')
    op.drop_table('source_locations')
    op.drop_table('consent_records')
    op.drop_table('policy_records')
    op.drop_table('business_events')
    op.drop_table('jurisdiction_profiles')
