# TRACE — Canonical Truth

| | |
|---|---|
| **Version** | 1.3 |
| **Date** | 2026-08-23 |
| **Authority** | This document controls on any conflict with any other file in this repository, including `AGENTS.md`, archived planning documents, and historical ADRs. |
| **Basis** | Reconciliation of the as-built system (branch `trace/TRACE-FND-003` @ `cc36a8d`), the shared memory vault (689 entries through 2026-08-21), and three rounds of owner rulings (2026-08-23). |
| **Companion docs** | `../CONTEXT.md` (glossary) · `docs/TRACE-Agent-Coding-Instructions.md` (conduct rules) · `docs/adr/` (historical decision records) · `docs/archive/` (superseded planning corpus) |

---

## 0. How to use this document

- **Agents:** this is the single source of truth for what TRACE *is* and what is *built*. Never implement from archived documents or historical ADRs.
- **Every substantive claim carries a status label** (§7 legend). Labels change only with evidence: a commit hash, a gate result, or a test-suite run recorded here.
- **Commercial truth and implementation truth are recorded separately** (§3). A missing implementation never demotes a settled commercial decision to "TBD".
- **Current vs target architecture are recorded separately** (§4, §5). Unmerged experiments are never described as built.

## 1. Mission and boundaries

**Canonical name:** `TRACE — Pre-Litigation Matter Development & Readiness`.

TRACE is TrueVow's deterministic pre-litigation operating and readiness layer. It takes an activated Matter and develops it — representation, conflict clearance, engagement execution, activation, treatment records, evidence, chronology, readiness — until an attorney can judge it demand-ready and export it for settlement.

| Name | Status |
|---|---|
| "Treatment Record Acquisition and Chronology Engine" | **RETIRED** — historical only |
| "Client Engagement and Case Readiness" | **SUPERSEDED** — intermediate descriptor (commit `3339798`) |
| "TRACE — Pre-Litigation Matter Development & Readiness" | **CANONICAL** |

**Boundary:** TRACE ends at demand-ready export. Settlement economics belong to SETTLE; capture belongs to INTAKE; measurement belongs to COMMAND. TRACE holds no opinion outside the pre-litigation development window.

## 2. Ecosystem position and contracts

Canonical lifecycle language (four products, **not** four sequential stages):

> **INTAKE Captures. TRACE Develops. SETTLE Resolves. COMMAND Measures.**

The case-processing path is principally `INTAKE → TRACE → SETTLE`; COMMAND measures across the ecosystem.

| Contract | Status |
|---|---|
| `matter.activated` consumption (signed webhook, per-link key `tv-saas-admin-to-trace-v1`, WebhookSignature v1.0, 300s tolerance + `event_id` replay guard) | **BUILT-TESTED** (17 golden fixture tests) |
| TRACE → SETTLE handoff | Demand-ready export is the boundary artifact; deeper integration **NOT PRESENT** |
| TRACE → COMMAND contract | **NOT DEFINED / NOT BUILT.** Do not invent one. |
| Legacy bearer-token cutoff | 2026-09-01 (recorded contract normalization) |

**Activation chain (canonical, per owner ruling):**

```
Engagement/internal RETAINER
        |  prepares/completes activation prerequisites
        v
activation command
        v
SaaS Admin — CANONICAL MATTER AUTHORITY
        |  activates the Matter; durable outbox
        v
signed matter.activated
        v
TRACE — validates (9-evidence manifest, rejection-gated, idempotent)
        v
TRACE Case (local projection)
```

TRACE accepting `matter.activated` means **TRACE successfully projected an already-activated Matter** — it is not the activation transition itself. Code/docstring wording calling RETAINER the direct emitter is stale contract drift (§9).

## 3. Commercial truth (settled) vs implementation status

**Commercial decision — CANONICAL:**

| Tier | Price | Plan code |
|---|---|---|
| TRACE Start | $35 / activated Matter | `trace_start_v1` |
| TRACE Essential | $179 / activated Matter | `trace_essential_v1` |
| TRACE Complete | $299 / activated Matter | `trace_complete_v1` |

- For approved active INTAKE firms: **first 12 activated Matters receive Complete at $0**. Before Matter 13 the firm must explicitly select/confirm its default TRACE tier. **No silent billing.**
- **Billing trigger:** canonical activated Matter. **System of record for counts/entitlement:** the Billing ledger. TRACE does not compute the first-12 counter.
- `selected_trace_plan_code` captured at activation and stored on the case is execution context / projection of the chosen plan — **not** an authoritative billing counter.

**Implementation status:**

| Item | Status |
|---|---|
| Tier capability gates in TRACE (`app/services/entitlements.py`, 16 capabilities across 3 plans) | **BUILT-TESTED** |
| Billing-ledger enforcement of per-Matter pricing and first-12 rule | **VERIFY AT BILLING SERVICE** — if absent, that is implementation drift in Billing, not pricing ambiguity |

**Superseded pricing models (never resurrect):** $299/mo + $199 per settled case (PRD v0.5 §9.2); Solo $199/case + $1,199/$1,999 tiers (Market Research v5.0); pilot-era $35/$179/$299 *per-matter variants with different packaging*.

## 4. Entities and identity

Per glossary (`../CONTEXT.md`):

- **Matter** — canonical platform/product business entity; identified by `matter_id`; SaaS Admin is canonical Matter authority.
- **TRACE Case** — TRACE-local operational projection of a Matter; identified by `case_id`. One activated Matter → at most one Case projection. `matter_id != case_id`; never interchangeable.

| Identity item | Status |
|---|---|
| Upstream `matter_id` accepted in `matter.activated` payload; local `case_id` minted on projection | **BUILT-TESTED** |
| Upstream `matter_id` persisted in legacy `cases.intake_record_id` | **KNOWN DEBT** — do not treat as evidence the IDs are the same |
| `trace_client_access_projections.matter_id` populated with TRACE `case_id` | **KNOWN DEBT** — naming conflation; do not "fix" during doc work |
| First-class `matter_id` column on cases; MDM-minted canonical identity end-to-end | **TARGET / NOT BUILT** |
| Clerk organization ↔ canonical TrueVow tenant UUID mapping | **KNOWN DEBT — platform-level.** Do not canonize Clerk `org_id` as the database tenant key. |

**Auth (current vs target):**

```
CURRENT:  Clerk App 3 (RS256 via JWKS) in production/staging; AUTH_MODE=local HS256 in dev/test.
          No Supabase Auth runtime exists on any branch. IAM-001 was an UNMERGED experiment.
KNOWN DEBT: Clerk org identity is not cleanly mapped to canonical TrueVow tenant UUID platform-wide.
TARGET:   Resolve the canonical identity contract (tenant UUID remains canonical).
```

## 5. As-built architecture

FastAPI service on port **3036**; Customer Portal (:3031, Next.js) proxies via generated HS256 JWTs in dev / Clerk session in prod.

| Layer | As-built | Status |
|---|---|---|
| Runtime DB | Supabase Postgres `cnbzuiuyppzrygxllgxj`, shared project, `trace` schema; Postgres-only, SQLite removed (FND-001); Alembic head `0022_fnd003_rls_reconciliation` under `infra/database/migrations/versions` | **BUILT-TESTED** |
| Tenant isolation | FORCE RLS on 43 tenant tables, canonical `tenant_isolation_fnd003` policies; parameterized `set_config` GUCs (`app.current_tenant_id/user_id/user_role`) in `get_db`; app-level `firm_id` filters remain mandatory | **BUILT-TESTED** — gate blocked on runtime role: Supabase `postgres` role has `rolbypassrls=true` (§10) |
| PHI store | `trace_phi` schema, app-layer AES-256-GCM (`app/core/crypto.py`), strict 32-byte key, fail-closed (`PhiKeyError`/`PhiDecryptError`), `/ready phi_key` gate; 49 legacy rows re-keyed 2026-08-20 | **BUILT-TESTED** |
| Auth | `AUTH_MODE=clerk` (RS256/JWKS) \| `AUTH_MODE=local` (HS256); startup enforces clerk in production | **BUILT-TESTED** |
| LLM | Provider abstraction: `azure_openai` \| `deepseek_api` \| `anthropic`; live selector env var `LLM_SERVICE_PROVIDER`; DeepSeek API in current use; `LLM_PHI_ALLOWED=false`; `/llm-test` | **BUILT-TESTED** (`llm_backend` settings field is vestigial — §9) |
| OCR | Four-tier pipeline (`app/services/ocr_pipeline.py`): pypdf → Mistral OCR 4 (self-hosted sidecar or API) / Tesseract fallback → Mistral cloud when confidence < 80% | **BUILT-TESTED** |
| NLP / extraction | OpenMed NER + regex fallback; `extraction_confidence` 5-label taxonomy (CONFIRMED / LIKELY_MATCH / NEEDS_CLIENT_CONFIRMATION / NEEDS_STAFF_REVIEW / DO_NOT_REQUEST); NPI registry lookup; NPI match ≠ fax authorization | **BUILT-TESTED** |
| Fax | Outbound via `FAX_PROVIDER` — **default `twilio`** (pre-signed URL flow), `documo` supported; inbound fax webhook present | **BUILT-TESTED** (inbound auth fail-open — §8) |
| Inbound email | Resend webhook → `process_inbound_email()`; HMAC verified **when configured** | **PARTIAL** — fail-open when secret/header absent (§8) |
| E-signature | Self-hosted DocuSeal client (`app/services/signing.py`): package send, raw-body HMAC webhook verify, replay guard, PENDING_SIGNATURE→INITIALIZATION advance on webhook | **BUILT-STALE** — service uncommissioned (no subscription/deployment); dev expects 502 |
| Evidence layer | EvidenceFact, SourceLocation (atomic provenance), ContradictionPair, MissingEvidenceSignal, FactVersion — wired into chronology, flag detectors, fact review | **BUILT-TESTED** |
| Shared foundation | AuthorityGate (AUTH-001..020 registry), ConsentLedger (append-only), PolicyRegistry (versioned tenant/jurisdiction policy), EventStore, StateMachine (`app/shared/`) | **BUILT-TESTED** |
| Client portal APIs | `/api/client/v1/*` routes + ClientAccessProjection (temporary mirror of Shared Platform grants; ACTIVE_MATTER added after `matter.activated`) | **BUILT-TESTED** |
| Case lifecycle | 7 stages `PENDING_SIGNATURE → INITIALIZATION → RETRIEVAL → PROCESSING → CHRONOLOGY_READY → ATTORNEY_REVIEW → DEMAND_READY`; gates: HIPAA signed / provider lock (Checkpoint 1) / faxes sent (Checkpoint 2) / PRIORITY flags annotated (demand-ready) | **BUILT-TESTED** |
| Export | PDF + JSON (`trace_export_version 1.0`), 403 unless DEMAND_READY, non-suppressible "ATTORNEY WORK PRODUCT — PRIVILEGED AND CONFIDENTIAL" disclaimer | **BUILT-TESTED** |
| Tests | 28 test files, ~156 collected functions; guarded suite 163/163 at FND-003; destructive tests require `TRACE_TEST_PG_URL` + `TRACE_TEST_ALLOW_DESTRUCTIVE=TRUEVOW_NONPROD_TEST_DB` | **BUILT-TESTED** |
| Deployment | Fly.io pilot deployment (`truevow-trace.fly.dev`, HEALTHY 2026-08-01) | **BUILT-STALE** — not currently commissioned |

## 6. Domain registries (canonical v1)

**Flag registry — the shipped 15-value `FLAG_TYPES` set (`app/models/event_node.py`) is canonical:**

```
TREATMENT_GAP, BILLING_DISCREPANCY, ESCALATION_FLAG, DELAYED_INITIAL_TREATMENT,
SUDDEN_TREATMENT_STOP, FOLLOWUP_NO_RECORD, NON_COMPLIANT_LANGUAGE,
BILL_NO_PROCEDURE_REPORT, CREDIBILITY_LANGUAGE, NEW_PROVIDER_NO_REFERRAL,
CHANGING_INCIDENT_DESCRIPTION, CHANGING_SYMPTOM_COMPLAINTS,
PRE_EXISTING_CONDITION_SIGNAL, FUNCTIONAL_IMPACT, IMAGING_CROSS_REFERENCE
```

Priorities: `PRIORITY | ADVISORY | INFORMATIONAL` (NOT NULL + CHECK, migration 0021). Demand-ready gate counts unannotated PRIORITY flags.

**Superseded flag specifications — historical design, not parallel registries:**
- PRD T1-01..T1-06 / T2-01..T2-06 taxonomy
- Market Research v5.0 15-flag naming set
- ADR-004 legacy named Tier-2 registry (e.g., `MEDICATION_ESCALATION`, `IMAGING_INCONSISTENCY`)

*Rule: historical flag concepts may inform future enhancements, but their old identifiers are not backlog requirements unless explicitly re-approved. Never "fix" the live enum to match an old ADR.*

**Readiness:** current `GET /cases/{id}/readiness` returns a slim summary (stage, HIPAA status, provider/lien counts, export readiness) — **PARTIAL**. The full capability is §10 roadmap.

## 7. Status label legend

| Label | Meaning |
|---|---|
| `PRODUCTION-PROVEN` | **Reserved.** Requires current production deployment + actual production use + evidence. Nothing holds this label in v1. |
| `BUILT-TESTED` | Implemented and covered by the current passing suite/gates. |
| `BUILT-STALE` | Implemented but not currently commissioned/verified against live dependencies. |
| `PARTIAL` | Exists in reduced form vs the decided capability. |
| `SPEC-ONLY` | Decided/recorded but never implemented. |
| `NOT PRESENT` | No code, no decision. |
| `RETIRED` | Explicitly abandoned; see §12 before reconsidering. |

## 8. Open security gaps (blockers for production commissioning)

**GAP-1 — Inbound email webhook auth is fail-open. `HIGH`.**
As built: `RESEND_WEBHOOK_SECRET` exists and is read (`settings.resend_webhook_secret`); a supplied secret/signature mismatch is rejected. **But `_verify_hmac()` (`app/services/inbound.py:56`) returns `True` whenever the secret OR the signature header is absent**, explicitly allowing unverified ingestion. An unconfigured deployment accepts unauthenticated inbound email payloads and attachments.
Required: fail closed outside explicit development/test mode; validate per the commissioned Resend contract.

**GAP-2 — Inbound fax webhook auth is fail-open. `HIGH`.**
`process_inbound_fax()` hardcodes `fax_webhook_secret = ""` (`app/services/inbound.py:220`), which makes the same helper always pass; `webhooks.py:64` checks only when the setting is non-empty.
Required: commissioned secret + fail-closed verification.

**Production consequence:** neither inbound document webhook path may receive `PRODUCTION-PROVEN` (or support production commissioning) until authentication is fail-closed.

## 9. Known debts (documented, not repaired in this pass)

| Debt | Note |
|---|---|
| `matter_id` stored in `cases.intake_record_id` | Identity conflation; see §4 |
| `client_access_projections.matter_id` holds a `case_id` | Naming conflation; do not infer interchangeability |
| `llm_backend` settings field vestigial | Live selector is `LLM_SERVICE_PROVIDER`; conduct-guide §3.9 wording updated to match |
| Activation handler docstrings say "from RETAINER" | Stale contract wording; canonical chain is §2 |
| AGENTS.md drift (fax default, name, pipeline line) | Corrected in this reconciliation |
| Orchestrator `config.yaml` says "Phase-1D-complete" | Stale ecosystem-side record (outside this repo) |
| ADR-005 claimed Spec Part 9.6 edit absent | Historical inconsistency; ADR-005 identity approach superseded by §4 rulings |

## 10. Roadmap

### DECIDED-BUT-UNBUILT (evidence-backed, in priority order)

| # | Item | Evidence / blocker |
|---|---|---|
| 1 | Commission non-bypass Supabase runtime role (`rolbypassrls=false`) to close the FND-003 RLS gate | Vault 2026-08-21; AGENTS.md HIGH; guarded suite 163/163 already green |
| 2 | Close GAP-1/GAP-2 inbound webhook auth (fail-closed + commissioned secrets) | §8, code lines cited |
| 3 | Matter Readiness Board — attorney-facing operational view of complete/waiting/missing/contradictory evidence and next-milestone readiness. **Status: DECIDED-BUT-UNBUILT.** ADR-004's five-column × four-status layout is a **SUPERSEDED DESIGN REFERENCE**, not a binding UI contract | Current `/readiness` is PARTIAL (§6) |
| 4 | DocuSeal commissioning (self-hosted deployment or approved subscription) to make the signing path live | `signing.py` BUILT-STALE |
| 5 | Resolve canonical identity contract: Clerk org ↔ TrueVow tenant UUID mapping (platform-level) | §4 |
| 6 | First-class `matter_id` storage on cases; fix projection naming conflation | §4, §9 |
| 7 | Independent Gate-002 PASS for FND-002 (awaited since re-key completion 2026-08-20) | Vault |
| 8 | Recommission staging/production Fly deployment (prerequisite for any `PRODUCTION-PROVEN` label) | §5 deployment row |

### IDEA / TBD (no commitment; requires explicit product decision)

- Historical flag concepts (e.g., medication-escalation detection) as *new* capabilities under the v1 registry — requires re-approval, never a rename of existing enum values.
- ModernBERT long-context NLP evaluation (`NLP_LONG_CONTEXT_BACKEND`) — ADR-003/004 evaluation never executed.
- Deeper SETTLE integration beyond demand-ready export.
- Any TRACE → COMMAND contract.

## 11. Maintenance protocol (mandatory)

1. **Who:** any agent working this service; the owner on rulings.
2. **When:** at slice acceptance — never batched across sessions.
3. **Evidence rule:** update a status label **only** with accepted evidence: merged commit hash, gate/test-suite result, or owner ruling. No label changes from memory or assumption.
4. **How:** edit in place; bump the version table; append a one-line entry to the revision log below.
5. **Slice flow (kanban):**

   | State | Authority / skill |
   |---|---|
   | IDEA/TBD | Truth doc + settled-path filter — not authorized to build |
   | DECIDED-BUT-UNBUILT | Canonical truth — decision exists, no implementation claim |
   | SPEC | `to-spec` — one bounded implementation contract; declares its status delta (e.g., PARTIAL → BUILT-TESTED) |
   | TICKETS | `to-tickets` — tracer bullets, independently testable, blocking edges |
   | BUILDING | `implement` — one ticket per branch/purpose, TDD at agreed seams |
   | SELF-REVIEW | `code-review` — Standards axis + Spec axis; builder fixes findings first |
   | INDEPENDENT VERIFY | TrueVow reviewer/gate — repo inspection, DB evidence, adversarial tests. Builder's green report is NOT Gate PASS |
   | PASS / MERGE / FREEZE | CTO gate records SHA, freezes unit |
   | TRUTH WRITEBACK | Exit condition — status/evidence updated here from accepted commit/gate; unlocks next slice |

6. **Entry filter:** any proposal matching a §12 settled path is rejected on sight.
7. **Writeback:** per `AGENTS.md`, session results go to the shared memory vault.

### Anti-drift rule — every `to-spec` invocation gets exactly three inputs

```
1. docs/TRACE-CANONICAL-TRUTH.md
2. the actual current repository / accepted base SHA
3. one explicitly authorized roadmap item
```

Not: all historical PRDs + all ADRs + all market research + agent imagination.

### CHANGE MANAGEMENT

```
TRACE is evolved through bounded vertical slices, not phase-scale rewrites.

Default:
Preserve the current canonical architecture and existing approved seams.

Every implementation change follows:
CANONICAL TRUTH → TO-SPEC → TO-TICKETS → IMPLEMENT → CODE-REVIEW
→ INDEPENDENT TRUEVOW VERIFY → GATE PASS → MERGE/FREEZE → CANONICAL TRUTH UPDATE

Architecture changes require:
1. evidence that the existing canonical seam/invariant is insufficient;
2. an explicit ADR or canonical-decision update;
3. a bounded migration strategy;
4. preservation of green intermediate states where practicable;
5. independent Gate PASS.

Unmerged experiments, historical plans, archived specs, and agent suggestions
cannot alter canonical architecture.

No accepted slice requires restarting the system from the beginning.
Wide structural changes use expand-migrate-contract rather than big-bang rewrite.
```

**Revision log**

### Maturity-first entry protocol (ratified 2026-08-23)

Skills are selected by unit maturity — never as a mandatory linear ceremony. Before any Pocock skill is invoked on a unit, the unit is classified in `docs/TRACE-MATURITY-LEDGER.md`:

```
A BUILT_PROVEN          -> protect (no rework)
B BUILT_AWAITING_PROOF  -> verify
C DEFECT/HARDENING GAP  -> repair tickets (to-spec only when blast radius warrants)
D DEFINED FEATURE       -> to-tickets if spec exists; else to-spec
E UNRESOLVED FEATURE    -> wayfinder -> to-spec -> to-tickets
```

Then, for every class that produces code: implement → code-review → independent TrueVow verify → PASS/merge/freeze → truth + ledger writeback.

| Version | Date | Change | Evidence |
|---|---|---|---|
| 1.0 | 2026-08-23 | Initial reconciliation from as-built audit + vault + owner rulings (3 grill rounds) | `cc36a8d`, vault 689 entries, session 2026-08-23 |
| 1.1 | 2026-08-23 | Operating model ratified: architecture frozen as default; Pocock skill chain + TrueVow gates become mandatory change machinery; CHANGE MANAGEMENT + anti-drift three-input rule added (§11) | Owner ruling 2026-08-23 |
| 1.2 | 2026-08-23 | Lifecycle adoption ruled PROSPECTIVE: completed work grandfathered; proportionality for small fixes; skills subordinate to canonical truth; four-eyes verification retained (§11) | Owner ruling 2026-08-23 |
| 1.3 | 2026-08-23 | Maturity-first entry protocol added; TRACE Completion/Maturity Ledger v1.0 published (`docs/TRACE-MATURITY-LEDGER.md`); FND-003-R1 classified C (wide/security-sensitive), proceeds at IMPLEMENT stage | Owner ruling 2026-08-23; Sales Ops control-plane learning |

### Adoption semantics of the Pocock lifecycle (ratified 2026-08-23)

- **Prospective only.** Previously accepted TrueVow gates are accepted historical work; completed development is grandfathered — no retroactive re-specification.
- **Proportionality.** Tiny repairs use a small spec/ticket; substantive slices use the full flow. No ceremony for ceremony's sake.
- **Tools, not authority.** The skills shape *how* engineering work is executed; canonical truth and accepted TrueVow decisions remain authoritative over any skill convention. If a convention proves counterproductive, the workflow adjusts — the architecture does not bend to accommodate tooling.
- **Four-eyes separation stands.** `code-review` conformance to spec never substitutes for independent TrueVow verification of repo, database, migration, and security state.

## 12. Settled / Superseded Paths (anti-resurrection appendix)

| Superseded path | Canonical path | Status | Purpose of record |
|---|---|---|---|
| Auth0 | Clerk App 3 | RETIRED | Prevent Auth0 resurrection |
| Supabase Auth / IAM-001 experiment | Clerk current; canonical tenant mapping unresolved (§4) | UNMERGED/RETIRED EXPERIMENT | Never treat IAM-001 as built |
| Separate TRACE Supabase project (ADR-001 #21) | Shared project + `trace`/`trace_phi` schemas | RETIRED | Current persistence topology |
| pgcrypto PHI design (Spec §2.1) | App-layer AES-256-GCM | RETIRED | Current encryption authority |
| SQLite runtime / `create_all` dev paths | Postgres-only + Alembic (FND-001) | RETIRED | FND-001 contract |
| Azure GPT-4o-mini as locked billing LLM; "No DeepSeek API (any version)" (Spec §2.3) | Provider abstraction; DeepSeek API in use | RETIRED | Quota reality; abstraction is the contract |
| PaddleOCR-VL / deepdoctection+DocTr OCR stacks | Four-tier pypdf→Mistral/Tesseract→Mistral cloud | RETIRED | As-built pipeline |
| Fax.Plus-first vendor posture; iFax | `FAX_PROVIDER`: twilio (default) / documo | RETIRED | As-built vendor set |
| HIGH/MEDIUM/LOW provider confidence | 5-label taxonomy (§5 NLP row) | RETIRED | As-built taxonomy |
| PRD T1/T2 flag taxonomy; Market Research flag names; ADR-004 named Tier-2 registry | 15-value `FLAG_TYPES` registry (§6) | SUPERSEDED | Prevent enum "fixes" toward old names |
| ADR-004 five-column × four-status board UI | Capability decided; UI geometry free (§10 item 3) | SUPERSEDED DESIGN REFERENCE | Product promise without frozen mockup |
| Old pricing models (§3) | $35/$179/$299 per activated Matter | RETIRED | Prevent billing regression |
| "Treatment Record Acquisition and Chronology Engine"; "Client Engagement and Case Readiness" | Pre-Litigation Matter Development & Readiness | RETIRED / SUPERSEDED | Current product boundary |
| INTAKE-outbox auto case creation; `matter.ready_for_signature` trigger | SaaS Admin signed `matter.activated` (§2) | RETIRED | Activation authority |
| Attorney-initiated `POST /cases` as primary creation path | Activation-projected case creation (attorney ad-hoc cases remain a dev/test convenience) | RETIRED for production flow | Canonical chain |
| ADR-005 `clerk_org_id`-as-tenant-key migration as written | Canonical tenant UUID stays; resolve org↔UUID mapping instead (§4) | SUPERSEDED | Identity ruling 2026-08-23 |
| `INTAKE → TRACE → SETTLE → COMMAND` as four sequential stages | Four products; processing path INTAKE→TRACE→SETTLE (§2) | RETIRED | Lifecycle language |

*Where the record does not prove an abandonment rationale, none is invented: the entry stands as "Reason not recorded; superseded by <decision/ruling date>".*

## 13. Evidence sources

- Branch `trace/TRACE-FND-003` @ `cc36a8d` (FND-001 → FND-003 commit series on `main`/branches)
- Shared memory vault: `../TrueVow_Shared_Codebase_Memory/memory.db` (689 entries; digest `../TrueVow_Context/memory-digest.md`)
- `../ORCHESTRATOR_PROGRESS.md` (RC v3 pilot, 2026-08-01)
- Owner rulings: grill Rounds 1–3 + operating-model ratification, 2026-08-23 (this document's controlling authority)
