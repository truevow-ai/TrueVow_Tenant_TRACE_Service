# TRUEVOW TRACE - FINAL POST-GATE-003 PRODUCT & IMPLEMENTATION PLAN

*Boundary-corrected plan after repository review, ontology gap analysis, and reconciliation with TRACE-PLAN-DMG-SETTLE-001*

**Status:** ACCEPTED PLANNING DIRECTION / Class D — DEFINED FEATURE. Implementation remains gated by independent Gate 003 PASS.

**Business objective:** make TRACE the law firm’s evidence-backed matter-development and readiness workspace: it should reduce missing evidence, missed follow-up, weak documentation, and premature demand preparation while preserving attorney authority. TRACE develops the matter; it does not value or resolve it.

## 1. Final product boundary

Canonical product model: INTAKE captures; TRACE develops; SETTLE resolves; COMMAND measures. TRACE begins after matter activation and ends when a governed, attorney-approved settlement-context handoff is ready. The handoff is a projection of TRACE truth, not a copy of TRACE’s database.

| TRACE owns | TRACE does not own |
|---|---|
| Source-linked evidence, records, bills, chronology and completeness | Settlement ranges, case value, demand amount recommendations |
| Treatment development, gaps, functional/client impact support | Offer acceptance/rejection recommendations or negotiation strategy |
| Documented economic-damages support: medical expense, wage loss, property/out-of-pocket | Comparable outcome intelligence or public benchmark analysis |
| Pre-settlement lien/reimbursement discovery and documentation status | Lien negotiation/resolution, settlement allocation or disbursement |
| Liability evidence/signals and comparative-fault evidence/signals | A hidden “liability strength” valuation score |
| Coverage/limits evidence and status | Settlement economics based on policy limits |
| Matter readiness, blockers, limitations and attorney review | Settlement confidence or predicted outcome |
| De-identified, versioned, approved handoff preparation | Shared settlement contribution intelligence |

## 2. What the repository already proves exists

- TRACE already models a case-development lifecycle through PENDING_SIGNATURE, INITIALIZATION, RETRIEVAL, PROCESSING, CHRONOLOGY_READY, ATTORNEY_REVIEW and DEMAND_READY.
- EvidenceFact is already the atomic source-linked clinical fact with review status, versioning, contradiction and duplicate semantics.
- The chronology engine already projects source-linked evidence into medical chronology and functional-impact tags.
- TRACE already contains document/evidence, contradiction, custody, consent, provider and operational workflow foundations. The post-Gate-003 plan therefore requires reconciliation before new migrations.

## 3. Corrected ontology: extend, do not duplicate

| Capability | Final decision | Implementation rule |
|---|---|---|
| Medical chronology | KEEP existing | Extend existing EvidenceFact/chronology only where needed. |
| Records & bills completeness | KEEP / strengthen | Derived completeness status must point to source/request evidence. |
| Treatment gaps | KEEP existing semantics | No second treatment-gap ontology; gap is not a negative valuation conclusion. |
| Medical expense support | ADD/EXTEND in TRACE | Source-linked documented amount/status; no settlement multiplier. |
| Wage-loss support | ADD/EXTEND in TRACE | Evidence/documentation and review status, not value prediction. |
| Property/out-of-pocket support | ADD only where relevant | Evidence-backed, practice-area applicable; do not force irrelevant categories. |
| Client impact support | ADD/EXTEND | Structured, source/review-aware impact evidence; not pain-and-suffering valuation. |
| Liability | ADD as evidence domain | Facts/signals/issues + attorney-reviewed position where needed; avoid pseudo-objective strength score. |
| Comparative fault | ADD as evidence/position domain | Record source-backed allegations/facts and reviewed position; SETTLE consumes context. |
| Coverage/policy limits | ADD as evidence/status domain | Carrier/coverage/limits/exhaustion/dispute status with provenance; no valuation. |
| Liens/reimbursement | SPLIT boundary | TRACE owns discovery, documentation, claimed/known status before resolution; SETTLE owns negotiation, resolution and payment. |
| Matter readiness | ADD/UNIFY | One readiness assessment, not separate “damages” and “matter” boards. |
| SETTLE handoff | ADD | Versioned, de-identified, attorney-approved contract projection. |

## 4. Features to shed from the prior plan

- Do not create generic `trace_damages_items` if existing EvidenceFact/document/fact models can represent the evidence cleanly. New persistence requires TRACE-DMG-000 proof of necessity.
- Do not create a second lien truth that competes with the existing settlement lien ontology. TRACE stores pre-resolution lien/recovery development; the authoritative resolution lifecycle moves to SETTLE.
- Do not create a separate Damages Readiness Board. Use one Matter Readiness capability with sections.
- Do not use a numeric readiness, case-quality, liability-strength or settlement-potential score. Readiness is categorical, explainable and blocker/limitation based.
- Do not make every possible damages category mandatory. Applicability must be practice-area/case-context driven.
- Do not transmit raw documents, PHI, direct client identifiers or unreviewed narrative simply because SETTLE could use them.

## 5. Missing capabilities that should be added

- Canonical Liability Evidence/Issue model: police/report evidence, admissions, witnesses, citations, disputed facts and attorney-reviewed position without converting it into valuation.
- Coverage & Limits Evidence model: insurer/coverage layer, limits-known status, limits source, reservation/dispute/exhaustion indicators and review state.
- Economic Damages Support model or extensions for wage loss, property loss and out-of-pocket expenses with source provenance and review state.
- Applicability semantics: NOT_APPLICABLE must be distinct from MISSING. This prevents a case from being blocked by evidence that is irrelevant to that matter.
- Staleness semantics for time-sensitive facts such as treatment status, outstanding records, liens and coverage information.
- Attorney-reviewed case-development position where professional judgment is necessary; extraction and signals remain non-authoritative.
- A Settlement Context Readiness Manifest: the minimal de-identified projection SETTLE needs, with explicit limitations and provenance references.

## 6. Unified Matter Readiness

Replace the proposed damages-only readiness concept with one attorney-facing Matter Readiness Assessment. It answers “is the matter sufficiently developed for settlement-context work, and what is still missing?” It never answers “what is the case worth?”

| Readiness section | Examples of deterministic checks |
|---|---|
| Engagement / authority | Representation complete; required consents/authority present. |
| Treatment | Current treatment status known; unresolved material treatment gaps identified. |
| Records & bills | Required records/bills received or explicitly limited; source completeness visible. |
| Evidence | Material evidence gaps/contradictions surfaced; provenance intact. |
| Economic damages support | Applicable medical expense, wage-loss, property/out-of-pocket evidence status. |
| Liability / comparative fault | Material evidence/issues and reviewed position available or limitation declared. |
| Coverage / limits | Known/unknown/disputed status explicit and sourced. |
| Liens / reimbursement | Known claims and documentation status captured; unresolved status declared. |
| Client impact | Applicable source/review-backed impact support available or limitation declared. |
| SETTLE handoff | Privacy validation, attorney approval and packet version complete. |

Recommended readiness outcomes: `READY_FOR_SETTLEMENT_CONTEXT`; `READY_WITH_LIMITATIONS`; `NOT_READY`; `ATTORNEY_REVIEW_REQUIRED`.

`UNKNOWN`, `NOT_APPLICABLE`, `MISSING`, `CONTRADICTED`, and `STALE` remain distinct conditions feeding those outcomes.

## 7. Final TRACE -> SETTLE handoff contract

The SETTLE repository contains historical/current integration documentation that predates the canonical TRACE → SETTLE settlement-context boundary. Do not treat legacy SETTLE integration documentation as architecture authority. During TRACE-STL-001, reconcile the actual SETTLE repository and its accepted contracts against the platform ontology before defining the new cross-product handoff. Matter activation starts TRACE. It must not be reused as the mature TRACE → SETTLE settlement-context boundary. The intended later boundary is an attorney-approved settlement-context readiness transition/event, with the exact canonical event name assigned only after TRACE/SETTLE ontology and event-registry reconciliation.

**TRACE-STL-001 is a two-sided reconciliation gate.** TRACE must not independently define what SETTLE consumes, and SETTLE must not independently dictate what TRACE stores. STL-001 must establish the smallest useful projection consistent with the approved ownership boundary. Only after both repositories, the platform ontology, and the event/transition registries are reconciled may the contract freeze its event name, schema, required/optional fields, authority, transition, privacy classification, versioning, idempotency, and acceptance semantics.

Candidate semantic event: `trace.settlement_context_ready` — **PROVISIONAL ONLY, NOT CANONICAL**. The exact name may be assigned only after the two-sided TRACE-STL-001 ontology, transition and event-registry reconciliation.

The candidate packet may include, subject to STL-001 reconciliation:

- opaque tenant/matter/case references;
- jurisdiction/venue;
- case/incident classification;
- structured treatment/injury context;
- documented economic-damages inputs;
- liability/comparative-fault context;
- coverage/limits status;
- lien/reimbursement development status;
- completeness/blockers/limitations;
- governed source references;
- review/approval metadata;
- schema version;
- correlation/causation identifiers.

It should exclude direct client identifiers and raw PHI by default.

## 8. Post-Gate-003 execution sequence

| Stage | Deliverable | Gate |
|---|---|---|
| TRACE-DMG-000 | Ontology + existing-model reconciliation, including applicability/staleness and lien boundary | No migrations until approved. |
| TRACE-DMG-001 | Domain contract and only necessary persistence extensions | RLS/FORCE RLS/provenance/authority contract. |
| TRACE-DMG-002 | Evidence-development services: economic damages, liability, coverage, lien-development, gaps | No valuation behavior. |
| TRACE-DMG-003 | Unified Matter Readiness service | Explainable categorical result; no score. |
| TRACE-DMG-004 | Governed APIs + Needs You / Waiting on Others / At Risk projections | Derived projections only. |
| TRACE-DMG-005 | Unified Matter Readiness UI | Evidence, missing items, limitations, responsibility, review. |
| TRACE-STL-001 | Two-sided TRACE/SETTLE ontology + contract reconciliation; define the smallest useful de-identified handoff projection only after reviewing both repositories. | Neither side may freeze the contract independently. Freeze event name, schema, fields, authority, transition, privacy, versioning and acceptance semantics only after joint reconciliation. |
| TRACE-STL-002 | Attorney approval lifecycle | AuthorityGate + TransitionContract. |
| TRACE-STL-003 | Signed, idempotent delivery/outbox | No cross-DB writes. |
| TRACE-STL-004 | Privacy, isolation and commissioning proof | Zero prohibited identifiers in serialized payload. |

Controlling order:

```text
Gate 003 PASS
    ↓
TRACE-DMG-000
    ↓
TRACE-DMG-001
    ↓
TRACE-DMG-002
    ↓
TRACE-DMG-003
    ↓
TRACE-DMG-004
    ↓
TRACE-DMG-005
    ↓
TRACE-STL-001
    ↓
TRACE-STL-002
    ↓
TRACE-STL-003
    ↓
TRACE-STL-004
```

## 9. Law-firm and consumer value test

Keep a TRACE feature only if it helps the firm develop a matter more completely, accurately, safely or efficiently, or helps the client by reducing missed evidence, unnecessary delay, documentation errors or opaque decision-making. If a feature merely predicts value, duplicates SETTLE, creates a second source of truth, or adds workflow without changing a legal-service outcome, shed it.

## 10. Definition of Done

- Gate 003 independently passes before feature build begins.
- No duplicate ontology is created; every new object has an owner, authority, provenance, lifecycle and privacy classification.
- One Matter Readiness system exists and distinguishes missing, unknown, not applicable, contradicted and stale.
- Liability, comparative-fault and coverage/limits gaps are filled as evidence domains, not valuation engines.
- Pre-resolution lien development is TRACE; lien resolution/payment is SETTLE.
- TRACE emits no settlement range, demand amount recommendation, offer recommendation, multiplier or negotiation strategy.
- The SETTLE packet is minimal, versioned, signed, idempotent, de-identified and attorney-approved.
- Cross-tenant, PHI/PII leakage, authority, transition and contract tests all pass.

## Source basis

This plan reconciles the owner-approved `TRACE-PLAN-DMG-SETTLE-001` direction with the current TRACE repository and the ratified architecture/ontology addenda. SETTLE repository artifacts are treated as evidence to be reconciled during TRACE-STL-001, not as architecture authority for the future TRACE → SETTLE boundary.
