# TRACE-FND-003-R1 — Session Inventory Ledger (Ticket 04)

| | |
|---|---|
| **Baseline frozen at** | `cc36a8d` (+ additive R1 commits 01/03; neither migrates callers) |
| **Scan pattern** | direct operational opens: `async_session_maker(`, engine connect/begin, `create_async_engine`, runtime-URL resolution |
| **Raw occurrence count** | **57** (matches spec-time estimate) |
| **Rule** | Batches flip rows; no re-scans. Final state must show `INVALID_BYPASS_PATH = 0` |

## Classification legend

`TENANT_REQUEST_SCOPED` (request dep · ctx.firm_id) · `TENANT_INTERNAL_SCOPED` (helper · explicit trusted source) · `GLOBAL_READ_ONLY` (proven tenant-agnostic) · `MIGRATION_TEST_ADMIN` (tooling lane only) · `INVALID_BYPASS_PATH` (unclassified bypass — must reach 0)

## Batch 05 — Attorney-route callers (12 sites)

| Site(s) | File | Context source | Target class | Invariant |
|---|---|---|---|---|
| :57,:90,:157,:232,:252 | routes/qa.py | `ctx.firm_id` (Depends) | REQUEST_SCOPED | demand-ready gate untouched |
| :58,:81,:106,:127 | routes/liens.py | `ctx.firm_id` | REQUEST_SCOPED | lien CRUD semantics unchanged |
| :80,:116,:354 | routes/evidence.py | `ctx.firm_id` | REQUEST_SCOPED | fact-review authorization order preserved |

## Batch 06 — Portal / activation / webhook-trusted callers (10 sites)

| Site(s) | File | Context source | Target class | Invariant |
|---|---|---|---|---|
| :67,:111,:139,:180,:218,:250 | routes/client_portal.py | access-grant → firm mapping | INTERNAL_SCOPED | grant verification precedes any tenant read |
| :43,:81,:129 | routes/signing.py | HMAC-verified DocuSeal submission → case → firm | INTERNAL_SCOPED | vendor-signed lookup is the trusted authority; token never logged |
| :157 | services/matter_activation.py | signed envelope `tenant_id` (9-ref manifest validated) | INTERNAL_SCOPED | idempotency keyed on event_id; rejection conditions precede projection |
| :74 | routes/webhooks.py | **none trusted today** | **INVALID_BYPASS_PATH** | "without RLS / system role" comment is the defect; → Ticket 09 |

## Batch 07 — Services + shared-foundation stores (27 sites)

| Site(s) | File | Context source | Target class | Invariant |
|---|---|---|---|---|
| :164 | services/chronology.py | calling flow's case/firm | INTERNAL_SCOPED | EvidenceFact bridge behavior unchanged |
| :129,:173,:190,:289,:498,:540 | services/evidence.py | calling flow's case/firm | INTERNAL_SCOPED | contradiction detection order preserved |
| :68,:121,:196,:232,:264 | services/fact_review.py | route ctx propagated in | INTERNAL_SCOPED | reviewer authority = attorney ctx |
| :41 | services/followup.py | scheduled job iterates tenants explicitly | INTERNAL_SCOPED | per-tenant GUC per iteration; no cross-tenant sweep |
| :60 | services/providers.py | upload-flow caller ctx | INTERNAL_SCOPED | NPI match ≠ fax authorization rule untouched |
| :162,:213,:237 | shared/consent_ledger.py | owning flow's tenant | INTERNAL_SCOPED | append-only semantics |
| :80,:116,:153 | shared/event_store.py | owning flow's tenant | INTERNAL_SCOPED | append-only semantics |
| :62,:97,:142,:163,:182,:198,:215 | shared/policy_registry.py | tenant rows: owning flow · profiles: global | MIXED (INTERNAL_SCOPED + GLOBAL_READ_ONLY) | jurisdiction_profiles reads require written justification at migration |

## Single-site tickets

| Site | File | Context source | Target | Invariant |
|---|---|---|---|---|
| :75 | core/audit.py | action-carried `firm_id` | Ticket 08 | INSERT-only under real RLS |
| :110 | main.py `/ready` | n/a — schema probes only (`LIMIT 0`, alembic_version) | **GLOBAL_READ_ONLY** (no change; Ticket 11 extends endpoint) | never returns tenant rows |

## Fail-close set (Ticket 09)

| Site(s) | File | Why untrusted | Current class → target |
|---|---|---|---|
| :88,:146,:189,:275,:292 | services/inbound.py | external identifiers (fax/email headers) drive lookups; GAP-1/GAP-2 fail-open auth | INVALID_BYPASS_PATH → fail-closed `BLOCKED_INTERNAL_TENANT_CONTEXT` |
| :74 | routes/webhooks.py | same trust deficit (fax status) | INVALID_BYPASS_PATH → fail-closed |

## Non-runtime lanes (classified, out of scope)

`alembic env.py` URL resolution → MIGRATION_TEST_ADMIN (Ticket 02 re-contracts it) · `tests/*` harness engines · `scripts/*` tooling · conftest placeholder URLs → MIGRATION_TEST_ADMIN.

## Verdicts

1. **Ticket 05 stays whole** — one uniform context pattern (authenticated `ctx.firm_id`), 12 sites, reviewable diff. No 05A/05B split.
2. **Watch-item:** Batch 07 is the largest (27 sites). It is internally uniform (helper adoption), but if its diff proves unreviewable at implementation time, split 07A services / 07B shared-foundation — sizing adjustment, no architecture impact, recorded here when done.
3. Baseline: **INVALID_BYPASS_PATH = 2** (inbound.py cluster, webhooks.py:74) → must be 0 after Ticket 09.
