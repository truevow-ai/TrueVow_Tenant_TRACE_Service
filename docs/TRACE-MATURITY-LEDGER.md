# TRACE Completion / Maturity Ledger

| | |
|---|---|
| **Version** | 1.1 |
| **Date** | 2026-08-30 |
| **Authority** | Classification derived from `docs/TRACE-CANONICAL-TRUTH.md` v1.4, accepted gate history, owner rulings through 2026-08-30, `TRACE-ARCH-ADD-001`, and the final post-Gate-003 planning baseline. This ledger routes work; canonical truth remains the substantive authority. |
| **Purpose** | Entry gate for the Pocock lifecycle: every outstanding unit receives a maturity classification BEFORE a skill is chosen. Skills are selected by maturity — never by how complicated an item looks. |

## Classes

| Class | Meaning | Correct next action |
|---|---|---|
| **A — BUILT_PROVEN** | Built + sufficiently proven | Protect; no Pocock rework |
| **B — BUILT_AWAITING_PROOF** | Implementation done, proof incomplete | Verification only |
| **C — DEFECT / HARDENING GAP** | Intended behavior settled; implementation violates it | Repair ticket(s) → implement → review; to-spec only when blast radius warrants |
| **D — DEFINED FEATURE** | Requirement settled, implementation absent | `to-tickets` if spec exists; otherwise `to-spec` |
| **E — UNRESOLVED FEATURE** | Product/architecture questions remain | `wayfinder` → `to-spec` → `to-tickets` |

## Ledger

### Class A — BUILT_PROVEN (protect)

| Unit | Evidence | Route |
|---|---|---|
| Case lifecycle (7 stages, 4 gates), case/provider/lien/document CRUD | Guarded suite green @ `cc36a8d`; FND-series merges | Protect |
| 43-table FORCE RLS policy layer (migration 0022 + preflight guard) | 15 adversarial tests; suite 163/163 | Protect (runtime enforcement itself = C below) |
| PHI store: AES-256-GCM strict key contract, fail-closed reads | FND-002 merged; `/ready phi_key` | Protect |
| PHI re-key commissioning (49 historical rows, 2026-08-20) | Accepted gate history closed FND-002 before FND-003 began (owner ruling 2026-08-23) — **Class A**, correcting the v1.0 misplacement in Class B | Protect |
| Evidence layer (EvidenceFact/SourceLocation/ContradictionPair/MissingEvidenceSignal/FactVersion) | Wired into chronology/flags/fact-review; covered | Protect |
| Shared foundation (AuthorityGate/ConsentLedger/PolicyRegistry/EventStore/StateMachine) | Implemented and covered | Protect |
| Webhook contract WebhookSignature v1.0 + 17 golden fixtures; EventEnvelope 1.0.1 | Golden fixture tests; RC-v3 pilot PASS | Protect |
| Entitlement capability gates ($35/$179/$299 plan codes) | `entitlements.py`; verified | Protect |
| Demand-ready export (PDF/JSON, 403 gate, disclaimer) | Covered; pilot-era verified | Protect |
| Grandfathered history: Phases 1A–1E, Phase 2A, FND-001/001A/002/003-code, IAM-001 (unmerged experiment) | Accepted gates / retired paths (truth §12) | Protected historical record |

### Class B — BUILT_AWAITING_PROOF (verify)

| Unit | Missing proof | Route |
|---|---|---|
| DocuSeal self-host signing path as a product dependency | Service commissioning proof remains incomplete even though current FND-003-R1 repairs the trust bootstrap | Verify after trust repair + commissioning |
| Fly.io deployment posture | Pilot deployment expired evidence (`BUILT-STALE`) | Verify on recommission (prereq for any `PRODUCTION-PROVEN`) |

### Class C — DEFECT / HARDENING GAP (repair)

| Unit | Violation of settled intent | Blast radius | Route |
|---|---|---|---|
| **TRACE-FND-003-R1 — runtime role bypasses RLS + unscoped internal sessions** | 43-table FORCE RLS is ineffective under a bypass-capable runtime role; multiple internal session callers require canonical tenant context | HIGH, security | Approved repair spec/ticket package; continue current implementation through T14 and independent Gate 003. Do not restart completed tickets. |
| **DocuSeal completion trusted-tenant bootstrap (T06B)** | Provider authentication alone does not establish canonical tenant identity before tenant-table access | Security / external trust | **Class C active repair.** Implement signed TRACE routing capability + current DocuSeal webhook verification + tenant known before DB. Do not disable the feature as the completion condition. |
| GAP-1/GAP-2: inbound email/fax webhook auth fail-open | Signed-webhook invariant violated | Small/contained auth gap, but external routing ownership remains broader | Repair fail-open behavior within current narrowed inbound work; unresolved trust-routing mechanism remains Class E where genuinely undecided. |
| `matter_id` stored in `cases.intake_record_id`; projection `matter_id` holds `case_id` | Identity separation violated by legacy columns/naming | Medium, data-touching | Bounded identity-normalization slice, expand–migrate–contract; schedule after R1 unless explicitly pulled forward |
| Vestigial `llm_backend`; stale activation wording / docstrings / historical agent drift | Canonical naming/contract wording drift | Trivial | Tiny repair tickets, no ceremony |
| Orchestrator `config.yaml` shows stale phase status | Ecosystem-side record stale | n/a (outside repo) | Note to orchestrator owner; not a TRACE implementation ticket |

### Class D — DEFINED FEATURE (build when scheduled)

| Unit | Settled requirement | Route |
|---|---|---|
| **Client Portal Grant-Bound Tenant Bootstrap (`TRACE-PORTAL-TRUST-001`)** | Shared Platform grant authority → signed portal capability → TRACE verifies tenant before DB → local grant projection validated under RLS | Thin `to-spec` / tickets already authorized for the current R1 sequence; implementation must preserve canonical tenant UUID and DB-backed revocation/permission checks |
| **Unified Matter Readiness + Damages Development + governed TRACE→SETTLE handoff** | Product boundary, ontology direction, source/derived separation, attorney approval, privacy default, and two-sided STL-001 rule are settled in `TRACE-ARCH-ADD-001`, ontology conformance contract, and `TRACE-FINAL-POST-GATE-003-PLAN.md` | **Do not build before Gate 003.** After Gate 003: `TRACE-DMG-000` ontology/existing-model reconciliation → DMG-001..005 → joint STL-001 → STL-002..004. No Wayfinder unless a genuinely new unresolved question appears. |
| Matter Readiness UI geometry | Capability and unified readiness ontology are settled; exact UI geometry remains a spec-time design choice | Design inside DMG-003/004/005; do not create a competing readiness board |

### Class E — UNRESOLVED FEATURE

| Unit | Open question |
|---|---|
| Clerk-org ↔ canonical TrueVow tenant UUID mapping | Mapping mechanism/platform ownership undecided (platform-scope, not TRACE-alone) |
| Broader inbound-document trust-resolution contract for Resend/Twilio/fax | Authentication must fail closed, but the long-term tenant-routing/vouching mechanism across these external inbound paths is not fully settled |
| TRACE → COMMAND contract | Explicitly NOT DEFINED — do not invent |
| ModernBERT long-context evaluation; historical flag concepts as new capabilities | IDEA/TBD — requires explicit product re-approval before routing |

**Superseded classifications:**

- DocuSeal trusted tenant routing is **not Class E**; intended architecture is settled and it is an active Class C repair.
- Client Portal trusted tenant bootstrap is **not Class E**; its grant-bound architecture is settled and it is Class D.
- “Deeper SETTLE integration beyond demand-ready export” is **not Class E** after owner ruling 2026-08-30. The TRACE development/readiness + governed handoff direction is Class D. The exact future event name and payload are intentionally deferred to the two-sided STL-001 reconciliation, which is part of the defined plan rather than evidence that the whole feature is unresolved.

## FND-003-R1 classification block

```text
TRACE-FND-003-R1
Maturity:            C — DEFECT / HARDENING GAP
Why:                 Intended tenant-isolation architecture is settled; runtime
                     role/session/trust paths must comply with it.
Product ambiguity:   NONE for the R1 goal
Architecture ambiguity: NONE for runtime-role + canonical-context repair
Implementation blast radius: HIGH
Entry:               No Wayfinder. Bounded repair spec justified by blast radius +
                     security impact.
Next:                Continue from actual repository state through remaining R1
                     tickets; only independent T14/Gate003 verification can PASS.
```

## Post-Gate-003 defined-feature sequence

```text
Gate 003 PASS
    ↓
TRACE-DMG-000  Ontology + existing-model reconciliation
    ↓
TRACE-DMG-001  Necessary domain/persistence extensions only
    ↓
TRACE-DMG-002  Evidence-development services
    ↓
TRACE-DMG-003  Unified Matter Readiness service
    ↓
TRACE-DMG-004  Governed APIs + operational projections
    ↓
TRACE-DMG-005  Unified Matter Readiness UI
    ↓
TRACE-STL-001  TWO-SIDED TRACE/SETTLE ontology + contract reconciliation
    ↓
TRACE-STL-002  Attorney approval lifecycle
    ↓
TRACE-STL-003  Signed, idempotent delivery/outbox
    ↓
TRACE-STL-004  Privacy, isolation and commissioning proof
```

`trace.settlement_context_ready` remains a **provisional** candidate event name until STL-001 jointly reconciles both repositories, the platform ontology, transition/event registries, privacy classification, versioning, and receiver acceptance semantics.

## Routing rules (binding)

1. No skill invocation precedes its unit's classification here.
2. Reclassification requires new evidence recorded in this ledger and, where substantive, canonical truth/approved-plan writeback.
3. Class A units are never reopened by methodology adoption; Class B earns proof through verification lanes, not rebuilds.
4. `implement` / `code-review` / independent-gate / writeback apply to every class that produces code.
5. Class D does **not** imply immediate authorization: scheduling/gates still control entry. The damages/SETTLE program remains blocked from implementation until independent Gate 003 PASS.
6. For STL-001, neither TRACE nor SETTLE may independently freeze the future cross-product contract. The smallest useful projection must be reconciled and frozen jointly.
