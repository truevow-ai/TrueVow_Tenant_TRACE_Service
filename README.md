# TRACE — Treatment Record Acquisition and Chronology Engine

TrueVow's second-stage pipeline product: **INTAKE → TRACE → SETTLE** (Capture → Build → Protect).
TRACE automates medical-record retrieval and builds a source-cited treatment chronology for
retainer-converted personal-injury cases, with the attorney in control at four checkpoints.

> Status: **Phases 1A-1D COMPLETE, Phase 1E active.** Portal integration built, 60/60 tests passing.

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

```bash
pytest            # runs against in-memory SQLite; no cloud required
ruff check .
mypy app
```

## Phase 1A acceptance gate (must pass before Phase 1B)

- An authenticated API call is recorded in `audit_log` (actor_id, timestamp, action, resource_type).
- An unauthenticated request returns **401**.
- A request authenticated as firm A cannot read firm B's data.
