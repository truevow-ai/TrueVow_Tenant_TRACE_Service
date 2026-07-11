# TRACE Coder Agent
Service: TrueVow TRACE (medical-records chronology engine)
Phase: 1D complete, 1E ready. 51 tests GREEN.
Stack: Python 3.11, FastAPI, async SQLAlchemy + Alembic, Supabase Postgres, Fly.io.

## Before Writing Code
1. Read `docs/00-Planning/TRACE-Agent-Coding-Instructions.md`
2. Read the relevant ADR (ADR-001 through ADR-005)
3. Run `sync-memory` + `agent-checkin start "TRACE: <task> | goal: <what success looks like>"`

## Binding Rules
- Auth: consume `@truevow/auth-client` (frontend) or verify Clerk JWT (backend). Never import Clerk directly.
- `AuthContext(user_id, firm_id, role, permissions)` via FastAPI Depends. Never raw Clerk objects.
- Every DB query includes `firm_id` / `clerk_org_id` scope (multi-tenant isolation).
- PHI never in logs, URLs, or error messages. Log only opaque UUIDs (case_id, firm_id, document_id, provider_id).
- `assert_production_for_phi()` as the first line of every PHI-touching job.
- Migrations: Alembic only, reversible `downgrade()`, tested on DB with existing data.
- No bare `except:`. Every error produces a plain-English message + support contact.
- Functions <50 lines, typed, single responsibility.
- Checkin protocol: end-of-session writeback is mandatory.
- RULE 0: No fabrication. Report only what you directly observed.
