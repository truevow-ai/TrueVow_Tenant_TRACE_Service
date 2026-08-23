# SPEC — TRACE-FND-003-R1

# Runtime Role Commissioning and Tenant-Context Closure

| | |
|---|---|
| **Slice** | TRACE-FND-003-R1 — Non-Bypass Runtime Role Commissioning |
| **Status delta** | BEFORE: FND-003 = `CODE_COMPLETE_BLOCKED_RUNTIME_ROLE`; operational tenant isolation = `PARTIAL / BLOCKED` → AFTER: FND-003 = `PASS_CANDIDATE`; operational trace-schema tenant isolation = `BUILT-TESTED` |
| **Inputs** | ① `docs/TRACE-CANONICAL-TRUTH.md` v1.1 (docs commit `7f0da3c`) ② accepted base `cc36a8dac28c6a628777eb2aa83caa15dfec8122` (`trace/TRACE-FND-003`) ③ authorized roadmap item §10 #1 only |
| **Gate** | Independent Gate 003 by CTO after code-review; builder green ≠ PASS |

## Problem Statement

The platform's tenant-isolation boundary is physically correct but operationally inert. All 43 tenant-scoped operational tables carry FORCE Row-Level Security with one canonical policy family each (migration 0022, preflight-guarded against unexpected policies) — yet the runtime application connects to Supabase as the `postgres` login, which holds `rolbypassrls = true`. RLS therefore evaluates to a no-op for every production request: tenant isolation currently rests entirely on the application-level `firm_id` filter habit, not on the database boundary that FND-003 built.

Compounding this, internal sessions that bypass the request-scoped session dependency — most importantly the append-only audit writer, which opens its own short-lived session with no tenant GUCs — would silently fail their writes (RLS denial) the moment a non-bypass login took over. Switching the login without closing those gaps would break audit persistence and any other unscoped internal writer.

## Solution

Split database authority into two identities with two connection strings, and close every internal tenant-context gap so the dedicated runtime identity can enforce RLS for real:

1. **Privileged migration/admin connectivity** — Alembic (and operator-only administration) runs from a separate privileged URL (`TRACE_MIGRATION_DATABASE_URL`). The application never reads it and cannot fall back to it.
2. **Dedicated application login** — `trace_runtime_login`: `NOSUPERUSER`, `NOBYPASSRLS`, non-owner of tenant tables, no CREATE/ALTER/DROP in `trace`, no access to `trace_phi`, no mutation/delete rights on `audit_log`. The FastAPI runtime connects exclusively through this identity (`TRACE_DATABASE_URL`).
3. **Tenant-context closure** — every internal operational session explicitly sets the same parameterized tenant GUCs the request-scoped dependency uses. The audit writer persists successfully *under* RLS rather than beside it.
4. **Runtime-role readiness evidence** — `/ready` gains a `runtime_role` check reporting the live `current_user`/`session_user` and the bypass flags, so commissioning is observable, not assumed.

No redesign accompanies this slice. Migration 0022 policies, Matter/Case identity, Clerk auth, PHI architecture, portal grants, Billing, and object scoping are frozen.

## User Stories

1. As the CTO/gate owner, I want the runtime connection to execute as a `NOBYPASSRLS` identity, so that FND-003's RLS is the operative tenant boundary instead of a dormant safety net.
2. As the CTO/gate owner, I want migrations to require a distinct privileged URL, so that application compromise cannot escalate to schema mutation.
3. As the CTO/gate owner, I want `/ready` to prove the live role identity and bypass flags, so that Gate 003 verification is evidence-based rather than trust-based.
4. As a solo attorney using the portal, I want my case list and documents isolated by firm at the database layer, so that another firm's data is unreachable even if application code errs.
5. As an attorney's client using the public upload link, I want my submissions confined to my matter's firm context, so that nothing I send can touch another tenant.
6. As the audit/compliance reviewer, I want audit rows written successfully while RLS enforces, so that the append-only trail survives the privilege downgrade.
7. As the audit/compliance reviewer, I want the runtime role unable to mutate or delete `audit_log`, so that the trail is tamper-resistant from the application tier.
8. As a platform operator, I want one documented place defining both URLs and their authorities, so that environment setup during commissioning is mechanical.
9. As a platform operator, I want startup/readiness to fail loudly when the runtime identity is wrong, so that a miswired deployment never serves traffic believing it is isolated.
10. As a developer on the next slice, I want a single helper for "internal session with explicit tenant context", so that future writers cannot reintroduce the bare-session gap.
11. As a developer on the next slice, I want adversarial cross-tenant tests in the guarded suite, so that regressions against the RLS contract are caught before merge.
12. As the Billing service (upstream consumer), I want tenant-scoped operational reads/writes to keep behaving identically after the role switch, so that matter-plan projections remain correct.
13. As a security reviewer, I want proof that missing tenant context denies access rather than defaulting to visibility, so that fail-open behavior cannot return through configuration drift.
14. As a security reviewer, I want the GUC proven transaction-local and reset-proven, so that tenant identity cannot leak across pooled connections.
15. As a junior agent picking up FND-004 later, I want this slice to end with an unambiguous `PASS_CANDIDATE` state recorded in canonical truth, so that I never build on a blocked foundation.
16. As the SaaS Admin relaying `matter.activated`, I want idempotent case projection to continue working under the runtime login, so that the canonical activation chain is unaffected by the privilege change.
17. As an auditor of the Supabase project, I want zero unexpected RLS policies post-commissioning, so that the 43/43 canonical guarantee remains verifiable.

## Implementation Decisions

1. **Two-URL contract.** Add a migration/admin URL setting consumed exclusively by the migration tooling. The runtime application resolves only the existing runtime and PHI URLs; there is no fallback path from either to the privileged URL, and the migration tooling fails loudly if the privileged URL is absent (no silent reuse of the runtime URL).
2. **Runtime identity.** A new dedicated Postgres login/role for the application: `NOSUPERUSER`, `NOBYPASSRLS`, `NOSUPERUSER`-class restrictions including no schema DDL in `trace`, no ownership of tenant tables, no privileges in `trace_phi`, and INSERT/SELECT-only on the audit table. Commissioned via a repeatable, idempotent SQL script checked into the repo (operator executes with the privileged connection); the script also grants the minimal table/column sequence DML rights the runtime requires and revokes inherited broad rights (including from the legacy direct-grant path used by pooled connections).
3. **Tenant-context closure.** Introduce one internal factory/helper alongside the existing request-scoped dependency that yields a session carrying the same three parameterized GUCs (`app.current_tenant_id`, `app.current_user_id`, `app.current_user_role`). Migrate onto it every operational caller proven to open a tenant-scoped session outside the canonical boundary — the audit writer and, per repo inspection at spec time, direct session opens in attorney QA routes, the Matter activation handler, client portal routes, evidence/lien/signing flows, inbound processing, and shared-foundation stores. **One architectural seam; multiple callers migrate onto it.**

   No new business-domain seam is introduced. FND-003-R1 may make **narrowly mechanical changes to any operational DB caller** proven to open a tenant-scoped session outside the canonical context boundary. Such changes may only: adopt the request-scoped dependency, invoke the shared tenant-context helper, or fail closed when no trustworthy tenant identity exists. They may not alter business semantics.
4. **Repository-wide session inventory — BLOCKING acceptance item.** Every operational runtime occurrence of direct session/engine construction (`async_session_maker`, `engine.connect`, `engine.begin`, `create_async_engine`, `effective_database_url`) must be classified into exactly one of:

   ```
   TENANT_REQUEST_SCOPED    — request-scoped, context via canonical dependency
   TENANT_INTERNAL_SCOPED   — internal work, context via canonical helper
   GLOBAL_READ_ONLY         — provably tenant-agnostic reads (e.g., catalogs,
                              alembic_version); no tenant rows touched
   MIGRATION_TEST_ADMIN     — migration/test/operator tooling only; never
                              reachable from runtime code
   INVALID_BYPASS_PATH      — everything else
   ```

   Final count of `INVALID_BYPASS_PATH` must be **0**. The inventory table is committed as slice evidence alongside the gate report. At spec time the raw count of direct session opens is ~57 across routes, services, shared foundation, health/readiness, and audit; the inventory accounts for each.

5. **Tenant-context source matrix (binding):**

   ```
   Authenticated attorney/staff request:
       ctx.firm_id -> canonical context helper

   matter.activated:
       verified signed envelope tenant_id -> canonical context helper

   audit writer:
       explicit firm_id carried by the action -> canonical context helper

   system/external webhook with no trustworthy tenant identity:
       MUST NOT bypass RLS
       MUST NOT use migration/admin connection
       MUST fail closed unless a separately authorized tenant-resolution
       mechanism exists
   ```

6. **Blocked-context semantics.** A new explicit condition — `BLOCKED_INTERNAL_TENANT_CONTEXT` — is raised when a runtime path needs tenant-owned data but cannot obtain tenant identity from an authenticated/verified authority before RLS access. Resolution may require a later bounded integration-contract/security slice. RLS may not be weakened to avoid the blocker, and this slice must not invent a privileged database lookup function to preserve an old webhook implementation.

7. **Fax/email callbacks specifically.** The current fax-status path documents an expectation of running "without RLS under a dedicated system role in production." That design is incompatible with the frozen architecture and is rejected by this spec. It is **not** replaced by a BYPASSRLS system role (which would recreate Gate 003's defect under another name) and **not** by a quiet `SECURITY DEFINER` tenant resolver (privileged discovery driven by untrusted external identifiers is the wrong dependency direction while GAP-1/GAP-2 authentication is fail-open). The invariant for R1:

   ```
   trusted tenant context -> RLS access

   never:
   untrusted external identifier -> privileged cross-tenant lookup -> discover tenant
   ```

   Any callback that cannot operate under that rule today **fails closed** and remains PARTIAL/uncommissioned until its integration-security slice.

8. **Audit-under-RLS correctness.** The canonical policy set must accept audit INSERTs when tenant context matches the row's `firm_id`; where the audit policy requires a role carve-out (append-only semantics), express it via grants to the runtime role (INSERT/SELECT only), never via `BYPASSRLS`, never via `SET ROLE` escalation from a privileged session inside the app.
9. **Readiness evidence.** Extend `/ready` with a `runtime_role` check executed on the runtime engine: report whether `current_user` = `session_user` = the expected login name, `rolsuper = false`, `rolbypassrls = false` (queried from the catalogs, values only — never credentials). Overall ready stays all-checks-green: `runtime_role`, `migration`, `database`, critical tables, `phi_key`.
10. **Connection-string discipline.** Pooler compatibility preserved (existing statement-cache disablement behavior carries over unchanged); search-path handling stays as-is.
11. **No SET ROLE workaround.** The application never connects as `postgres` and issues `SET ROLE`; commissioning means actually logging in as the restricted identity.
12. **Idempotent, reversible-by-script commissioning.** The role/grant script is safe to re-run (idempotent GRANTs/revokes) and ships with a companion verification query block an operator can paste to confirm role attributes and effective policies.

## Testing Decisions

Good tests here assert externally observable authorization behavior — who may read/write what given a connection identity and tenant context — never SQLAlchemy internals.

- **Seam (single):** the database session/context boundary. Request-scoped dependency and the new internal tenant-context helper are the only two entry points under test. Callers migrate onto them via narrowly mechanical changes only; each migrated caller stays covered by the guarded regression suite, and fail-closed paths (untrusted-context callbacks raising `BLOCKED_INTERNAL_TENANT_CONTEXT`) gain explicit tests. Business logic downstream is exercised as today — unchanged by design.
- **Role-attribute tests** (guarded suite, local Postgres): assert the commissioned role's catalog facts — superuser false, bypass false, membership/ownership absences, `trace_phi` absence.
- **Adversarial RLS tests:** cross-tenant SELECT/UPDATE/DELETE denied; missing-GUC session denied on tenant-operational tables; audit INSERT succeeds with matching context and fails without; GUC reset proven across pooled reuse (set → commit → new transaction sees defaults).
- **Readiness tests:** `/ready` reports `runtime_role: ok` under the commissioned role and fails correctly when connecting as an over-privileged role (test doubles the check logic against a controlled connection).
- **Regression anchor:** full guarded suite green (163+ tests) — proves the downgrade broke no operational behavior; prior art: FND-001A baseline tests and FND-003's fifteen adversarial tests extend naturally.
- **Supabase bounded smoke (operator-run, privileged):** create role, apply grants, run the adversarial smoke as the runtime login against staging project, capture `current_user`/`session_user`/flags output as Gate 003 evidence. Application-level Supabase tests stay behind the destructive-test latch as today.

### Acceptance contract (non-negotiable outcomes)

```
Supabase runtime:
  current_user = trace_runtime_login ; session_user = trace_runtime_login
  rolsuper = false ; rolbypassrls = false
Runtime role:
  does not own tenant tables ; cannot CREATE in trace
  cannot ALTER/DROP schema objects ; cannot access trace_phi
  cannot mutate/delete audit_log ; same-tenant operational CRUD works
Migration/admin:
  separate privileged URL ; application cannot fall back to it
Tenant context:
  get_db() parameterized ; internal tenant sessions parameterized
  audit writer persists under RLS ; no unscoped tenant-operational session remains
RLS:
  43/43 enabled ; 43/43 FORCE ; canonical policies only ; 0 unexpected
Security:
  cross-tenant denied ; missing context denied ; GUC reset proven
Readiness:
  runtime_role = ok ; migration = ok ; phi_key = ok
Session inventory:
  100% of direct session/engine occurrences classified
  INVALID_BYPASS_PATH count = 0 (blocking)
Tests:
  full guarded Postgres run green ; 0 failed ; 0 skipped
Supabase:
  bounded runtime-login adversarial smoke PASS
```

## Out of Scope

- Rewriting migration 0022 or its policy predicates (preflight guard stays).
- Clerk/auth architecture; Clerk-org ↔ tenant-UUID mapping (truth doc §4 debt).
- Matter/Case identity normalization (`intake_record_id` debt) or projection naming fixes.
- `trace_phi` object scoping beyond confirming the runtime role has no access.
- Billing enforcement changes; portal grant model; any TRACE→COMMAND contract.
- FND-004 work of any kind; unrelated credential rotation.
- Performance tuning of pools/connection counts beyond preserving current behavior.
- Any BYPASSRLS system/application role; any `SECURITY DEFINER` tenant-resolution mechanism; any weakening of RLS to avoid `BLOCKED_INTERNAL_TENANT_CONTEXT`.
- Building the integration-contract/security slice that would legitimately resolve blocked callback contexts (successor work, separately specified).

## Further Notes

- Inbound fax/email callback paths that cannot obtain trustworthy tenant context under the §Implementation-Decisions source matrix **fail closed** and remain PARTIAL/uncommissioned after this slice; closing them (together with GAP-1/GAP-2 fail-open authentication) is a successor integration-security slice, not a workaround here.

- This slice converts the truth-doc roadmap item §10 #1 only; upon independent Gate 003 PASS, canonical truth flips FND-003 to `PASS_CANDIDATE` with the gate SHA as evidence, and the docs branch (`docs/TRACE-CANONICAL-TRUTH-v1` @ `7f0da3c`) rebases onto merged main separately.
- Owner-imposed prohibitions binding this slice: no architecture restart; no `SET ROLE` from `postgres`; no 0022 rewrite; no unrelated credential rotation; no FND-004.
- Vocabulary per `CONTEXT.md`: tenants are firms (`firm_id` UUID remains canonical); Matters are projected locally as Cases; activation authority is upstream (SaaS Admin) and untouched here.
