# TRACE — Phase 1A Confirmation Document (v3 — Architecture Plan Referenced)

**Purpose:** Confirmation of build decisions for review **before** the first line of Phase 1A code is written.
**Source of truth:** TRACE PRD v0.1 + Technical Spec (revised) + **ADR-001 (Phase 1 Architecture Plan)** — consolidated architecture supersedes all prior decision documents.
**Status:** v3 — all architectural decisions finalized. Phase 1B will not start until Phase 1A acceptance criteria pass.

---

## 1. Technology Stack — Per Component (platform-grounded)

| Component | Technology | Source / rationale |
|-----------|-----------|--------------------|
| Backend API | **Python 3.11 / FastAPI** (async) + uvicorn | Spec LOCKED + matches every TrueVow service |
| Operational DB | **Supabase PostgreSQL** + SQLAlchemy 2.0 async + asyncpg | Platform standard (FM pattern); pooler URL, `statement_cache_size=0` |
| Multi-tenancy | **RLS via GUC** `app.current_tenant_id` (= Clerk `org_id`) + `app.current_user_id/role/correlation_id` | FM `app/core/database.py` pattern |
| PHI store | **Separate Supabase instance/project**, pgcrypto AES-256 columns; referenced only by opaque `client_token` | Spec LOCKED; net-new to platform (TRACE's HIPAA bar) |
| File storage | **Supabase Storage** (supabase-py SDK); self-hosted alt: MinIO (evaluated — deferred to Phase 2+); SSE-KMS + BAA | Platform standard; private bucket, 15-min signed URLs; MinIO adds ops burden without clear quality win for Phase 1 |
| Document access | **Pre-signed S3 URLs, 15-min expiry** → PDF.js in browser | Bytes never through app server |
| OCR | **Hybrid: deepdoctection + DocTr (Tier 1, air-gapped) + LlamaParse (Tier 2, cloud, BAA, handwriting only)** | Spec updated to `[IMPLEMENTATION CHOICE]`; local-first with cloud escalation for handwritten/low-confidence pages only |
| Cloud fax | **Fax.Plus Enterprise** (BAA signed, HIPAA mode, webhooks); alt: ICTFax (evaluated — deferred to Phase 2+) | ICTFax still requires SIP trunk provider; self-hosted fax does not eliminate third-party; Fax.Plus is managed + BAA-covered |
| Clinical NLP + PHI de-ID | **OpenMed** (self-hosted, Apache-2.0); 1,000+ clinical models, HIPAA de-identification built-in, Docker REST service | Spec updated to `[IMPLEMENTATION CHOICE]`; replaces scispaCy (1 model → 1,000+ specialized models); no PHI to external APIs |
| Billing-recon LLM | **LLM-agnostic via `LLMService` abstraction**; `LLM_SERVICE_PROVIDER` env var selects backend | Spec updated to `[IMPLEMENTATION CHOICE]`; production default: DeepSeek V4 Pro (air-gapped, no BAA needed); cloud dev/staging: BAA-covered provider |
| Frontend | **React 18 + TypeScript** + **PDF.js** | Spec LOCKED |
| Authentication | **Clerk + MFA** (App 3 "TrueVow-Tenants"), JWKS RS256; service-to-service scoped tokens | ✅approved — **replaces Auth0**; platform-wide standard |
| Audit / logs | **Append-only `audit_log` table (INSERT-only role) + pgaudit** (HIPAA 6-yr) · **OTEL→SigNoz + Sentry** (APM/errors) | ✅approved — **replaces CloudWatch** |
| Secrets | **Fly.io secrets / `.env.local`** (no secrets in code) | Platform standard |
| Hosting / deploy | **Fly.io** (`fly.toml`, region `iad`) + Dockerfile; register with Internal Ops service registry | Platform standard |
| Migrations / tests / lint | **Alembic** · **pytest + pytest-asyncio + SQLite in-memory fallback** · **ruff + mypy** | Platform standard (FM/SETTLE) |

**Grounded reuse (no rebuild):**
- **SOL** — reuse INTAKE's persisted statute snapshot (`intake_sessions.statute_*`) + 23 jurisdiction JSON files (`app/services/jurisdictions/*.json`). No duplicate hardcoded SOL table.
- **Retainer trigger** — subscribe to INTAKE **outbox** (`CaseCreated` / `engagement_letter_signed`), not a synchronous INTAKE→TRACE POST.

**Prohibited:** local LLMs on unmanaged hardware (developer laptops) with real case data, any cloud LLM without a BAA (non-air-gapped environments only), Streamlit, Docspell, DICOM/Orthanc/OHIF, flat-file case storage, localStorage/IndexedDB, regex-only billing-code extraction, rebuilding billing extraction. **Note:** DeepSeek V4 Pro is the current production LLM backend — it is not prohibited. It runs air-gapped inside TrueVow's infrastructure boundary.

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

**Blockers cleared:** PRD §12 confirmed at 12 questions; the three architectural questions (cloud provider, LLM backend, billing repo) are resolved in ADR-000; LLM layer is now agnostic via `LLMService` abstraction with DeepSeek V4 Pro as the current production backend (air-gapped — no BAA required for production, BAA required for any cloud LLM used in dev/staging). *Awaiting your go-ahead to begin Phase 1A.*
