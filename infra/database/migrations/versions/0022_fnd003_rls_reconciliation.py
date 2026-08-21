"""FND-003: operational tenant isolation / RLS reconciliation.

Inventory-driven reconciliation of every tenant-scoped trace.* table at the
locked base (45 physical tables: 43 tenant-scoped, 1 global reference
jurisdiction_profiles, 1 non-tenant internal alembic_version).

Replaces the inconsistent historical policies (tenant_isolation /
firm_isolation) with ONE canonical policy per table:
``tenant_isolation_fnd003`` (command ALL, explicit USING + WITH CHECK).

Preflight: any policy on a targeted table whose name is not one of the three
known names aborts the migration (BLOCKED_UNEXPECTED_POLICY) — old permissive
policies must never be layered on top of the canonical one.

Tenant expression used everywhere:

    NULLIF(current_setting('app.current_tenant_id', true), '')::uuid

Missing/empty context can never match (fails closed).

Downgrade deliberately restores the known 0021 schema-defined RLS state
(exact historical policy predicates and enable/force flags).

Revision ID: 0022_fnd003_rls_reconciliation
Revises: 0021_flag_priority_guard
Create Date: 2026-08-20
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0022_fnd003_rls_reconciliation"
down_revision: str | None = "0021_flag_priority_guard"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_T = "NULLIF(current_setting('app.current_tenant_id', true), '')::uuid"
_CANONICAL = "tenant_isolation_fnd003"
_KNOWN_POLICIES = ("tenant_isolation", "firm_isolation", _CANONICAL)

# ── Classification manifest (binding) ────────────────────────────────

_DIRECT_SIMPLE = {
    "cases": "firm_id",
    "firm_users": "firm_id",
    "business_events": "tenant_id",
    "policy_records": "tenant_id",
    "jurisdiction_activations": "tenant_id",
}

_DIRECT_CASE_BOUND = (
    "signed_documents", "liens", "medical_bill_line", "upload_links",
)

_CASE_DERIVED = (
    "providers", "documents", "chronology_entries", "event_nodes",
    "record_requests", "pipeline_audit_log",
    "evidence_facts", "contradiction_pairs", "missing_evidence_signals",
    "incidents", "claims", "injuries", "symptoms", "diagnoses",
    "treatment_episodes", "damages_categories", "damages_items",
    "insurance_policies", "insurance_claims", "coverage_positions",
    "liability_theories", "issues", "demand_drafts", "demand_packages",
    "readiness_assessments", "record_completeness_assessments",
    "chain_of_custody_events", "witnesses", "witness_statements",
)

_ALL_TENANT_TABLES = tuple(_DIRECT_SIMPLE) + _DIRECT_CASE_BOUND + _CASE_DERIVED + (
    "audit_log", "consent_records", "trace_client_access_projections",
    "source_locations", "fact_versions",
)
assert len(_ALL_TENANT_TABLES) == 43, len(_ALL_TENANT_TABLES)


def _predicate(table: str) -> str:
    if table in _DIRECT_SIMPLE:
        col = _DIRECT_SIMPLE[table]
        return f"{col} = {_T}"
    if table in _DIRECT_CASE_BOUND:
        return (
            f"firm_id = {_T} AND case_id IN ("
            f"SELECT c.case_id FROM trace.cases c WHERE c.firm_id = {_T})"
        )
    if table == "audit_log":
        return (
            f"(case_id IS NULL AND firm_id = {_T}) OR ("
            f"case_id IN (SELECT c.case_id FROM trace.cases c WHERE c.firm_id = {_T}) "
            f"AND (firm_id IS NULL OR firm_id = {_T}))"
        )
    if table == "consent_records":
        return (
            f"(matter_id IS NULL AND tenant_id = {_T}) OR ("
            f"matter_id IN (SELECT c.case_id FROM trace.cases c WHERE c.firm_id = {_T}) "
            f"AND (tenant_id IS NULL OR tenant_id = {_T}))"
        )
    if table == "trace_client_access_projections":
        return (
            f"tenant_id = {_T} AND (matter_id IS NULL OR matter_id IN ("
            f"SELECT c.case_id FROM trace.cases c WHERE c.firm_id = {_T}))"
        )
    if table == "source_locations":
        return (
            "EXISTS (SELECT 1 FROM trace.documents d "
            "JOIN trace.cases c ON c.case_id = d.case_id "
            f"WHERE d.document_id = source_locations.document_id AND c.firm_id = {_T})"
        )
    if table == "fact_versions":
        return (
            "EXISTS (SELECT 1 FROM trace.evidence_facts f "
            "JOIN trace.cases c ON c.case_id = f.case_id "
            f"WHERE f.fact_id = fact_versions.fact_id AND c.firm_id = {_T})"
        )
    # case-derived
    return (
        "EXISTS (SELECT 1 FROM trace.cases c "
        f"WHERE c.case_id = {table}.case_id AND c.firm_id = {_T})"
    )


_ARRAY_LITERAL = "{" + ",".join(_ALL_TENANT_TABLES) + "}"
_POLICIES_LITERAL = "(" + ",".join(f"'{p}'" for p in _KNOWN_POLICIES) + ")"

_PREFLIGHT_SQL = f"""
DO $$
DECLARE
    t text;
    p record;
BEGIN
    FOREACH t IN ARRAY '{_ARRAY_LITERAL}'::text[] LOOP
        FOR p IN
            SELECT policyname FROM pg_policies
            WHERE schemaname = 'trace' AND tablename = t
              AND policyname NOT IN {_POLICIES_LITERAL}
        LOOP
            RAISE EXCEPTION 'BLOCKED_UNEXPECTED_POLICY: trace.% policy %', t, p.policyname;
        END LOOP;
    END LOOP;
END
$$;
"""


def upgrade() -> None:
    op.execute(_PREFLIGHT_SQL)
    for table in _ALL_TENANT_TABLES:
        op.execute(
            f"DROP POLICY IF EXISTS tenant_isolation ON trace.{table};"
        )
        op.execute(
            f"DROP POLICY IF EXISTS firm_isolation ON trace.{table};"
        )
        op.execute(
            f"DROP POLICY IF EXISTS {_CANONICAL} ON trace.{table};"
        )
        op.execute(f"ALTER TABLE trace.{table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE trace.{table} FORCE ROW LEVEL SECURITY;")
        pred = _predicate(table)
        op.execute(
            f"CREATE POLICY {_CANONICAL} ON trace.{table} "
            f"USING ({pred}) WITH CHECK ({pred});"
        )


# ── Downgrade: restore known 0021 schema-defined RLS state ────────────

_LEGACY_CASE_DERIVED_UNQUALIFIED = (
    "providers", "documents", "chronology_entries", "event_nodes",
    "record_requests",
)
_LEGACY_CASE_DERIVED_QUALIFIED = ("pipeline_audit_log", "signed_documents")
_LEGACY_FIRM_COALESCE = ("upload_links", "firm_users")


def downgrade() -> None:
    for table in _ALL_TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {_CANONICAL} ON trace.{table};")
    for table in _ALL_TENANT_TABLES:
        op.execute(f"ALTER TABLE trace.{table} DISABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE trace.{table} NO FORCE ROW LEVEL SECURITY;")

    # cases: two historical policies
    op.execute(
        "CREATE POLICY tenant_isolation ON trace.cases USING "
        "(firm_id = current_setting('app.current_tenant_id', true)::uuid);"
    )
    op.execute(
        "CREATE POLICY firm_isolation ON trace.cases USING (firm_id = "
        "COALESCE(current_setting('app.current_tenant_id', true), "
        "'00000000-0000-0000-0000-000000000000')::uuid);"
    )
    op.execute("ALTER TABLE trace.cases ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE trace.cases FORCE ROW LEVEL SECURITY;")

    for table in _LEGACY_CASE_DERIVED_UNQUALIFIED:
        op.execute(
            f"CREATE POLICY tenant_isolation ON trace.{table} USING "
            f"(case_id IN (SELECT case_id FROM cases WHERE "
            f"firm_id = current_setting('app.current_tenant_id', true)::uuid));"
        )
        op.execute(f"ALTER TABLE trace.{table} ENABLE ROW LEVEL SECURITY;")
        if table != "record_requests":
            op.execute(f"ALTER TABLE trace.{table} FORCE ROW LEVEL SECURITY;")

    for table in _LEGACY_CASE_DERIVED_QUALIFIED:
        op.execute(
            f"CREATE POLICY tenant_isolation ON trace.{table} USING "
            f"(case_id IN (SELECT case_id FROM trace.cases WHERE "
            f"firm_id = current_setting('app.current_tenant_id', true)::uuid));"
        )
        op.execute(f"ALTER TABLE trace.{table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE trace.{table} FORCE ROW LEVEL SECURITY;")

    for table in _LEGACY_FIRM_COALESCE:
        op.execute(
            f"CREATE POLICY tenant_isolation ON trace.{table} USING "
            f"(firm_id = COALESCE(current_setting('app.current_tenant_id', true), "
            f"'00000000-0000-0000-0000-000000000000')::uuid);"
        )
        op.execute(f"ALTER TABLE trace.{table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE trace.{table} FORCE ROW LEVEL SECURITY;")
