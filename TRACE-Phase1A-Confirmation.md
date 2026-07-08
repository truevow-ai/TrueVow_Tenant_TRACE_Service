# TRACE — Phase 1A Confirmation Document (v2 — Platform-Grounded)

**Purpose:** Confirmation of build decisions for review **before** the first line of Phase 1A code is written.
**Source of truth:** TRACE PRD v0.1 + Technical Spec (revised) + **`TRACE-Architecture-Decisions.md` (ADR-000)**, which reconciles the spec against the actual TrueVow platform.
**Status:** v2 supersedes v1. All three LOCKED-decision deviations were **product-owner approved (2026-07-08)**. Phase 1B will not start until Phase 1A acceptance criteria pass.

---

## 1. Technology Stack — Per Component (platform-grounded)

| Component | Technology | Source / rationale |
|-----------|-----------|--------------------|
| Backend API | **Python 3.11 / FastAPI** (async) + uvicorn | Spec LOCKED + matches every TrueVow service |
| Operational DB | **Supabase PostgreSQL** + SQLAlchemy 2.0 async + asyncpg | Platform standard (FM pattern); pooler URL, `statement_cache_size=0` |
| Multi-tenancy | **RLS via GUC** `app.current_tenant_id` (= Clerk `org_id`) + `app.current_user_id/role/correlation_id` | FM `app/core/database.py` pattern |
| PHI store | **Separate Supabase instance/project**, pgcrypto AES-256 columns; referenced only by opaque `client_token` | Spec LOCKED; net-new to platform (TRACE's HIPAA bar) |
| File storage | **AWS S3 via boto3**, wrapped in a `StorageService` interface; **SSE-KMS (customer-managed key) + AWS BAA** | Follows SETTLE `app/services/storage/s3_service.py`; upgraded to KMS+BAA for PHI ✅approved |
| Document access | **Pre-signed S3 URLs, 15-min expiry** → PDF.js in browser | Bytes never through app server |
| OCR | **AWS Textract** (cross-cloud API) | Spec LOCKED; AWS BAA (same as S3) |
| Cloud fax | **Fax.Plus Enterprise** (BAA, HIPAA mode, webhooks) | Spec LOCKED |
| Clinical NLP | **spaCy + scispaCy `en_core_sci_md`**, in-infra | Spec LOCKED; no PHI to external NLP |
| Billing-recon LLM | **Azure OpenAI GPT-4o-mini** (BAA, PHI-stripped input) | Spec LOCKED; **DeepSeek prohibited (any version)** |
| Frontend | **React 18 + TypeScript** + **PDF.js** | Spec LOCKED |
| Authentication | **Clerk + MFA** (App 3 "TrueVow-Tenants"), JWKS RS256; service-to-service scoped tokens | ✅approved — **replaces Auth0**; platform-wide standard |
| Audit / logs | **Append-only `audit_log` table (INSERT-only role) + pgaudit** (HIPAA 6-yr) · **OTEL→SigNoz + Sentry** (APM/errors) | ✅approved — **replaces CloudWatch** |
| Secrets | **Fly.io secrets / `.env.local`** (no secrets in code) | Platform standard |
| Hosting / deploy | **Fly.io** (`fly.toml`, region `iad`) + Dockerfile; register with Internal Ops service registry | Platform standard |
| Migrations / tests / lint | **Alembic** · **pytest + pytest-asyncio + SQLite in-memory fallback** · **ruff + mypy** | Platform standard (FM/SETTLE) |

**Grounded reuse (no rebuild):**
- **SOL** — reuse INTAKE's persisted statute snapshot (`intake_sessions.statute_*`) + 23 jurisdiction JSON files (`app/services/jurisdictions/*.json`). No duplicate hardcoded SOL table.
- **Retainer trigger** — subscribe to INTAKE **outbox** (`CaseCreated` / `engagement_letter_signed`), not a synchronous INTAKE→TRACE POST.

**Prohibited:** local LLMs, DeepSeek API (any version), any LLM without a BAA, Streamlit, Docspell, DICOM/Orthanc/OHIF, flat-file case storage, localStorage/IndexedDB, regex-only billing-code extraction, rebuilding billing extraction.

---

## 2. The Three Database Roles

| Role | Granted | Denied |
|------|---------|--------|
| **`trace_app_role`** | SELECT/INSERT/UPDATE on `cases`, `providers`, `documents`, `chronology_entries`, `event_nodes`, `medical_bill_line`, `cpt_reference`, `icd10_reference`; **INSERT-only** on `audit_log` | No SELECT/UPDATE/DELETE on `audit_log`; no `clients` (PHI); no DELETE on operational tables |
| **`trace_phi_role`** | SELECT/INSERT/UPDATE on `clients` (PHI store) | Never open by default — elevated only for a specific attorney-authenticated PHI read |
| **`trace_readonly_role`** | SELECT on operational tables | No `audit_log`; no `clients` |

Invariants: `audit_log` append-only; PHI only via `trace_phi_role`; all tables firm-segmented by RLS. (`medical_bill_line`, `cpt_reference`, `icd10_reference` are TRACE-owned per ADR-000 — billing/FM untouched.)

---

## 3. First Five API Endpoints (in order)

Base `/api/v1/trace/`. Every endpoint: valid **Clerk** JWT, firm-scoped (Clerk `org_id`), writes an `audit_log` row before responding.

| # | Endpoint | Purpose | Gate |
|---|----------|---------|------|
| 1 | `POST /cases` | Case init — encrypt PII→PHI store, create case, resolve SOL from INTAKE snapshot, subscribe/trigger provider extraction | incident_date not future; valid state; 409 on duplicate `intake_record_id` |
| 2 | `GET /cases/{case_id}/providers` | List extracted providers for review | firm-scoped; low-confidence labeled |
| 3 | `PUT /cases/{case_id}/providers/{id}` | Edit a provider | only while not LOCKED |
| 4 | `POST /cases/{case_id}/providers` | Add a provider | captures name/facility/fax/address/specialty/dates |
| 5 | `POST /cases/{case_id}/providers/confirm` | **Checkpoint 1** — lock list, `provider_list_status=CONFIRMED`, timestamp+attorney, audit snapshot | ≥1 CONFIRMED; **no fax sent** |

Phase 1A skeleton also ships a protected `/health`/readiness endpoint solely to validate the Clerk + audit middleware acceptance criteria.

---

## 4. Phase 1A Deliverables & Acceptance

**I will produce (no live-cloud dependency):**
- Git repo initialized; structure matching platform (`app/` layout, `infra/database/migrations`, `tests/`).
- FastAPI skeleton: **Clerk JWKS middleware** + `correlation_id`/`audit_context` middleware + plain-English error handling; `/health`.
- Section 3.1 schema + **Alembic** migrations (operational + PHI store) + Section 3.2 roles/RLS; `otel_init`/`sentry_init` from shared-libraries.
- `StorageService` interface (S3 impl stub) + `Dockerfile` + `fly.toml` (region `iad`).
- **pytest + SQLite in-memory fallback** so acceptance tests run locally without cloud.

**Left to your team:** real Fly.io app + Supabase projects (operational + PHI), Clerk App-3 keys, AWS BAA + KMS bucket, Fax.Plus creds — supplied via Fly secrets.

**Phase 1A acceptance (gate to 1B):** authenticated API call logged in `audit_log` (actor_id/timestamp/action); unauthenticated → 401; firm A cannot read firm B.

---

**Blockers cleared:** PRD §12 confirmed at 9 questions; the three architectural questions (cloud provider, LLM BAA, billing repo) are resolved in ADR-000. *Awaiting your go-ahead to begin Phase 1A.*
