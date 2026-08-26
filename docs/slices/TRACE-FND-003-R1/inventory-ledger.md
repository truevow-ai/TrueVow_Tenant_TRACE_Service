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

## Batch 06 — Trusted callers only (3 sites; reclassified per owner review)

Provider authentication ≠ tenant authentication. Surfaces whose tenant identity must itself be *discovered* via a tenant-table query cannot be trusted callers under real RLS (circularity) — they moved to the Ticket 09 fail-close set.

| Site(s) | File | Context source | Target class | Invariant |
|---|---|---|---|---|
| :157 | services/matter_activation.py | signed envelope `tenant_id` (9-ref manifest validated) | INTERNAL_SCOPED | idempotency keyed on event_id; rejection conditions precede projection |
| :43,:81 | routes/signing.py | authenticated `ctx.firm_id` (attorney `/send` flow + `_get_case(firm_id)` helper) | REQUEST_SCOPED / INTERNAL_SCOPED | attorney-side only; webhook handler (:115+) excluded |

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

## Fail-close set (Ticket 09) — 13 sites

All surfaces that need tenant-owned data but hold no trustworthy tenant UUID before their first tenant-table access. R1 behavior: raise `BLOCKED_INTERNAL_TENANT_CONTEXT`; long-term resolution = Class E trust-resolution contract.

| Site(s) | File | Why untrusted |
|---|---|---|
| :88,:146,:189,:275,:292 | services/inbound.py | external identifiers (fax/email headers) drive lookups; GAP-1/GAP-2 fail-open auth |
| :74 | routes/webhooks.py | fax-status callback; "without RLS / system role" expectation is the defect |
| :129 | routes/signing.py | DocuSeal completion webhook: verified provider signature, but `submission_id → case/firm` discovery requires tenant-scoped read first |
| :67,:111,:139,:180,:218,:250 | routes/client_portal.py | `_verify_client_access()` receives caller-supplied identity/matter ids and discovers tenant via ClientAccessProjection — circular under RLS; `/access` same pattern |

## Non-runtime lanes (classified, out of scope)

`alembic env.py` URL resolution → MIGRATION_TEST_ADMIN (Ticket 02 re-contracts it) · `tests/*` harness engines · `scripts/*` tooling · conftest placeholder URLs → MIGRATION_TEST_ADMIN.

## Verdicts

0. **Progress log** (evidence SHAs on `trace/TRACE-FND-003`): T01 `18745cb` → T01-R1 `0a52a14` · T03 `787f6a4` · T02 `6b3c058` · **T05 MIGRATED `173f597`** (batch-05 rows = TENANT_REQUEST_SCOPED/INTERNAL_SCOPED via canonical seam; guard test `test_fnd003_r1_session_guard.py` now enforces zero bare opens in qa/liens/evidence routes). · **T06A MIGRATED `d4914c1`** (matter.activated envelope tenant + attorney signing/send; guard paths fixed — original allowlist used nonexistent `app/api/routes/`, silently erroring since creation; real inventory re-baselined at 43 sites + 2 seam impl). · **T08 MIGRATED `bd88ccf`** (`0cdae80` repair: DocuSeal webhook site :131 restored to T06B scope; audit writer fail-closed without firm, webhooks fax-status audit best-effort). · **T07A MIGRATED `e73e094`** (providers/followup/fact_review/evidence/chronology — 14 sites threaded with required `firm_id`; jobs/qa/evidence-routes/client-portal/main/tests updated; export path gained missing `Case.firm_id` filter; portal call threads existing ctx.tenant_id, discovery defect itself stays on PORTAL-TRUST-001). Remaining bare opens: T07B shared stores (13: consent_ledger 3, event_store 3, policy_registry 7), T06B signing webhook (:131), PORTAL-TRUST-001 client_portal (6), T09 inbound trio (webhooks :74 + inbound.py 5), T11 main.py (:110).

1. **Ticket 05 stays whole** — one uniform context pattern (authenticated `ctx.firm_id`), 12 sites, reviewable diff. No 05A/05B split.
2. **Watch-item:** Batch 07 is the largest (27 sites). It is internally uniform (helper adoption), but if its diff proves unreviewable at implementation time, split 07A services / 07B shared-foundation — sizing adjustment, no architecture impact, recorded here when done.
3. Baseline after reclassification: **INVALID_BYPASS_PATH = 13 sites** (inbound.py cluster ×5, webhooks.py:74, signing.py:129, client_portal.py ×6) → must be 0 after Ticket 09.
4. Reclassification history: v1.1 of this ledger — owner review moved DocuSeal-webhook discovery and Client Portal access-projection discovery out of Ticket 06 into Ticket 09 (provider authentication ≠ tenant authentication; tenant-discovery-via-tenant-table is circular under real RLS).
