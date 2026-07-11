# ADR-005 — Platform Identity and ID Contract

**Status:** DRAFT — pending review and approval
**Decision:** NOT YET IMPLEMENTED. Zero schema changes have been made. This ADR must be approved before any migration begins.
**Classification:** **BINDING** on all TrueVow services that reference firms, users, cases, or clients
**Date:** July 2026
**Authors:** Platform-wide identity audit of SaaS Admin, INTAKE, TRACE, SETTLE, Billing — July 2026
**Prerequisite reading:** SaaS Admin Security Contract v1 (`migrations/118_clerk_org_id_migration.sql`), SaaS Admin MDM tables (`migrations/126_mdm_core_tables.sql`), ADR-001, ADR-003, TRACE Technical Implementation Spec

---

## Executive Summary

SaaS Admin already defines a canonical identity model via its Master Data Management (MDM) layer — `mdm_cases`, `mdm_contacts`, and the Security Contract v1 (`clerk_org_id` TEXT, never UUID). Downstream services (INTAKE, TRACE, SETTLE, Billing) currently each mint their own identifiers with inconsistent names and types, creating a pipeline where no two services can reliably join on the same entity. **The fix is to adopt the existing contract everywhere.**

This ADR codifies the binding platform identity contract, then specifies the concrete migration plan for TRACE (target: `clerk_org_id` TEXT, `mdm_case_id` UUID, `contact_id` UUID). SETTLE and Billing follow from the same contract but are deferred to their own ADRs.

---

## Part A — Canonical Platform Identity Contract (Binding)

### A.1 Canonical ID Table

Every TrueVow service that references these entities must use the following identifiers.

| Entity | Canonical ID | Type | Source of Truth | Service-Owner |
|---|---|---|---|---|
| **Firm / Tenant** | `clerk_org_id` | **TEXT** (`org_*`) | Clerk | SaaS Admin maps local `tenant_id` ↔ `clerk_org_id`; all others use `clerk_org_id` directly |
| **Staff / User** | `clerk_user_id` | **TEXT** (`user_*`) | Clerk | SaaS Admin anchors; services may maintain a local surrogate FK but always carry `clerk_user_id` |
| **Case / Matter** | `mdm_cases.case_id` | **UUID** | SaaS Admin MDM | MDM is the ONLY minter. All downstream services reference this UUID. |
| **Client / Claimant** | `mdm_contacts.contact_id` | **UUID** | SaaS Admin MDM | Non-PHI cross-service client key. PHI-protecting services (TRACE) carry both `contact_id` (non-PHI) and an opaque `client_token` (PHI-protected). |
| **External CRM Matter** | `crm_matter_id` | **TEXT** | SaaS Admin CRM sync layer (`integration_crm_sync_logs`) | Propagated from SaaS Admin to downstream services; never minted locally |

---

### A.2 Binding Rules

These rules are binding on TRACE, INTAKE, SETTLE, Billing, and every future service that touches firm, user, case, or client identity.

#### Rule 1 — Only MDM Mints `case_id`

**Statement:** The `mdm_cases.case_id` UUID is the canonical — and sole — case identifier across the platform. SaaS Admin's MDM layer (`mdm_cases` table, `app/services/mdm/case_management.py`) is the only service that generates it. Every other service stores `mdm_case_id` (or `case_id` referencing MDM) as a received foreign key, never as a locally-generated UUID for the same concept.

**Why:** The current state has TRACE minting its own `case_id`, Billing minting its own `case_id`, and SETTLE storing a `String(36)` "for MDM reference" — three separate case ids for one legal matter. No cross-service query can join them reliably.

**Mechanism:** `mdm_events_outbox` fans out `case.created` events. Downstream services subscribe, receive the canonical `case_id`, and store it.

#### Rule 2 — Firm Identity Is `clerk_org_id` TEXT, Never UUID-Cast

**Statement:** Firm/tenant identity across all services is the Clerk `org_id` as TEXT (format `org_2abc123…`). Services may maintain a local internal surrogate for FK integrity, but the externally-visible, cross-service firm identifier is `clerk_org_id` TEXT. UUID-casting `clerk_org_id` is explicitly prohibited by SaaS Admin's Security Contract v1 (`migrations/118_clerk_org_id_migration.sql`, lines 6-10).

**Why:** TRACE currently casts `firm_id` to UUID (`uuid.UUID(org_id)`). Clerk `org_id` values are not guaranteed to be UUID-formatted. The TRACE auth layer will break on a real Clerk org id. Billing has the same UUID/String split internally. Settle misses `tenant_id` entirely on its primary data table.

**Source:** `TrueVow_SaaS_Administration_Service/supabase/migrations/118_clerk_org_id_migration.sql:6-10`:
> "Per Security Contract v1: tenant_id across ALL services = Clerk org_id (TEXT). No UUID casting. No alternate tenant keys."

#### Rule 3 — `contact_id` Travels Alongside `client_token`

**Statement:** TRACE (and any HIPAA/PHI-protecting service) stores the client in the PHI store behind an opaque `client_token`. This is correct and must not change. **In addition**, the non-PHI `contact_id` (from MDM's `mdm_contacts.contact_id`) must also be stored on the case record, and used as the cross-service client key for all non-PHI joins and API calls.

**Why:** Without `contact_id`, no downstream service can confirm that a TRACE case, a SETTLE settlement, and a Billing charge all belong to the same injured person — without accessing the PHI store, which is deliberately walled-off. `contact_id` is the safe bridge: it carries zero PHI and enables cross-service joinability.

#### Rule 4 — `mdm_events_outbox` Is the Fan-Out Mechanism

**Statement:** The canonical event flow is:
```
INTAKE retainer signed → CaseCreated event → MDM (mints case_id, resolves contact_id)
                                             → mdm_events_outbox
                                             → case.created + contact.created
                                             → subscribed services (TRACE, SETTLE, Billing, Portal)
```
Services subscribe to MDM outbox events. They do not call each other synchronously for identity creation.

**Why:** INTAKE currently defines `CaseCreated` but never wires the outbox dispatch to FSM completion. No canonical `case_id` is ever minted. TRACE receives the inbound `intake_record_id` but never sees a `case_id` from MDM.

#### Rule 5 — CRM Matter ID Propagates from SaaS Admin Downstream

**Statement:** SaaS Admin's `integration_crm_sync_logs` table stores the external CRM matter/case identifier (`crm_entity_id`) alongside the internal entity being synced (`entity_id`). Because SaaS Admin is the single integration point to Clio, MyCase, CASEpeer etc., it must propagate the `crm_matter_id` through the MDM outbox event so downstream services (TRACE, SETTLE) can carry it.

**Why:** Currently, CRM identifiers dead-end at SaaS Admin. A TRACE case cannot be reconciled to the law firm's own CRM matter number. The firm sees one case id in Clio and a different unrelated case id in TRACE — the product story is broken.

---

### A.3 Identity Flow Diagram

```
                     ┌──────────────┐
                     │    CLERK      │
                     │ org_id (TEXT) │
                     │ user_id (TEXT)│
                     └──────┬───────┘
                            │ Clerk App 3 JWT
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                    ▼
  ┌──────────┐      ┌──────────────┐      ┌──────────┐
  │  INTAKE  │      │   SAAS ADMIN │      │  SETTLE  │
  │ lead_id  │      │   (MDM)      │      │ case_id  │
  │ session  │      │              │      │ (→MDM)   │
  │   _id    │      │ mdm_cases    │      │          │
  └────┬─────┘      │   .case_id   │◄─────┤ contact  │
       │            │ mdm_contacts │      │  (none)  │
       │            │   .contact_id│      └──────────┘
       │            └──────┬───────┘
  retainer                │ fan-out via
  signed                  │ mdm_events_outbox
       │                  │
       │    CaseCreated   │  case.created event
       └──────────────────┤  carries: mdm_case_id,
                          │  contact_id,
                          │  clerk_org_id
                     ┌────-┴───────┐
                     ▼             ▼
               ┌──────────┐ ┌──────────┐
               │  TRACE   │ │ BILLING  │
               │case_id   │ │case_id   │
               │  (local) │ │  (local) │
               │mdm_case  │ │mdm_case  │
               │  _id ←───┤ │  _id ←───┤
               │contact_id│ └──────────┘
               └──────────┘
```

---

## Part B — TRACE Migration Plan

This section specifies the concrete schema and code changes to align TRACE with the contract in Part A. **These changes must not be implemented until ADR-005 is reviewed and approved, including the INTAKE outbox wiring (INTAKE gate).**

---

### B.1 Current State vs. Target State

| Layer | Current (broken) | Target (ADR-005) |
|---|---|---|
| **Firm** | `firm_id` **UUID** — `uuid.UUID(org_id)` in auth | `clerk_org_id` **TEXT** — stored as-received from Clerk JWT; never cast |
| **Case (external)** | None — TRACE mints own `case_id` | `mdm_case_id` **UUID** nullable — populated from MDM `case.created` outbox event |
| **Case (internal)** | `case_id` UUID as PK — used both internally and externally | Retained as internal PK/surrogate for FK integrity; **external identity is `mdm_case_id` only** |
| **Client (cross-service)** | None — only `client_token` (PHI opaque) | `contact_id` **UUID** nullable — populated from MDM `contact.created`; non-PHI, safe for cross-service joins |
| **Client (PHI)** | `client_token` UUID → `trace_phi.clients` | **Unchanged — stays as-is.** `client_token` remains the only path to PHI. `contact_id` is additive, not a replacement. |
| **CRM** | None | `crm_matter_id` TEXT nullable — received from MDM outbox event |

---

### B.2 Migration Phases

#### Phase M1 — `firm_id` UUID → `clerk_org_id` TEXT

This is the largest change. It touches every TRACE table carrying `firm_id`.

**Migrated tables (all under `trace` schema):**

| Table | Current | Target |
|---|---|---|
| `cases` | `firm_id UUID NOT NULL` | `clerk_org_id TEXT NOT NULL` |
| `firm_users` | `firm_id UUID NOT NULL` (PK composite) | `clerk_org_id TEXT NOT NULL` |
| `clients` (`trace_phi`) | `firm_id UUID` | `clerk_org_id TEXT` |
| `liens` | `firm_id UUID NOT NULL` | `clerk_org_id TEXT NOT NULL` |
| `medical_bill_line` | `firm_id UUID` | `clerk_org_id TEXT` |
| `signed_documents` | `firm_id UUID NOT NULL` | `clerk_org_id TEXT NOT NULL` |
| `upload_links` | `firm_id UUID NOT NULL` | `clerk_org_id TEXT NOT NULL` |
| `audit_log` | `firm_id UUID` | `clerk_org_id TEXT` |
| `pipeline_audit_log` | *(no firm column)* | unchanged |

All tables reachable through FKs from `cases` also gain `clerk_org_id` TEXT if they currently carry `firm_id`.

**Alembic migration approach:**

The migration must be reversible and must preserve data integrity. Approach:
1. Add `clerk_org_id TEXT` as a **nullable** column on every affected table.
2. Backfill: `UPDATE <table> SET clerk_org_id = firm_id::TEXT` for all existing (test-only) rows.
3. Add `NOT NULL` constraint after backfill is verified.
4. Drop the old `firm_id` column.
5. Rename `clerk_org_id` → leave as `clerk_org_id` (do NOT rename to `firm_id` — the column name must match the contract).
6. Re-create all indexes where `firm_id` was part of a composite key; update unique constraints.

The `downgrade()` function reverses these steps.

**Note:** The FK from `providers.case_id` → `cases.case_id` and all other `case_id` FKs are unchanged. Only the firm identifier column itself changes — no FKs from other services reference TRACE tables directly.

**RLS policy updates:**

Every RLS policy referencing `firm_id` must switch to `clerk_org_id = current_setting('app.current_tenant_id', true)::TEXT` (removing the `::uuid` cast that currently exists).

Current RLS pattern (`0001_initial_schema.py` ~line 185):
```sql
firm_id = current_setting('app.current_tenant_id', true)::uuid
```

Target RLS pattern:
```sql
clerk_org_id = current_setting('app.current_tenant_id', true)
```
(No cast — TEXT comparison, both sides are TEXT.)

**AuthContext update:**

The current `AuthContext` dataclass (`app/middleware/auth_context.py`) carries `firm_id: UUID`. It must change to `firm_id: str` (or better, `clerk_org_id: str` — name matches the contract).

Caller in `app/core/database.py` currently does `uuid.UUID(ctx.firm_id)` before setting `app.current_tenant_id`. This must change to pass the TEXT value directly — no cast.

**Auth JWT claim read:**

Current (`app/auth/deps.py` ~line 57):
```python
firm_id = claims.get("org_id") or claims.get("firm_id")
ctx = AuthContext(... firm_id=uuid.UUID(firm_id)[...])
```

Target:
```python
clerk_org_id = claims.get("org_id") or claims.get("firm_id", "")
ctx = AuthContext(... firm_id=clerk_org_id [...])  # str, not UUID
```

The `org_id` claim from Clerk is TEXT already (e.g., `org_2abc123def`). The UUID cast was the bug — removing it is the fix.

**Code touchpoints (partial, to be confirmed during implementation):**

| File | Change |
|---|---|
| `app/middleware/auth_context.py` | `firm_id: UUID` → `clerk_org_id: str` |
| `app/auth/deps.py` | Remove `uuid.UUID()` on org_id claim |
| `app/core/database.py` | Set `app.current_tenant_id` to TEXT value, no cast |
| `app/models/case.py` | `firm_id` → `clerk_org_id` |
| `app/models/firm_user.py` | `firm_id` → `clerk_org_id`, PK composite type change |
| `app/models/client.py` | `firm_id` → `clerk_org_id` |
| `app/models/lien.py`, `medical_bill.py`, `signed_document.py`, `upload_link.py` | Column rename |
| `app/models/audit.py` | Column rename |
| `infra/database/migrations/versions/0001_initial_schema.py` | *Do NOT edit applied migrations.* Create new migration. |
| `infra/database/setup_rls.sql` or equivalent | Update all RLS policies |
| `app/schemas/*.py` | Any Pydantic schema producing `firm_id` in API responses |
| `app/api/v1/routes/*.py` | Any route returning `firm_id` in responses |
| `tests/**/*.py` | All test fixtures, AuthContext mocks, firm_id assertions |

All changes are additive (new column, drop old, rename) and Alembic-tracked. Zero raw SQL against production.

**M1 Acceptance Criterion — Clarification 1 (BINDING): test fixtures ship in the SAME commit as M1.**

The test JWT helper and all its call sites must migrate in the same commit as the M1 schema/code change — never after. If M1 lands while fixtures still emit a UUID `firm_id`, the whole suite breaks with no obvious cause.

- The actual helper is `make_token(...)` / `auth_header(...)` in `tests/conftest.py` (there is **no** `_create_test_jwt` — that was a placeholder name). It currently emits a UUID:
  ```python
  # tests/conftest.py — CURRENT (wrong after M1)
  payload = {"firm_id": firm_id or str(uuid.uuid4()), "user_id": ..., "role": role}
  ```
  After M1 it must emit a TEXT `org_id` in `org_*` format:
  ```python
  # tests/conftest.py — TARGET
  payload = {"org_id": clerk_org_id or "org_2abc123test", "user_id": ..., "role": "attorney"}
  ```
- `auth_header(firm_id=...)` → `auth_header(clerk_org_id=...)`, and every call site (`auth_header(firm_id=firm)` appears across ~10 test files: `test_case_init.py`, `test_firm_isolation.py`, `test_phase1b/1c/1d/1e_gates.py`, `test_provider_confirmation.py`, `test_phase_1c_e2e.py`, `test_e2e_synthetic.py`, `test_health_and_auth.py`) must pass an `org_*` TEXT value.
- Helpers that currently do `uuid.UUID(firm)` (`seed_case`, `_make_case`, and similar) must stop casting — the firm identifier is TEXT.
- **Format note:** real Clerk org ids are `org_` + base58 (e.g., `org_2abc123…`); SaaS Admin enforces `clerk_org_id LIKE 'org_%'`. Confirm the exact live format from the Clerk dashboard before finalizing fixtures and RLS policies.

**They ship together or not at all.**

---

#### Phase M2 — Add `mdm_case_id`

**Target:** `cases.mdm_case_id UUID UNIQUE NULLABLE`

**Purpose:** External cross-service case identifier, populated when MDM mints it via the `case.created` outbox event. TRACE's own `case_id` (internal PK) is retained as the local surrogate for internal FK integrity.

**Alembic migration:**
```sql
ALTER TABLE trace.cases ADD COLUMN mdm_case_id UUID UNIQUE;
-- no NOT NULL — populated later via outbox
```

**Code touchpoints:**
- `app/models/case.py` — add `mdm_case_id` column.
- Event subscriber: when TRACE receives `case.created` from MDM, match on `intake_record_id` and set `mdm_case_id`.
- API responses: exposing `mdm_case_id` alongside local `case_id` in case responses so downstream consumers can reference the canonical id.

---

#### Phase M3 — Add `contact_id`

**Target:** `cases.contact_id UUID NULLABLE`

**Purpose:** Non-PHI cross-service client key. Populated from MDM's `contact.created` outbox event alongside the existing `client_token`. `contact_id` is safe to use in cross-service queries, analytics, notifications, and portal displays. `client_token` remains the sole path to PHI.

```sql
ALTER TABLE trace.cases ADD COLUMN contact_id UUID;
```

**No index is needed on `contact_id` alone** — it is cross-service-joinable but not a TRACE-side lookup key. An index may be added if cross-service queries prove slow; TBD.

---

#### Phase M4 — INTAKE Outbox Wiring (Pre-Production Gate)

TRACE cannot populate `mdm_case_id` or `contact_id` until INTAKE wires its `CaseCreated` outbox event:

1. INTAKE's FSM completion (`retainer_signed` state / `engagement_letter_signed == true`) emits `CaseCreated` via `app/events/case_events.py` → outbox.
2. MDM receives the event, mints `mdm_cases.case_id`, resolves/link-to-or-create `mdm_contacts.contact_id`.
3. MDM emits `case.created` and `contact.created` via `mdm_events_outbox`.
4. TRACE subscribes, matches on `intake_record_id`, stores `mdm_case_id` and `contact_id` on the case.

**This is a pre-production gate for TRACE.** Without it, M2 and M3 columns remain NULL forever.

**Clarification 2 (BINDING): M4 is recorded in the production go-live checklist.** A gate item has been added to the TRACE Technical Implementation Spec **Part 9.6 (Attorney Onboarding Readiness)** requiring one end-to-end synthetic case (INTAKE → MDM → TRACE) that confirms `mdm_case_id` is NOT NULL on the resulting TRACE case record. TRACE must not onboard any real attorney until that gate passes.

---

### B.3 Sequencing & Rollback

**Deploy order:**
1. **INTAKE** wires CaseCreated outbox → MDM.
2. **SaaS Admin / MDM** confirms outbox fan-out operational.
3. **TRACE** runs Phases M1–M4 in one atomic upgrade: Alembic migration (add nullable columns first, backfill, add NOT NULL, drop old), code deploy, acceptance test.
4. **SETTLE** and **Billing** follow their own ADRs.

**Rollback:** Each Alembic migration has a tested `downgrade()`. The code change is a FastAPI restart — zero-downtime with a blue/green deploy on Fly.io. If something breaks, revert to the prior image and run `alembic downgrade`.

**Acceptance criteria:**
- TRACE's `clerk_org_id` column value matches the Clerk JWT `org_id` claim exactly (no cast).
- RLS policies enforce isolation using TEXT comparison.
- TRACE's `mdm_case_id` is populated for all cases after M2 backfill.
- TRACE's `contact_id` is populated and non-nullable for all cases after M3 backfill.
- All existing Phase 1A–1D tests pass with updated fixtures.
- The `make_token`/`auth_header` helpers in `tests/conftest.py` (and all ~10 call sites) sign with a TEXT `org_id` claim in `org_*` format — updated in the SAME commit as M1 (see Clarification 1).

---

### B.4 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Clerk `org_id` is not UUID-formatted, breaking existing code mid-`uuid.UUID()` | High (certain, per Clerk spec) | Production auth failure for all TRACE users | Remove the UUID cast as part of M1 (the fix). Do a phased test with a real Clerk org_id before production. |
| `intake_record_id` is never minted by INTAKE | High | `mdm_case_id` stays NULL forever | INTAKE outbox wiring is a TRACE pre-production gate. Tracked here. |
| Billing `tenant_id` UUID/String split breaks cross-service joins | High | SETTLE/Billing joins fail even after TRACE fix | Billing own ADR. Interim: Billing exposes `intake_id` which TRACE already stores. |
| SETTLE `case_id` String(36) vs UUID mismatch | Medium | SETTLE can't join MDM `case_id` without type conversion | SETTLE own ADR. MDM `case_id` is UUID; SETTLE must cast from String(36). |

---

### B.5 What Does NOT Change

- `client_token` and the `trace_phi.clients` PHI store — unchanged. All PHI handling is unaffected.
- TRACE's local `case_id` UUID PK — retained as internal surrogate. Not exposed as the cross-service case identifier.
- All FK relationships anchored on TRACE's local `case_id` — unchanged.
- HIPAA isolation, PHI encryption, audit logging — all untouched.

---

## Part C — Impact on Other Services (Summary, Not Executed Here)

| Service | Required change | ADR |
|---|---|---|
| **INTAKE** | Wire `CaseCreated` outbox → MDM at retainer-signed | INTAKE ADR (not TRACE's) |
| **SETTLE** | `case_id` String(36) → UUID; add `clerk_org_id` TEXT; add `contact_id` on settlement records | SETTLE ADR |
| **Billing** | Unify `tenant_id` UUID/String split → `clerk_org_id` TEXT; point `case_id` → `mdm_cases.case_id`; keep `intake_id` and `external_case_id` as secondary reconciliation fields | Billing ADR |
| **SaaS Admin** | Confirm MDM outbox fan-out is operational; expose `crm_matter_id` in outbox event | SaaS Admin operational task |

---

## Approval Gate

- [ ] **CTO review** — ADR-005 contract approval
- [ ] **INTAKE readiness** — `CaseCreated` outbox wiring confirmed or scheduled
- [ ] **TRACE migration approval** — Part B Phases M1–M4 authorized for implementation
- [ ] **SETTLE / Billing** — own ADRs acknowledged

**No migration begins until this ADR is approved and signed.**

---

*ADR-005 — July 2026. Binding on all TrueVow services. Grounded in schema audit of SaaS Admin (`truevow-cto/supabase/migrations/118`, `126`), INTAKE (`app/models/`, `app/events/case_events.py`), TRACE (`app/models/`, `app/auth/`, `infra/database/migrations/0001`), SETTLE (`alembic/versions/`, `app/auth/auth.py`), and Billing (`app/models/`, `infra/repository/`). Zero code has been changed — this ADR is documentation pending review.*
