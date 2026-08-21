"""FND-003 — RLS tenant isolation adversarial tests (guarded PostgreSQL lane).

Runs against the designated test database under a NOSUPERUSER NOBYPASSRLS
test role. The docker harness superuser is used ONLY for setup (role
creation, grants, seeding); every isolation assertion executes as the
non-bypass role with transaction-local tenant context.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import text

from app.core.database import async_session_maker, engine

TEST_ROLE = "trace_fnd003_test_role"
TENANT_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
TENANT_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

TENANT_TABLES = (
    "cases", "audit_log", "signed_documents", "liens", "medical_bill_line",
    "upload_links", "firm_users", "business_events", "policy_records",
    "consent_records", "trace_client_access_projections",
    "jurisdiction_activations",
    "providers", "documents", "chronology_entries", "event_nodes",
    "record_requests", "pipeline_audit_log",
    "evidence_facts", "contradiction_pairs", "missing_evidence_signals",
    "incidents", "claims", "injuries", "symptoms", "diagnoses",
    "treatment_episodes", "damages_categories", "damages_items",
    "insurance_policies", "insurance_claims", "coverage_positions",
    "liability_theories", "issues", "demand_drafts", "demand_packages",
    "readiness_assessments", "record_completeness_assessments",
    "chain_of_custody_events", "witnesses", "witness_statements",
    "source_locations", "fact_versions",
)

GLOBAL_REFERENCE = ("jurisdiction_profiles",)
NON_TENANT_INTERNAL = ("alembic_version",)
CANONICAL_POLICY = "tenant_isolation_fnd003"


# ─────────────────────────────────────────────────────────────────────
# Setup: test role + grants (superuser), per-test seeding
# ─────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def _prepare_test_role():
    import asyncio

    async def _setup() -> None:
        async with engine.begin() as conn:
            await conn.execute(text(
                f"DO $$ BEGIN "
                f"IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{TEST_ROLE}') THEN "
                f"CREATE ROLE {TEST_ROLE} NOSUPERUSER NOBYPASSRLS NOLOGIN; "
                f"END IF; END $$;"
            ))
            await conn.execute(text(
                f"GRANT USAGE ON SCHEMA trace TO {TEST_ROLE}"
            ))
            await conn.execute(text(
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA trace TO {TEST_ROLE}"
            ))
            await conn.execute(text(
                f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA trace TO {TEST_ROLE}"
            ))
            # Audit invariants: effective application role is INSERT-only on audit_log.
            await conn.execute(text(
                f"REVOKE UPDATE, DELETE ON trace.audit_log FROM {TEST_ROLE}"
            ))

    asyncio.run(_setup())
    return


@asynccontextmanager
async def tenant_role_session(firm: str | None):
    """Session executing as the non-bypass test role with a tenant GUC."""
    async with async_session_maker() as session:
        await session.execute(text(f"SET LOCAL ROLE {TEST_ROLE}"))
        if firm is not None:
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :t, true)"),
                {"t": firm},
            )
        yield session
        await session.rollback()


async def _seed_case(conn, firm: str, label: str) -> uuid.UUID:
    case_id = uuid.uuid4()
    await conn.execute(text(
        "INSERT INTO trace.cases (case_id, client_token, firm_id, "
        "intake_record_id, incident_date, jurisdiction_state) VALUES "
        "(CAST(:c AS uuid), gen_random_uuid(), CAST(:f AS uuid), "
        "gen_random_uuid(), '2026-01-15', 'CA')"
    ), {"c": str(case_id), "f": firm})
    await conn.execute(text(
        "INSERT INTO trace.documents (case_id, s3_bucket, s3_key, source) "
        "VALUES (CAST(:c AS uuid), 'b', :k, 'ATTORNEY_UPLOAD')"
    ), {"c": str(case_id), "k": f"k-{label}-{uuid.uuid4().hex[:8]}"})
    await conn.execute(text(
        "INSERT INTO trace.providers (case_id, provider_name) "
        "VALUES (CAST(:c AS uuid), :n)"
    ), {"c": str(case_id), "n": f"provider-{label}"})
    return case_id


@pytest.fixture
async def seeded(_setup_db):
    """Seed a minimal two-tenant graph (as superuser) and return ids.

    Explicitly depends on the autouse truncation fixture so seeding ALWAYS
    happens after the per-test truncate (async fixture ordering is not
    guaranteed otherwise).
    """
    ids: dict[str, uuid.UUID] = {}
    async with engine.begin() as conn:
        for firm, label in ((TENANT_A, "a"), (TENANT_B, "b")):
            case_id = await _seed_case(conn, firm, label)
            ids[f"{label}_case"] = case_id

            await conn.execute(text(
                "INSERT INTO trace.firm_users (clerk_user_id, firm_id) "
                "VALUES (:s, CAST(:f AS uuid))"
            ), {"s": f"sub-{label}", "f": firm})

            await conn.execute(text(
                "INSERT INTO trace.business_events (event_id, event_type, "
                "occurred_at, tenant_id, aggregate_type, aggregate_id, "
                "aggregate_version, actor_type, authority_class, "
                "sensitivity_class, schema_version) VALUES (gen_random_uuid(), "
                "'t', NOW(), CAST(:f AS uuid), 'agg', gen_random_uuid(), 1, "
                "'S', 'S', 'INTERNAL', '1.0.1')"
            ), {"f": firm})

            await conn.execute(text(
                "INSERT INTO trace.policy_records (policy_id, tenant_id, "
                "category, name, version, is_active) VALUES (gen_random_uuid(), "
                "CAST(:f AS uuid), 'c', :n, 1, TRUE)"
            ), {"f": firm, "n": f"policy-{label}"})

            await conn.execute(text(
                "INSERT INTO trace.consent_records (consent_id, person_id, "
                "tenant_id, matter_id, consent_type, state, version) VALUES "
                "(gen_random_uuid(), gen_random_uuid(), CAST(:f AS uuid), "
                "CAST(:c AS uuid), 't', 'ACTIVE', 1)"
            ), {"f": firm, "c": str(case_id)})

            await conn.execute(text(
                "INSERT INTO trace.trace_client_access_projections "
                "(projection_id, tenant_id, client_identity_id, matter_id, "
                "relationship_scope, status) VALUES (gen_random_uuid(), "
                "CAST(:f AS uuid), gen_random_uuid(), CAST(:c AS uuid), "
                "'ACTIVE_MATTER', 'ACTIVE')"
            ), {"f": firm, "c": str(case_id)})

            await conn.execute(text(
                "INSERT INTO trace.jurisdiction_profiles (profile_id, "
                "jurisdiction, version, name) VALUES "
                "(gen_random_uuid(), 'CA', '1', :n)"
            ), {"n": f"profile-{label}"})

            await conn.execute(text(
                "INSERT INTO trace.jurisdiction_activations (activation_id, "
                "tenant_id, profile_id, is_active) SELECT gen_random_uuid(), "
                "CAST(:f AS uuid), profile_id, TRUE FROM "
                "trace.jurisdiction_profiles LIMIT 1"
            ), {"f": firm})

            # Case-bound direct
            await conn.execute(text(
                "INSERT INTO trace.liens (case_id, firm_id, lien_type) "
                "VALUES (CAST(:c AS uuid), CAST(:f AS uuid), 'HEALTHCARE')"
            ), {"c": str(case_id), "f": firm})
            await conn.execute(text(
                "INSERT INTO trace.upload_links (case_id, firm_id, created_by, "
                "expires_at) VALUES (CAST(:c AS uuid), CAST(:f AS uuid), "
                "gen_random_uuid(), NOW() + INTERVAL '1 day')"
            ), {"c": str(case_id), "f": firm})
            doc_id = uuid.uuid4()
            await conn.execute(text(
                "INSERT INTO trace.documents (document_id, case_id, s3_bucket, "
                "s3_key, source) VALUES (CAST(:d AS uuid), CAST(:c AS uuid), "
                "'b', :k, 'ATTORNEY_UPLOAD')"
            ), {"d": str(doc_id), "c": str(case_id), "k": f"bill-{label}"})
            await conn.execute(text(
                "INSERT INTO trace.medical_bill_line (case_id, firm_id, "
                "document_id) VALUES (CAST(:c AS uuid), CAST(:f AS uuid), "
                "CAST(:d AS uuid))"
            ), {"c": str(case_id), "f": firm, "d": str(doc_id)})
            await conn.execute(text(
                "INSERT INTO trace.signed_documents (case_id, firm_id, "
                "docuseal_submission_id, document_type) VALUES "
                "(CAST(:c AS uuid), CAST(:f AS uuid), :s, 'HIPAA')"
            ), {"c": str(case_id), "f": firm, "s": f"sub-{label}"})

            # audit_log hybrid (case-bound)
            await conn.execute(text(
                "INSERT INTO trace.audit_log (actor_type, action, resource_type, "
                "case_id, firm_id) VALUES ('SYSTEM', 'seed', 'test', "
                "CAST(:c AS uuid), CAST(:f AS uuid))"
            ), {"c": str(case_id), "f": firm})

            # Evidence chain
            loc = uuid.uuid4()
            await conn.execute(text(
                "INSERT INTO trace.source_locations (location_id, document_id, "
                "page_number, extraction_method) VALUES "
                "(CAST(:l AS uuid), CAST(:d AS uuid), 1, 'MANUAL')"
            ), {"l": str(loc), "d": str(doc_id)})
            fact = uuid.uuid4()
            await conn.execute(text(
                "INSERT INTO trace.evidence_facts (fact_id, case_id, fact_type, "
                "fact_text, source_location_id, review_status, version, "
                "is_contradicted, is_duplicate) VALUES (CAST(:f AS uuid), "
                "CAST(:c AS uuid), 'VISIT', 'x', CAST(:l AS uuid), "
                "'UNREVIEWED', 1, FALSE, FALSE)"
            ), {"f": str(fact), "c": str(case_id), "l": str(loc)})
            await conn.execute(text(
                "INSERT INTO trace.fact_versions (version_id, fact_id, "
                "version_number) VALUES (gen_random_uuid(), CAST(:f AS uuid), 1)"
            ), {"f": str(fact)})

            # Case-derived singles
            await conn.execute(text(
                "INSERT INTO trace.event_nodes (case_id, flag_type, flag_priority, "
                "system_description) VALUES (CAST(:c AS uuid), 'TREATMENT_GAP', 'PRIORITY', 'x')"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.pipeline_audit_log (case_id, stage, "
                "event_type) VALUES (CAST(:c AS uuid), 'OCR', 'RUN')"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.incidents (incident_id, case_id, "
                "incident_type, incident_date) VALUES (gen_random_uuid(), "
                "CAST(:c AS uuid), 'MVA', '2026-01-15')"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.claims (claim_id, case_id, claim_type, "
                "status) VALUES (gen_random_uuid(), CAST(:c AS uuid), 'PI', 'OPEN')"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.injuries (injury_id, case_id, body_region, "
                "injury_type, description, status, is_permanent) VALUES "
                "(gen_random_uuid(), CAST(:c AS uuid), 'NECK', 'STRAIN', 'x', "
                "'ACTIVE', FALSE)"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.symptoms (symptom_id, case_id, description) "
                "VALUES (gen_random_uuid(), CAST(:c AS uuid), 'pain')"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.diagnoses (diagnosis_id, case_id, "
                "diagnosis_text, is_primary) VALUES (gen_random_uuid(), "
                "CAST(:c AS uuid), 'dx', TRUE)"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.treatment_episodes (episode_id, case_id, "
                "episode_type, status) VALUES (gen_random_uuid(), "
                "CAST(:c AS uuid), 'PT', 'ACTIVE')"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.damages_categories (category_id, case_id, "
                "category_type, total_claimed, total_supported) VALUES "
                "(gen_random_uuid(), CAST(:c AS uuid), 'MEDICAL', 0, 0)"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.damages_items (item_id, case_id, "
                "description, amount, status) VALUES (gen_random_uuid(), "
                "CAST(:c AS uuid), 'x', 0, 'OPEN')"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.insurance_policies (policy_id, case_id, "
                "carrier_name) VALUES (gen_random_uuid(), CAST(:c AS uuid), "
                "'CARRIER')"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.insurance_claims (insurance_claim_id, "
                "case_id) VALUES (gen_random_uuid(), CAST(:c AS uuid))"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.coverage_positions (position_id, case_id, "
                "source, coverage_status) VALUES (gen_random_uuid(), "
                "CAST(:c AS uuid), 'CARRIER', 'PENDING')"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.liability_theories (theory_id, case_id, "
                "version, is_active) VALUES (gen_random_uuid(), "
                "CAST(:c AS uuid), 1, TRUE)"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.issues (issue_id, case_id, title, "
                "description, severity, status, blocks_demand_ready) VALUES "
                "(gen_random_uuid(), CAST(:c AS uuid), 't', 'x', 'LOW', "
                "'OPEN', FALSE)"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.demand_drafts (draft_id, case_id, version, "
                "status) VALUES (gen_random_uuid(), CAST(:c AS uuid), 1, 'DRAFT')"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.demand_packages (package_id, case_id, "
                "version, status) VALUES (gen_random_uuid(), CAST(:c AS uuid), "
                "1, 'DRAFT')"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.readiness_assessments (assessment_id, "
                "case_id, milestone, status, total_checks, passed_checks, "
                "failed_checks, waived_checks, blocked_by_issues, "
                "blocked_by_flags) VALUES (gen_random_uuid(), CAST(:c AS uuid), "
                "'M', 'OPEN', 0, 0, 0, 0, 0, 0)"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.record_completeness_assessments "
                "(assessment_id, case_id, total_expected_items, "
                "total_received_items, total_missing_items, completeness_pct) "
                "VALUES (gen_random_uuid(), CAST(:c AS uuid), 0, 0, 0, 0)"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.chain_of_custody_events (event_id, case_id, "
                "document_id, event_type) VALUES (gen_random_uuid(), "
                "CAST(:c AS uuid), CAST(:d AS uuid), 'RECEIVED')"
            ), {"c": str(case_id), "d": str(doc_id)})
            witness = uuid.uuid4()
            await conn.execute(text(
                "INSERT INTO trace.witnesses (witness_id, case_id, full_name, "
                "witness_type) VALUES (CAST(:w AS uuid), CAST(:c AS uuid), "
                ":n, 'PERCIPIENT')"
            ), {"w": str(witness), "c": str(case_id), "n": f"witness-{label}"})
            await conn.execute(text(
                "INSERT INTO trace.witness_statements (statement_id, case_id, "
                "witness_id, statement_type) VALUES (gen_random_uuid(), "
                "CAST(:c AS uuid), CAST(:w AS uuid), 'WRITTEN')"
            ), {"c": str(case_id), "w": str(witness)})
            await conn.execute(text(
                "INSERT INTO trace.record_requests (case_id, provider_id, "
                "fax_number) SELECT CAST(:c AS uuid), provider_id, '5550000' "
                "FROM trace.providers WHERE case_id = CAST(:c AS uuid) LIMIT 1"
            ), {"c": str(case_id)})
            await conn.execute(text(
                "INSERT INTO trace.chronology_entries (case_id, event_date, "
                "event_type, clinical_description, source_document_id, "
                "source_page_number) VALUES (CAST(:c AS uuid), NOW(), 'VISIT', "
                "'x', CAST(:d AS uuid), 1)"
            ), {"c": str(case_id), "d": str(doc_id)})
            await conn.execute(text(
                "INSERT INTO trace.missing_evidence_signals (signal_id, "
                "case_id, signal_type, days_overdue) VALUES (gen_random_uuid(), "
                "CAST(:c AS uuid), 'MISSING_RECORD', 3)"
            ), {"c": str(case_id)})
            fact2 = uuid.uuid4()
            await conn.execute(text(
                "INSERT INTO trace.evidence_facts (fact_id, case_id, fact_type, "
                "fact_text, source_location_id, review_status, version, "
                "is_contradicted, is_duplicate) VALUES (CAST(:f AS uuid), "
                "CAST(:c AS uuid), 'VISIT', 'y', CAST(:l AS uuid), "
                "'UNREVIEWED', 1, FALSE, FALSE)"
            ), {"f": str(fact2), "c": str(case_id), "l": str(loc)})
            await conn.execute(text(
                "INSERT INTO trace.contradiction_pairs (contradiction_id, "
                "case_id, fact_a_id, fact_b_id, contradiction_type, "
                "resolution_status) VALUES (gen_random_uuid(), CAST(:c AS uuid), "
                "CAST(:a AS uuid), CAST(:b AS uuid), 'CLINICAL', 'UNRESOLVED')"
            ), {"c": str(case_id), "a": str(fact), "b": str(fact2)})

            ids[f"{label}_doc"] = doc_id
            ids[f"{label}_fact"] = fact
            ids[f"{label}_loc"] = loc
    return ids


# ─────────────────────────────────────────────────────────────────────
# A. Manifest completeness + structural RLS
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_manifest_completeness():
    async with engine.connect() as conn:
        physical = {r[0] for r in (await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='trace'"
        ))).fetchall()}
    tenant = set(TENANT_TABLES)
    global_ref = set(GLOBAL_REFERENCE)
    internal = set(NON_TENANT_INTERNAL)
    unclassified = physical - tenant - global_ref - internal
    assert len(physical) == 45, f"physical={len(physical)}"
    assert len(tenant) == 43
    assert unclassified == set(), f"unclassified tables: {unclassified}"


@pytest.mark.asyncio
async def test_structural_rls_on_all_tenant_tables():
    async with engine.connect() as conn:
        for table in TENANT_TABLES:
            row = (await conn.execute(text(
                "SELECT c.relrowsecurity, c.relforcerowsecurity "
                "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname='trace' AND c.relname=:t"
            ), {"t": table})).first()
            assert row is not None, f"{table} missing"
            assert row[0] is True, f"{table}: RLS not enabled"
            assert row[1] is True, f"{table}: RLS not forced"

            policies = (await conn.execute(text(
                "SELECT policyname, cmd, qual IS NOT NULL, with_check IS NOT NULL "
                "FROM pg_policies WHERE schemaname='trace' AND tablename=:t"
            ), {"t": table})).fetchall()
            assert [p[0] for p in policies] == [CANONICAL_POLICY], (
                f"{table}: policies={policies}"
            )
            name, cmd, qual, with_check = policies[0]
            assert cmd == "ALL", f"{table}: cmd={cmd}"
            assert qual, f"{table}: missing USING"
            assert with_check, f"{table}: missing WITH CHECK"


@pytest.mark.asyncio
async def test_no_tenant_policy_on_global_or_internal():
    async with engine.connect() as conn:
        for table in (*GLOBAL_REFERENCE, *NON_TENANT_INTERNAL):
            policies = (await conn.execute(text(
                "SELECT count(*) FROM pg_policies "
                "WHERE schemaname='trace' AND tablename=:t"
            ), {"t": table})).scalar()
            assert policies == 0, f"{table} has tenant policies"
        row = (await conn.execute(text(
            "SELECT relrowsecurity FROM pg_class c "
            "JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='trace' AND c.relname='jurisdiction_profiles'"
        ))).scalar()
        assert row is False


# ─────────────────────────────────────────────────────────────────────
# C/D. Two-tenant visibility
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cross_tenant_select_denial_named_tables(seeded):
    named = (
        "cases", "liens", "medical_bill_line", "evidence_facts",
        "source_locations", "fact_versions", "business_events",
        "consent_records", "trace_client_access_projections", "audit_log",
        "record_requests", "pipeline_audit_log", "firm_users",
        "jurisdiction_activations",
    )
    for table in named:
        async with tenant_role_session(TENANT_A) as session:
            rows = (await session.execute(text(
                f"SELECT count(*) FROM trace.{table}"
            ))).scalar()
            assert rows > 0, f"{table}: tenant A sees nothing"
    async with tenant_role_session(TENANT_A) as session:
        b_cases = (await session.execute(text(
            "SELECT count(*) FROM trace.cases WHERE firm_id = CAST(:f AS uuid)"
        ), {"f": TENANT_B})).scalar()
        assert b_cases == 0


@pytest.mark.asyncio
async def test_table_driven_visibility_smoke(seeded):
    for firm in (TENANT_A, TENANT_B):
        async with tenant_role_session(firm) as session:
            for table in TENANT_TABLES:
                rows = (await session.execute(text(
                    f"SELECT count(*) FROM trace.{table}"
                ))).scalar()
                assert rows > 0, f"{table}: {firm[:4]} sees no own rows"


# ─────────────────────────────────────────────────────────────────────
# E. Cross-tenant INSERT denial
# ─────────────────────────────────────────────────────────────────────

async def _expect_rls_denial(session, firm: str, stmt, params):
    with pytest.raises(Exception) as exc_info:
        await session.execute(text(stmt), params)
    await session.rollback()
    assert "row-level security" in str(exc_info.value).lower()
    # SET LOCAL ROLE is transaction-local: re-establish after the rollback so
    # subsequent assertions in this session still run as the non-bypass role.
    await session.execute(text(f"SET LOCAL ROLE {TEST_ROLE}"))
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :t, true)"),
        {"t": firm},
    )


@pytest.mark.asyncio
async def test_cross_tenant_insert_denial(seeded):
    b_case = seeded["b_case"]

    async with tenant_role_session(TENANT_A) as session:
        await _expect_rls_denial(session, TENANT_A,
            "INSERT INTO trace.cases (client_token, firm_id, intake_record_id, "
            "incident_date, jurisdiction_state) VALUES (gen_random_uuid(), "
            "CAST(:f AS uuid), gen_random_uuid(), '2026-01-15', 'CA')",
            {"f": TENANT_B})
        await _expect_rls_denial(session, TENANT_A,
            "INSERT INTO trace.business_events (event_id, event_type, "
            "occurred_at, tenant_id, aggregate_type, aggregate_id, "
            "aggregate_version, actor_type, authority_class, "
            "sensitivity_class, schema_version) VALUES (gen_random_uuid(), "
            "'t', NOW(), CAST(:f AS uuid), 'agg', gen_random_uuid(), 1, "
            "'S', 'S', 'INTERNAL', '1.0.1')",
            {"f": TENANT_B})
        await _expect_rls_denial(session, TENANT_A,
            "INSERT INTO trace.liens (case_id, firm_id, lien_type) VALUES "
            "(CAST(:c AS uuid), CAST(:f AS uuid), 'HEALTHCARE')",
            {"c": str(b_case), "f": TENANT_A})
        await _expect_rls_denial(session, TENANT_A,
            "INSERT INTO trace.event_nodes (case_id, flag_type, flag_priority, "
            "system_description) VALUES (CAST(:c AS uuid), 'TREATMENT_GAP', 'PRIORITY', 'x')",
            {"c": str(b_case)})
        await _expect_rls_denial(session, TENANT_A,
            "INSERT INTO trace.evidence_facts (fact_id, case_id, fact_type, "
            "fact_text, source_location_id, review_status, version, "
            "is_contradicted, is_duplicate) VALUES (gen_random_uuid(), "
            "CAST(:c AS uuid), 'VISIT', 'x', CAST(:l AS uuid), 'UNREVIEWED', "
            "1, FALSE, FALSE)",
            {"c": str(b_case), "l": str(seeded["a_loc"])})
        await _expect_rls_denial(session, TENANT_A,
            "INSERT INTO trace.consent_records (consent_id, person_id, "
            "tenant_id, matter_id, consent_type, state, version) VALUES "
            "(gen_random_uuid(), gen_random_uuid(), CAST(:f AS uuid), "
            "CAST(:c AS uuid), 't', 'ACTIVE', 1)",
            {"f": TENANT_A, "c": str(b_case)})


# ─────────────────────────────────────────────────────────────────────
# F/G. Cross-tenant UPDATE/DELETE denial
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cross_tenant_update_denial(seeded):
    b_case = seeded["b_case"]
    async with tenant_role_session(TENANT_A) as session:
        updated = (await session.execute(text(
            "UPDATE trace.cases SET case_stage='DEMAND_READY' "
            "WHERE case_id = CAST(:c AS uuid)"
        ), {"c": str(b_case)})).rowcount
        assert updated == 0

        with pytest.raises(Exception) as exc_info:
            await session.execute(text(
                "UPDATE trace.liens SET case_id = CAST(:b AS uuid) "
                "WHERE firm_id = CAST(:a AS uuid)"
            ), {"b": str(b_case), "a": TENANT_A})
        assert "row-level security" in str(exc_info.value).lower()
        await session.rollback()


@pytest.mark.asyncio
async def test_cross_tenant_delete_denial(seeded):
    b_case = seeded["b_case"]
    async with tenant_role_session(TENANT_A) as session:
        deleted = (await session.execute(text(
            "DELETE FROM trace.event_nodes WHERE case_id = CAST(:c AS uuid)"
        ), {"c": str(b_case)})).rowcount
        assert deleted == 0


@pytest.mark.asyncio
async def test_same_tenant_crud_succeeds(seeded):
    a_case = seeded["a_case"]
    async with tenant_role_session(TENANT_A) as session:
        await session.execute(text(
            "INSERT INTO trace.event_nodes (case_id, flag_type, flag_priority, "
            "system_description) VALUES (CAST(:c AS uuid), 'TREATMENT_GAP', 'PRIORITY', 'own')"
        ), {"c": str(a_case)})
        await session.commit()
    async with tenant_role_session(TENANT_A) as session:
        rows = (await session.execute(text(
            "SELECT count(*) FROM trace.event_nodes "
            "WHERE case_id = CAST(:c AS uuid)"
        ), {"c": str(a_case)})).scalar()
        assert rows >= 1
        await session.execute(text(
            "DELETE FROM trace.event_nodes WHERE case_id = CAST(:c AS uuid)"
        ), {"c": str(a_case)})
        await session.commit()


# ─────────────────────────────────────────────────────────────────────
# H/I. Missing-context fail closed + GUC pool reset
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_missing_context_fails_closed(seeded):
    async with tenant_role_session(None) as session:
        for table in TENANT_TABLES:
            rows = (await session.execute(text(
                f"SELECT count(*) FROM trace.{table}"
            ))).scalar()
            assert rows == 0, f"{table}: visible without tenant context"
        with pytest.raises(Exception) as exc_info:
            await session.execute(text(
                "INSERT INTO trace.cases (client_token, firm_id, "
                "intake_record_id, incident_date, jurisdiction_state) VALUES "
                "(gen_random_uuid(), CAST(:f AS uuid), gen_random_uuid(), "
                "'2026-01-15', 'CA')"
            ), {"f": TENANT_A})
        assert "row-level security" in str(exc_info.value).lower()

    async with tenant_role_session(None) as session:
        await session.execute(text(
            "SELECT set_config('app.current_tenant_id', '', true)"
        ))
        rows = (await session.execute(text(
            "SELECT count(*) FROM trace.cases"
        ))).scalar()
        assert rows == 0


@pytest.mark.asyncio
async def test_guc_is_transaction_local_no_pool_leak(seeded):
    async with tenant_role_session(TENANT_A) as session:
        a = (await session.execute(text(
            "SELECT count(*) FROM trace.cases"
        ))).scalar()
        assert a > 0
    async with tenant_role_session(None) as session:
        none_rows = (await session.execute(text(
            "SELECT count(*) FROM trace.cases"
        ))).scalar()
        assert none_rows == 0
    async with tenant_role_session(TENANT_B) as session:
        b = (await session.execute(text(
            "SELECT count(*) FROM trace.cases"
        ))).scalar()
        assert b > 0


# ─────────────────────────────────────────────────────────────────────
# J/K. Global reference + audit invariants + role flags
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_global_reference_visible_to_both_tenants(seeded):
    for firm in (TENANT_A, TENANT_B):
        async with tenant_role_session(firm) as session:
            rows = (await session.execute(text(
                "SELECT count(*) FROM trace.jurisdiction_profiles"
            ))).scalar()
            assert rows >= 1


@pytest.mark.asyncio
async def test_audit_log_insert_only_for_app_role(seeded):
    a_case = seeded["a_case"]
    async with tenant_role_session(TENANT_A) as session:
        await session.execute(text(
            "INSERT INTO trace.audit_log (actor_type, action, resource_type, "
            "case_id, firm_id) VALUES ('SYSTEM', 'fnd003', 'test', "
            "CAST(:c AS uuid), CAST(:f AS uuid))"
        ), {"c": str(a_case), "f": TENANT_A})
        await session.commit()

    # UPDATE / DELETE denied by privilege for the application role.
    async with tenant_role_session(TENANT_A) as session:
        with pytest.raises(Exception) as exc_info:
            await session.execute(text(
                "UPDATE trace.audit_log SET action='tampered' "
                "WHERE action='fnd003'"
            ))
        assert "permission denied" in str(exc_info.value).lower()

    async with tenant_role_session(TENANT_A) as session:
        with pytest.raises(Exception) as exc_info:
            await session.execute(text(
                "DELETE FROM trace.audit_log WHERE action='fnd003'"
            ))
        assert "permission denied" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_adversarial_role_is_non_bypass():
    async with tenant_role_session(TENANT_A) as session:
        user = (await session.execute(text("SELECT current_user"))).scalar()
        assert user == TEST_ROLE
        flags = (await session.execute(text(
            "SELECT rolsuper, rolbypassrls FROM pg_roles "
            "WHERE rolname = current_user"
        ))).first()
        assert flags == (False, False)


# ─────────────────────────────────────────────────────────────────────
# GUC parameterization (get_db hardening)
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_db_sets_gucs_via_set_config():
    from dataclasses import dataclass

    from app.core.database import get_db

    @dataclass
    class _Ctx:
        firm_id: str
        user_id: str
        role: str | None

    gen = get_db(_Ctx(firm_id=TENANT_A, user_id="user-1", role="attorney"))
    session = await anext(gen)
    try:
        tenant = (await session.execute(text(
            "SELECT current_setting('app.current_tenant_id', true)"
        ))).scalar()
        assert tenant == TENANT_A
        role = (await session.execute(text(
            "SELECT current_setting('app.current_user_role', true)"
        ))).scalar()
        assert role == "attorney"
    finally:
        await session.rollback()
        await session.close()
