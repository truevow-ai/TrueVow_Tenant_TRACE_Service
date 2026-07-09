# TRACE — Platform-Grounded Architecture Decisions (ADR-000)

**Purpose:** Reconcile the TRACE PRD + Technical Spec against the **actual TrueVow platform** as it exists in the codebase today. Where the spec's `[DECISION LOCKED]` assumptions diverge from platform reality, this document records the grounded decision and flags anything that requires product-owner / Privacy-Officer sign-off (the spec requires written approval to deviate from Section 2).

**Method:** Direct codebase exploration of INTAKE (Tenant Application Service), SETTLE, Billing, Financial Management, and shared-libraries. Evidence-based; file paths cited inline.

**Status:** Proposed — for review. Supersedes the stack table in `TRACE-Phase1A-Confirmation.md` where reality differs.

---

## A. Spec assumption vs. platform reality

| Concern | TRACE spec says | Platform reality (evidence) | Grounded decision |
|--------|-----------------|-----------------------------|-------------------|
| **Auth** | Auth0 + MFA `[LOCKED]` | **Clerk**, everywhere. 3-domain arch in `.env.local`; `TrueVow_Tenant_Application_Service/app/middleware/auth.py` (JWKS RS256), `clerk_auth.py` (MFA via `two_factor_enabled`). **Zero Auth0 usage.** | **Use Clerk** (App 3 "TrueVow-Tenants", attorney-facing). MFA already supported. **⚠ Requires sign-off — deviates from a LOCKED decision.** |
| **App DB** | PostgreSQL 15 (RDS) | Supabase Postgres + SQLAlchemy 2.0 async + asyncpg + Alembic; RLS via GUC `app.current_tenant_id` (FM `app/core/database.py`). `tenant_id = Clerk org_id`. | **Supabase Postgres, follow FM's async+Alembic+RLS-GUC pattern.** Pooler URL, `statement_cache_size=0`. |
| **Object storage** | AWS S3 + SSE-KMS `[IMPLEMENTATION CHOICE]` | **S3 already in use** — `TrueVow_Tenant_SETTLE-Service/app/services/storage/s3_service.py` (boto3, presigned URLs, SSE-AES256, mock mode, `us-west-2`). *(Corrects my earlier "no existing object storage" flag.)* | **Supabase Storage** (supabase-py SDK, private bucket, 15-min signed URLs, existing BAA). Self-hosted alt (MinIO) evaluated but deferred to Phase 2+ — adds ops burden without quality win for Phase 1. |
| **Audit / logs** | AWS CloudWatch `[IMPLEMENTATION CHOICE]` | **SigNoz (OTEL) + Sentry**, not CloudWatch. `shared-libraries/observability/python/otel_init.py`, `sentry/python/sentry_init.py`. | **HIPAA audit = append-only `audit_log` table (INSERT-only role) + pgaudit** (the durable 6-yr record). **APM/errors = OTEL→SigNoz + Sentry** (platform standard). No CloudWatch. |
| **SOL engine** | Build own 50-state `SOL_TABLE` in code (spec §5.4) | INTAKE already persists an SOL snapshot per case (`statute_jurisdiction_state`, `statute_sol_years`, `statute_reference`, `statute_valid_from`) and ships **23 jurisdiction JSON files** with per-practice-area SOL (`app/services/jurisdictions/*.json`). | **Reuse INTAKE's jurisdiction data + persisted statute snapshot.** Do not maintain a duplicate hardcoded table. TRACE reads the snapshot from the intake record; falls back to the shared jurisdiction JSON. Single source of truth, attorney-reviewed. |
| **Retainer trigger** | INTAKE calls `POST /trace/cases` directly (spec §4.2) | INTAKE uses an **outbox/domain-event** pattern: `engagement_letter_signed` boolean on `intake_sessions` + `OutboxEvent` table + `CaseCreated` event (`app/events/case_events.py`). No `cases` table exists yet. | **TRACE subscribes to the INTAKE outbox** (`case.created` / `engagement_letter_signed → true`) rather than being invoked synchronously. Keeps INTAKE decoupled; matches existing platform event flow. |
| **Billing LLM** | Spec updated to LLM-agnostic `[IMPLEMENTATION CHOICE]` via `LLMService` abstraction + `LLM_SERVICE_PROVIDER` env var | No Azure usage in platform; production is air-gapped and runs DeepSeek V4 Pro internally. | **LLM-agnostic via `LLMService` abstraction** (pluggable backend). Production: DeepSeek V4 Pro (air-gapped, no BAA needed). Cloud dev/staging: any BAA-covered provider selected via env var. No platform conflict. |
| **OCR** | AWS Textract (cross-cloud OK) | SETTLE uses boto3/S3; production is air-gapped and cannot call cloud OCR. | **Hybrid: deepdoctection + DocTr (Tier 1, air-gapped) + LlamaParse (Tier 2, cloud, handwriting only).** Via `OCRService` abstraction. Self-hosted alt (deepdoctection) selected; cloud alt (LlamaParse/Textract) for handwritten/low-confidence pages only. |
| **Cloud Fax** | Fax.Plus Enterprise | BAA signed, HIPAA mode, webhooks. Self-hosted alt (ICTFax + SIP trunk) evaluated and deferred — still requires third-party SIP provider, adds significant ops burden, reliability drops without T.38. | **Keep Fax.Plus Enterprise.** Self-hosted fax does not eliminate third-party dependency; managed BAA-covered service is safer for Phase 1 early access. |
| **Migrations / tests / lint** | "migrations", pytest implied | Alembic (FM programmatic RLS in migration 010); pytest + pytest-asyncio + **SQLite in-memory fallback** (`tests/conftest.py`); ruff+mypy at truth-loop level. | **Alembic, pytest+asyncio with SQLite fallback, ruff+mypy.** The SQLite fallback is how Phase 1A acceptance tests run locally without live cloud. |
| **Hosting** | AWS us-east-1/us-west-2 | **Fly.io** (`fly.toml`, `primary_region='iad'`) + Docker; service registry via Internal Ops. | **Fly.io + Dockerfile**, matching platform (per your "amend spec for Fly.io+Supabase"). |
| **PHI store** | Separate encrypted PG instance (pgcrypto/KMS) | No existing separate-PHI-store precedent; INTAKE keeps caller PII in `intake_sessions` under RLS + data-residency middleware. | **Net-new for TRACE:** separate Supabase project/instance for the `clients` PHI table (pgcrypto AES-256), referenced only by opaque `client_token` from the operational DB. Keep as specّd — TRACE's HIPAA bar is higher than INTAKE's. |

---

## B. The ICD/CPT medical-billing data decision (your explicit question)

**Question posed:** put extracted ICD/CPT medical-billing data in the **billing DB** (new schema) or the **FM DB** (new schema)?

**Findings:**
- Neither DB uses multiple Postgres schemas today — everything is `public`. A new schema is net-new in either.
- **Billing DB** isolates by `tenant_id` (= attorney firm) — semantically matches "per-firm medical bill." RLS partial (Growth-Tier only).
- **FM DB** isolates by `legal_entity_id` (= TrueVow's own corporate entities) — does **not** map to attorney firms; would need a mapping layer. Cleanest RLS pattern, but wrong tenancy model for this data.
- Both are **TrueVow's financial systems** (SaaS revenue / corporate accounting). The PI client's CPT/ICD is **PHI**, not TrueVow finance.

**Decision (FINAL — everything medical is self-contained in TRACE):**

The billing DB is the single source of truth for **SaaS subscriptions + metering**; a medical CPT/ICD catalog does not belong in that bounded context. FM is corporate double-entry accounting keyed by `legal_entity_id` — also the wrong context. TRACE is the near-exclusive, high-frequency consumer of the catalog. Therefore both the PHI and the reference catalog live in **TRACE's own database**:

1. **Per-case, per-client extracted medical bill lines (PHI) → TRACE operational DB** as `event_nodes` (billing-discrepancy flags) + a `medical_bill_line` table, firm-segmented by RLS `app.current_tenant_id`. Never in billing/FM (HIPAA segmentation).

2. **Non-PHI CPT/ICD reference catalog** (code → description → documentation-requirement mapping) → **TRACE operational DB** as versioned reference tables (`cpt_reference`, `icd10_reference`, with a `code_set_version` column). Rationale: (a) TRACE is the primary consumer — billing reconciliation iterates bills and looks up CPT requirements in a tight loop; co-location avoids cross-service latency; (b) keeps the billing DB pure (subscriptions/metering) and FM pure (corporate finance); (c) the catalog FKs naturally to `medical_bill_line`; (d) TRACE owns the catalog's annual-review versioning lifecycle (mandated for SOL/CPT reference data).

3. **Extraction** uses the temporary spaCy CPT/ICD fallback from faxed BILLING documents (per prior decision), marked TODO — no rebuild of billing logic.

**Net:** TRACE owns the medical domain end-to-end; **billing and FM schemas are untouched.** The only cross-service touchpoint remains the eventual §5.6 reconciliation, which uses the temp in-TRACE fallback until a real medical-billing source exists.

---

## C. Deviations from `[DECISION LOCKED]` Section 2 — APPROVED

Product-owner approved (2026-07-08). Record for the Privacy-Officer file per the spec's deviation rule:

1. **Auth0 → Clerk** ✅ APPROVED — TRACE joins Clerk App 3 "TrueVow-Tenants."
2. **S3 SSE-AES256 → SSE-KMS + AWS BAA** ✅ APPROVED — dedicated KMS-encrypted, BAA-covered PHI bucket for TRACE.
3. **CloudWatch → SigNoz/pgaudit/`audit_log` table** ✅ APPROVED — platform-standard observability + append-only DB audit.

---

## D. Resolved (formerly outstanding)

All items below are resolved. The consolidated architecture is documented in **ADR-001 — Phase 1 Architecture Plan**, which supersedes this document for all decisions after ADR-000.

- **PRD §12** — confirmed at 12 questions. Questions 10–12 added under "Architecture" header.
- **Amended spec** — Fly.io+Supabase `[IMPLEMENTATION CHOICE]` applied to File Storage, Infrastructure, and Audit Logging sections.
- **LLM backend** — updated to LLM-agnostic via `LLMService` abstraction. DeepSeek V4 Pro is the current production backend (air-gapped). No prohibition remains.
- **ADR-001** — consolidated Phase 1 architecture plan including: end-to-end data flow with PHI boundaries, service abstraction layer, processing pipeline stages with tool assignments, deployment topology, and all 20 decisions since ADR-000.
