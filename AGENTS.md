# TrueVow_Tenant_TRACE_Service â€” Agent Rules

# Agent Onboarding Preamble
# Drop this into any service's AGENTS.md to wire it into the ecosystem.
# The agent reads this on startup and becomes ecosystem-aware.

## WRITEBACK PROTOCOL (MANDATORY)

**You report to the TrueVow CTO Orchestrator.** Every session you work on this service, you MUST write back your learnings to the shared memory vault. Services without recent activity are flagged as STALE. Do not let this service go stale.

**Format for all writebacks:** "<service>: <specific action taken> | <result/outcome> | <what you learned> | <next step or blocker>"

### Start of Session â€” Activate Service
```
python ../TrueVow_Shared_Orchestration/orchestrator.py sync-memory
python ../TrueVow_Shared_Orchestration/orchestrator.py scan-services
python ../TrueVow_Shared_Orchestration/orchestrator.py agent-checkin start "TRACE: <specific task> | resuming from <previous state> | goal: <what success looks like>"
```

### During Work â€” Log Learnings
```
python ../TrueVow_Shared_Orchestration/memory.py remember <category> "<title>" "<content>" --importance N
```
Categories: architecture, pattern, decision, dependency, convention, bug, context, todo, relationship
Importance: 10 = critical blocker, 8 = important decision, 5 = observation

### End of Session â€” Writeback Results
```
python ../TrueVow_Shared_Orchestration/orchestrator.py agent-checkin done "TRACE: <what was accomplished> | outcome: <result> | learned: <key insight> | next: <what remains>" --status DONE
python ../TrueVow_Shared_Orchestration/orchestrator.py push-memory
```

### If Blocked â€” Alert Immediately
```
python ../TrueVow_Shared_Orchestration/orchestrator.py agent-checkin blocked "TRACE: <specific blocker> | attempted: <what you tried> | need: <what will unblock>"
```

### Before Any Work â€” Route the Task
```
python ../TrueVow_Shared_Orchestration/orchestrator.py dispatch "<user's request>"
```

### Security & Research
- Scan new skills: `skillspector scan <path> --no-llm`
- Web research: `agent-reach doctor` for status

**Reminder:** Services go STALE after 24h without agent activity. Write back to prove this one is alive. The CTO dashboard refreshes every scan.

---

## Service Identity

| Field | Value |
|-------|-------|
| **Service name** | TRACE â€” Client Engagement and Case Readiness |
| **Pipeline position** | INTAKE â†’ **TRACE** â†’ SETTLE â†’ COMMAND |
| **Port** | 3036 |
| **Owner** | Yasha |
| **Clerk domain** | App 3 (TrueVow-Tenants) â€” external law firm users |
| **Database** | Supabase Postgres: cnbzuiuyppzrygxllgxj (production project) |
| **PHI store** | Separate Postgres schema (trace_phi), AES-256-GCM encryption |
| **Status** | Phases 1A-1E COMPLETE. Phase 2A (evidence, ontology, contracts) deployed. 68/68 tests passing. |

## Quick Start (for any agent)

```bash
# 1. Activate environment
.venv\Scripts\activate

# 2. Ensure .env.local has:
#    AUTH_MODE=local
#    LOCAL_JWT_SECRET=test-secret-at-least-32-bytes-long-000
#    TRACE_DATABASE_URL=postgresql://...  (or leave empty for SQLite)
#    LLM_SERVICE_PROVIDER=deepseek_api
#    DEEPSEEK_API_KEY=sk-...

# 3. Run the service
.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 3036

# 4. Verify
curl http://localhost:3036/health

# 5. Test LLM
curl http://localhost:3036/llm-test

# 6. Test with auth (generate JWT first)
python -c "import jwt; print(jwt.encode({'sub':'test','firm_id':'11111111-1111-4111-8111-111111111111','role':'attorney','mfa':True}, 'test-secret-at-least-32-bytes-long-000', algorithm='HS256'))"
# Use token as: Authorization: Bearer <token>
```

## Dependencies (what must be running)

| Service | Port | Required for | Down impact |
|---------|------|-------------|-------------|
| Supabase Postgres | cloud | All CRUD operations | Cases, providers, liens, chronology fail |
| Supabase Storage | cloud | Document uploads | Upload endpoint returns errors |
| DeepSeek API | cloud | /llm-test | LLM test fails (non-blocking) |
| Customer Portal | 3031 | Attorney UI | No frontend, API still works via curl |
| Tenant Billing | 3016 | Feature gating | Menu items hidden unless billing fallback exists |
| DocuSeal | cloud | E-signature | Cases won't advance past PENDING_SIGNATURE (can force via DB) |
| Documo Fax | cloud | Outbound fax | Fax send fails but API returns 200 with FAILED status |

## Auth System

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ DEV (AUTH_MODE=local)                                â”‚
â”‚   JWT: HS256 with LOCAL_JWT_SECRET                   â”‚
â”‚   Required claims: sub, firm_id, role, mfa           â”‚
â”‚                                                      â”‚
â”‚   generate: jwt.encode({                             â”‚
â”‚     'sub':'user_id',                                 â”‚
â”‚     'firm_id':'11111111-1111-4111-8111-111111111111',â”‚
â”‚     'role':'attorney', 'mfa':True                    â”‚
â”‚   }, SECRET, algorithm='HS256')                      â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ PROD (AUTH_MODE=clerk)                               â”‚
â”‚   JWT: RS256, verified via Clerk JWKS endpoint       â”‚
â”‚   Requires: CLERK_JWKS_URL, CLERK_ISSUER, CLERK_AUDIENCEâ”‚
â”‚   No local JWT generation possible                   â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**Critical gotcha:** The service loads `.env.local` via `load_dotenv(override=True)` in `app/main.py`. If `.env.local` has `AUTH_MODE=clerk`, it WILL override any shell env var. To use local auth, `.env.local` MUST contain `AUTH_MODE=local`. If you change it, KILL AND RESTART the uvicorn process â€” the change only takes effect on startup.

## Architecture Summary

```
Portal (:3031, Next.js)
   â”‚  /api/trace/[...path]  â† universal proxy (generates HS256 JWT)
   â”‚  Clerk App3 auth (browser cookies)
   â–¼
TRACE Backend (:3036, FastAPI)
   â”‚
   â”œâ”€â”€ /api/v1/trace/cases              â†’ cases.py
   â”œâ”€â”€ /api/v1/trace/cases/{id}/providers â†’ providers.py
   â”œâ”€â”€ /api/v1/trace/cases/{id}/requests  â†’ requests.py (fax)
   â”œâ”€â”€ /api/v1/trace/cases/{id}/documents â†’ documents.py (upload)
   â”œâ”€â”€ /api/v1/trace/cases/{id}/liens     â†’ liens.py
   â”œâ”€â”€ /api/v1/trace/cases/{id}/chronology â†’ qa.py
   â”œâ”€â”€ /api/v1/trace/cases/{id}/export     â†’ qa.py
   â”œâ”€â”€ /api/v1/trace/webhooks/*           â†’ webhooks.py
   â””â”€â”€ /webhooks/docuseal/*              â†’ signing.py
   â”‚
   â”œâ”€â”€ Supabase Postgres (operational DB + PHI DB)
   â”œâ”€â”€ Supabase Storage (trace-medical-records bucket)
   â”œâ”€â”€ DeepSeek API (billing LLM, replaces Azure GPT-4o-mini)
   â”œâ”€â”€ Documo (outbound fax)
   â”œâ”€â”€ DocuSeal (e-sign, not subscribed)
   â”œâ”€â”€ OpenMed NLP (clinical NER, regex fallback)
   â”œâ”€â”€ NPI Registry (provider lookup)
   â””â”€â”€ Mistral OCR (document text extraction)
```

## Key Files (read these first)

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app, middleware, /health, /llm-test, load_dotenv |
| `app/core/config.py` | pydantic-settings, env vars, DB URL resolution |
| `app/core/middleware.py` | Correlation ID + audit logging |
| `app/auth/clerk.py` | JWT verification (HS256 local / Clerk RS256) |
| `app/auth/deps.py` | AuthContext dependency for FastAPI |
| `app/api/v1/__init__.py` | Router aggregation â€” all endpoints wired here |
| `app/api/v1/routes/cases.py` | Case CRUD + SOL + PHI store |
| `app/api/v1/routes/providers.py` | Provider CRUD + confirmation gate |
| `app/api/v1/routes/requests.py` | Fax preview + send + cover sheets |
| `app/api/v1/routes/qa.py` | Chronology, readiness, export, approve |
| `app/api/v1/routes/webhooks.py` | Fax status, inbound email, inbound fax |
| `app/api/v1/routes/documents.py` | Attorney upload + portal link ingestion |
| `app/api/v1/routes/liens.py` | Lien CRUD |
| `app/api/v1/routes/signing.py` | DocuSeal signing + webhook |
| `app/api/v1/routes/client_links.py` | Public client upload links |
| `app/services/llm.py` | LLM abstraction (DeepSeek / Azure / Anthropic) |
| `app/services/inbound.py` | Inbound email/fax processing + case matching |
| `app/services/providers.py` | NLP + NPI provider extraction |
| `app/services/phi_store.py` | AES-256-GCM client PII encryption |
| `app/services/sol.py` | Statute of limitations calculator (50 states) |
| `app/services/export.py` | ChronologyExporter (PDF + JSON) |
| `app/services/chronology.py` | Timeline builder + flag engine |
| `app/models/case.py` | Case model (7 stages, SOL, HIPAA) |
| `app/models/provider.py` | Provider model (extraction confidence, fax) |
| `app/models/document.py` | Document metadata (storage key, hash, source) |
| `app/models/audit.py` | Audit log (append-only, VARCHAR(255) action) |
| `app/storage/storage_service.py` | Supabase Storage via REST API |

## Database Setup

**Operational DB (`trace` schema):**
- Connection: Supabase Postgres at cnbzuiuyppzrygxllgxj.supabase.co
- Tables: cases, providers, documents, event_nodes, record_requests, liens, medical_bill_line, signed_documents, upload_links, audit_log, firm_users, pipeline_audit_log
- Firm isolation: explicit `firm_id` filter on every query + Supabase RLS in production
- Every query MUST include `firm_id` filter â€” this is the multi-tenant isolation guarantee

**PHI Store (`trace_phi` schema):**
- Separate database/schema from operational DB
- Client PII (name, DOB, address, phone) encrypted with AES-256-GCM
- Operational DB only sees `client_token` (opaque UUID)
- Decryption only via `app/services/phi_store.py::get_client()`

**Schema migrations applied:**
- Migration `0017` â€” 31 new tables (evidence, ontology, client portal, workflow). Already applied to Supabase.
- Migration `0008` â€” trace schema + RLS. Already applied.
- Legacy ALTER TABLE for extraction_confidence and audit_log still pending (non-blocking).

## Webhook Authentication (Frozen Contract: WebhookSignature v1.0)

TRACE verifies incoming webhooks using HMAC-SHA256 signatures per the frozen `WebhookSignature v1.0` contract:

| Caller â†’ TRACE | Canonical Path | Idempotency Key |
|---|---|---|
| SaaS Admin | `POST /api/v1/trace/webhooks/matter-activated` | `event_id` |

TRACE does not currently send signed webhooks to other services. If it does, use the same contract with `app/shared/webhook_auth.py`.

### Env vars
```
# Per-link key (NOT a global shared secret):
TRUEVOW_WEBHOOK_KEY_ID=tv-saas-admin-to-trace-v1
TRUEVOW_WEBHOOK_SECRET=<per-environment-secret>
# Optional rotation (also per-link):
TRUEVOW_WEBHOOK_SECONDARY_KEYS=[{"key_id":"tv-saas-admin-to-trace-v2","secret":"..."}]
```

### Replay protection
Two-layer: (1) 300s timestamp tolerance, (2) event_id idempotency via `WebhookVerifier.is_replay()` / `mark_consumed()`. Never rely on timestamp alone.

### Authoritative contract locations
- `app/shared/webhook_auth.py` â€” Python verifier + signing
- `app/shared/contracts.py` â€” frozen contract versions
- `tests/test_golden_fixture.py` â€” 17 golden fixture tests
- `../TrueVow_Documentation/TrueVow_Ontology_Registry_v1.0.yaml` â€” canonical ontology

### Implementation rules for TRACE
- Hash exact raw request bytes (never re-serialize parsed JSON)
- Canonical path: `/api/v1/trace/webhooks/matter-activated` (no trailing slash, no query string)
- Constant-time comparison on signatures
- Never log secrets, full signatures, or confidential body contents
- Development, staging, and production must use different secrets
- Per-link keys only: SaaS Admin's key for TRACE must differ from INTAKEâ†’RETAINER or RETAINERâ†’SaaS Admin keys

## Common Pitfalls & Fixes

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| "Invalid or expired session" on all API calls | `.env.local` has AUTH_MODE=clerk but you're in dev | Change to `AUTH_MODE=local`, KILL uvicorn, restart |
| Portal proxy returns 401 | LOCAL_JWT_SECRET mismatch between portal and TRACE | Both must use `test-secret-at-least-32-bytes-long-000` |
| "no such table: cases" in tests | TRACE_DATABASE_URL not set to empty for SQLite | Set `TRACE_DATABASE_URL=""` before importing app |
| LLM test returns internal error | DEEPSEEK_API_KEY not in os.environ | `load_dotenv` must run before the app starts |
| Cases list empty in portal | No `trace` feature in billing response | Billing fallback now includes trace. Ensure billing proxy is reachable. |
| Upload works but document not found | Supabase Storage bucket not created | Create bucket `trace-medical-records` via Supabase dashboard or API |
| python-dotenv parse error | Invalid line in .env.local (line 491 was `@DOCUMENTATION`) | Fixed. Check for lines without `=` sign. |
| `str object has no attribute hex` | Passing string case_id to UUID column in SQLite | Always wrap with `uuid.UUID(case_id)` in raw SQL |
| Wrong firm can read cases | `get_case` had no firm_id filter (pre-Jul 24) | Fixed. Now requires `Case.firm_id == firm_uuid`. |
| Export returns TypeError | qa.py called export with wrong params | Fixed. Now passes strings from case model. |

## Case Lifecycle (7 Stages)

```
PENDING_SIGNATURE â†’ INITIALIZATION â†’ RETRIEVAL â†’ PROCESSING â†’ CHRONOLOGY_READY â†’ ATTORNEY_REVIEW â†’ DEMAND_READY
```

**Gates (case cannot advance past these without passing):**
1. **HIPAA signed** â€” DocuSeal webhook or force-advance via DB
2. **Checkpoint 1** â€” Provider list must have 1+ CONFIRMED, then locked
3. **Checkpoint 2** â€” Fax requests sent to all CONFIRMED providers
4. **Demand-ready gate** â€” All PRIORITY flags must be attorney-annotated

## Truth Commands

```bash
# Standard checks (run from TRACE service root, use venv)
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m mypy app

# Quick API smoke test
curl http://localhost:3036/health
python -c "import jwt; print(jwt.encode({'sub':'t','firm_id':'11111111-1111-4111-8111-111111111111','role':'attorney','mfa':True}, 'test-secret-at-least-32-bytes-long-000', algorithm='HS256'))" 
# Then: curl -H "Authorization: Bearer <token>" http://localhost:3036/api/v1/trace/cases

# Full E2E test suite  
.venv\Scripts\python.exe C:\Users\yasha\AppData\Local\Temp\opencode\trace_e2e_test.py
.venv\Scripts\python.exe C:\Users\yasha\AppData\Local\Temp\opencode\trace_quick.py

# Portal E2E
# Start TRACE backend first, then Portal, then:
# Browser: http://localhost:3031/dashboard/trace?preview=bypass
```

## Recent Session History (July 2026)

| Session | What was done | State |
|---------|--------------|-------|
| Jul 31 | Billing plan code + entitlement capability gates added | DONE |
| Jul 31 | Webhook timestamp aligned to milliseconds (WebhookSignature v1.0 contract) | DONE |
| Jul 31 | Migration 0018: trace_plan_code column on cases, /ready returns 'ready' | DONE |
| Jul 31 | Portal access ownership model corrected (ClientAccessProjection is temporary mirror) | DONE |
| Jul 31 | Contract normalization: EventEnvelope 1.0.1, 9 evidence refs, HMAC auth, global/tenant separation | DONE |
| Jul 31 | MatterActivation handler: 8 rejection conditions, idempotent case creation | DONE |
| Jul 30 | Phase 2A schema migration: 31 tables applied to Supabase (migration 0017) | DONE |
| Jul 30 | Client portal endpoints: /api/client/v1/matters, completion, documents, requests, access | DONE |
| Jul 30 | ClientAccessProjection model (TRACE-local mirror of Shared Platform canonical grant) | DONE |
| Jul 29 | Shared foundation: AuthorityGate, ConsentLedger, PolicyRegistry, EventStore, StateMachine | DONE |
| Jul 29 | Golden fixture test: 9 cross-repository contract validation tests | DONE |
| Jul 29 | Webhook auth: HMAC-SHA256 aligned with SaaS Admin convention | DONE |
| Jul 29 | Ontology alignment: 20 new models covering 40/42 TRACE entities | DONE |
| Jul 27 | Source-linked evidence: EvidenceFact, SourceLocation, ContradictionPair, MissingEvidenceSignal | DONE |
| Jul 24 | Inbound email/fax reception built + tested | DONE |
| Jul 24 | 9 bugs fixed (firm isolation, export, JWT, schema) | DONE |
| Jul 24 | TRACE portal module: 6 pages + proxy + client | DONE |
| Jul 23 | DeepSeek API switched as billing LLM (Azure quota denied) | DONE |
| Jul 23 | /llm-test endpoint wired (was dead code) | DONE |
| Jul 19-23 | E2E testing: 60/60 tests passed | DONE |
| Jul 20 | BAA research: DeepSeek no BAA, Anthropic + OpenAI API do | CONTEXT |
| Jul 19 | extraction_confidence VARCHAR(10â†’32) model fix | DONE |

## Remaining TODOs

| Priority | Task | Blocked by |
|----------|------|-----------|
| HIGH | Run ALTER TABLE on Supabase for extraction_confidence + audit_log | Needs DB admin access |
| HIGH | Configure RESEND_WEBHOOK_SECRET for inbound email | Resend dashboard setup |
| MEDIUM | DocuSeal subscription for e-sign in production | Budget decision |
| MEDIUM | Billing service: add `trace` to real feature response | ghaus-fsd (billing owner) |
| MEDIUM | Intake leads API route needs shared-library fix | @truevow/rbac-engine build |
| LOW | Deploy TRACE to Fly.io | Staging environment ready |
| LOW | DeepSeek BAA for production PHI-adjacent billing | Vendor negotiation |

> Add further service-specific rules below. The ecosystem preamble above wires
> this agent into the TrueVow Agent Ecosystem.
