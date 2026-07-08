# TRACE — Treatment Record Acquisition and Chronology Engine

TrueVow's second-stage pipeline product: **INTAKE → TRACE → SETTLE** (Capture → Build → Protect).
TRACE automates medical-record retrieval and builds a source-cited treatment chronology for
retainer-converted personal-injury cases, with the attorney in control at four checkpoints.

> Status: **Phase 1A — Infrastructure & Database.** Pre-early-access. All chronology output
> requires attorney review and approval before use in any legal matter. Not legal advice.

## Stack (platform-grounded — see `TRACE-Architecture-Decisions.md`)

- **API:** Python 3.11 / FastAPI (async) + uvicorn
- **DB:** Supabase PostgreSQL, SQLAlchemy 2.0 async + asyncpg, Alembic; RLS via `app.current_tenant_id` GUC
- **PHI store:** separate encrypted Postgres instance (pgcrypto AES-256), referenced only by opaque `client_token`
- **Auth:** Clerk (App 3 "TrueVow-Tenants") + MFA — `AUTH_MODE=clerk` (prod) / `local` (dev/test)
- **Storage:** AWS S3 via `StorageService` abstraction, SSE-KMS + BAA (PHI)
- **OCR:** AWS Textract · **Fax:** Fax.Plus · **NLP:** scispaCy `en_core_sci_md` · **Billing LLM:** Azure OpenAI GPT-4o-mini
- **Audit/obs:** append-only `audit_log` + pgaudit; OTEL → SigNoz + Sentry
- **Deploy:** Fly.io (`iad`)

## Local development

```bash
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -r requirements.txt
copy .env.example .env.local                          # set AUTH_MODE=local, LOCAL_JWT_SECRET=...
uvicorn app.main:app --reload --port 8080
```

With no database configured, the app falls back to in-memory SQLite (dev/test only).

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
