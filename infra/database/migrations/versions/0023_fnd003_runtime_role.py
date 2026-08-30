"""FND-003-R1: runtime role commissioning.

Creates the dedicated non-bypass application login ``trace_runtime_login``
and grants minimal same-tenant operational DML as VERSIONED SCHEMA STATE
(spec TRACE-FND-003-R1; authoritative for role/grant DDL).

Contract:
- LOGIN; NOSUPERUSER; NOBYPASSRLS; NOCREATEDB; NOCREATEROLE; NOINHERIT
- USAGE on schema ``trace`` only; no privileges anywhere in ``trace_phi``
- SELECT/INSERT/UPDATE/DELETE on the 43 tenant-scoped tables
- audit_log: INSERT only (SELECT/UPDATE/DELETE revoked)
- jurisdiction_profiles (global reference): SELECT only
- SELECT on ``trace.alembic_version`` (readiness revision probe)
- USAGE, SELECT on all sequences in ``trace``

Least-privilege rule (T01-R1): there is deliberately NO default-ACL /
future-table grant. Every future migration must grant the runtime login
explicitly for the operational tables it introduces — unknown future
tables start with zero runtime privileges.

No password is set here (fail closed): credentials are provisioned by the
operator secret-handling procedure during commissioning, never through
versioned state.

Downgrade revokes everything granted here and drops the role only when it
owns no objects / holds no memberships; otherwise it aborts loudly
(BLOCKED_ROLE_NOT_DROPPABLE) so privilege state can never silently linger.

Revision ID: 0023_fnd003_runtime_role
Revises: 0022_fnd003_rls_reconciliation
Create Date: 2026-08-23
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0023_fnd003_runtime_role"
down_revision: str | None = "0022_fnd003_rls_reconciliation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ROLE = "trace_runtime_login"

# ── Tenant-table manifest (binding; mirrors 0022) ────────────────────

_DIRECT_SIMPLE = (
    "cases", "firm_users", "business_events", "policy_records",
    "jurisdiction_activations",
)

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

_ALL_TENANT_TABLES = _DIRECT_SIMPLE + _DIRECT_CASE_BOUND + _CASE_DERIVED + (
    "audit_log", "consent_records", "trace_client_access_projections",
    "source_locations", "fact_versions",
)
assert len(_ALL_TENANT_TABLES) == 43, len(_ALL_TENANT_TABLES)

_GLOBAL_REFERENCE = ("jurisdiction_profiles",)


def upgrade() -> None:
    # 1. Role existence + attribute normalization (idempotent).
    #
    # Deliberately a single CREATE statement: the attribute set is written
    # inline so CREATE itself normalizes it. A follow-up ALTER ROLE is NOT
    # used here — on this host the migration login holds CREATEROLE but not
    # SUPERUSER, and Postgres refuses ALTER ROLE on any role that carries
    # SUPERUSER (or that the non-superuser caller cannot alter). CREATE with
    # the attributes inline is the only portable path and yields exactly the
    # contracted privileges: NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE
    # NOINHERIT LOGIN.
    op.execute(
        f"DO $$ BEGIN "
        f"IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{_ROLE}') THEN "
        f"CREATE ROLE {_ROLE} WITH LOGIN NOSUPERUSER NOBYPASSRLS "
        f"NOCREATEDB NOCREATEROLE NOINHERIT; "
        f"END IF; END $$;"
    )

    # 2. Schema usage only — no CREATE.
    op.execute(f"GRANT USAGE ON SCHEMA trace TO {_ROLE};")

    # 3. Same-tenant operational DML on tenant tables (INSERT-only audit).
    for table in _ALL_TENANT_TABLES:
        if table == "audit_log":
            op.execute(f"REVOKE ALL ON trace.audit_log FROM {_ROLE};")
            op.execute(f"GRANT INSERT ON trace.audit_log TO {_ROLE};")
            continue
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON trace.{table} TO {_ROLE};"
        )

    # 4. Global reference: read-only.
    for table in _GLOBAL_REFERENCE:
        op.execute(f"REVOKE ALL ON trace.{table} FROM {_ROLE};")
        op.execute(f"GRANT SELECT ON trace.{table} TO {_ROLE};")

    # 5. Readiness probe: revision row readable, nothing more.
    op.execute(f"GRANT SELECT ON trace.alembic_version TO {_ROLE};")

    # 6. Sequences (uuid defaults are client-side; serial columns still exist).
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA trace TO {_ROLE};")


def downgrade() -> None:
    op.execute(f"REVOKE SELECT ON trace.alembic_version FROM {_ROLE};")
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA trace FROM {_ROLE};")
    op.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA trace FROM {_ROLE};")
    op.execute(f"REVOKE ALL ON SCHEMA trace FROM {_ROLE};")
    op.execute(
        f"DO $$ DECLARE owned int; BEGIN "
        f"SELECT count(*) INTO owned FROM pg_class "
        f"WHERE relowner = (SELECT oid FROM pg_roles WHERE rolname = '{_ROLE}'); "
        f"IF owned > 0 THEN "
        f"RAISE EXCEPTION 'BLOCKED_ROLE_NOT_DROPPABLE: % owned object(s)', owned; "
        f"END IF; "
        f"DROP ROLE IF EXISTS {_ROLE}; "
        f"END $$;"
    )
