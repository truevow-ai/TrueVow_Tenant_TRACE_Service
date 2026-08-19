# TRACE — Client Engagement and Case Readiness

TRACE takes an approved prospect through engagement, signature, Matter activation, evidence collection, treatment tracking, records development, and case readiness.

TrueVow's four-product suite: **INTAKE → TRACE → SETTLE → COMMAND**.

> Status: **Phase 2A complete.** 68 tests passing, 42 tables on Supabase, webhook spine operational.

## Stack

- **API:** Python 3.11 / FastAPI (async) + uvicorn (port 3036)
- **DB:** Supabase PostgreSQL, SQLAlchemy 2.0 async + asyncpg, Alembic; RLS via app.current_tenant_id GUC
- **PHI store:** separate encrypted Postgres instance (pgcrypto AES-256-GCM), referenced only by opaque client_token
- **Auth:** Clerk (App 3 "TrueVow-Tenants") + MFA — AUTH_MODE=clerk (prod) / local (dev/test) with HS256 JWT
- **Storage:** Supabase Storage (trace-medical-records bucket, private, pre-signed URLs)
- **OCR:** Mistral OCR · **NLP:** OpenMed v1.7 + regex fallback · **Billing LLM:** DeepSeek V3 API (Azure quota denied)
- **Fax:** Documo (outbound) + inbound email/fax webhook reception
- **E-sign:** DocuSeal (self-hosted, AGPL-3.0 on Fly.io, not yet subscribed)
- **Audit/obs:** append-only audit_log + OTEL → SigNoz + Sentry
- **Deploy:** Fly.io (iad)

## Portal

The TRACE module is integrated into the Customer Portal (Next.js 14, port 3031, Clerk App3 auth):
- `/dashboard/trace` — landing page with stats + recent cases
- `/dashboard/trace/cases` — filterable cases table
- `/dashboard/trace/cases/new` — 3-step case creation wizard
- `/dashboard/trace/cases/[id]` — case detail with stage timeline
- `/dashboard/trace/cases/[id]/providers` — provider management
- `/dashboard/trace/cases/[id]/chronology` — chronology viewer + flags

## Local development

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env.local
# Required in .env.local: AUTH_MODE=local, LOCAL_JWT_SECRET=<32+ chars>
uvicorn app.main:app --host 0.0.0.0 --port 3036
```

For the full developer guide with architecture diagrams, API reference, data flow, and troubleshooting,
see `docs/00-Planning/TRACE-Agent-Coding-Instructions.md`.

## Tests

TRACE persists only to Supabase/PostgreSQL — there is no SQLite test path.

```bash
# Pure unit tests (no database required)
pytest tests/test_db_config.py tests/test_sol.py tests/test_golden_fixture.py

# Persistence/integration tests — BOTH safety guards required:
# the designated NON-PRODUCTION Postgres URL and the destructive latch.
$env:TRACE_TEST_PG_URL="postgresql://..."           # designated non-production DB
$env:TRACE_TEST_PHI_PG_URL="postgresql://..."       # optional separate PHI test DB
$env:TRACE_TEST_ALLOW_DESTRUCTIVE="TRUEVOW_NONPROD_TEST_DB"
pytest

ruff check .
mypy app
```

`TRACE_DATABASE_URL` / `DATABASE_URL` / `TRACE_PHI_DATABASE_URL` are NEVER
treated as test databases, and no migration or table truncation runs unless
both `TRACE_TEST_PG_URL` and the destructive latch are present.

## Phase 1A acceptance gate (must pass before Phase 1B)

- An authenticated API call is recorded in `audit_log` (actor_id, timestamp, action, resource_type).
- An unauthenticated request returns **401**.
- A request authenticated as firm A cannot read firm B's data.
