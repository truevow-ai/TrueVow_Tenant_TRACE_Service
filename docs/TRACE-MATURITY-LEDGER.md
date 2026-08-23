# TRACE Completion / Maturity Ledger

| | |
|---|---|
| **Version** | 1.0 |
| **Date** | 2026-08-23 |
| **Authority** | Classification derived from `docs/TRACE-CANONICAL-TRUTH.md` v1.2 (statuses carry evidence), accepted gate history, and the session audit. This ledger routes work; the truth doc remains the substantive authority. |
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
| Evidence layer (EvidenceFact/SourceLocation/ContradictionPair/MissingEvidenceSignal/FactVersion) | Wired into chronology/flags/fact-review; covered | Protect |
| Shared foundation (AuthorityGate/ConsentLedger/PolicyRegistry/EventStore/StateMachine) | Implemented ~300–400 lines each; covered | Protect |
| Webhook contract WebhookSignature v1.0 + 17 golden fixtures; EventEnvelope 1.0.1 | Golden fixture tests; RC-v3 pilot PASS | Protect |
| Entitlement capability gates ($35/$179/$299 plan codes) | `entitlements.py`; verified this session | Protect |
| Demand-ready export (PDF/JSON, 403 gate, disclaimer) | Covered; pilot-era verified | Protect |
| Grandfathered history: Phases 1A–1E, Phase 2A, FND-001/001A/002/003-code, IAM-001 (unmerged experiment) | Accepted gates / retired paths (truth §12) | Protected historical record |

### Class B — BUILT_AWAITING_PROOF (verify)

| Unit | Missing proof | Route |
|---|---|---|
| FND-002 re-key commissioning | Independent **Gate-002 PASS** awaited since 2026-08-20 (truth §10 #7) | Verify (independent gate) |
| DocuSeal self-host signing path | Service uncommissioned (no deployment/subscription) | Verify-after-commissioning; blocked by budget decision |
| Fly.io deployment posture | Pilot deployment expired evidence (`BUILT-STALE`) | Verify on recommission (prereq for any PRODUCTION-PROVEN) |

### Class C — DEFECT / HARDENING GAP (repair)

| Unit | Violation of settled intent | Blast radius | Route |
|---|---|---|---|
| **TRACE-FND-003-R1 — runtime role bypasses RLS + unscoped internal sessions** | 43-table FORCE RLS is inert under `rolbypassrls=true`; ~57 direct session opens lack canonical context | HIGH, security | **C — wide/security-sensitive:** approved spec (`53d119b`) + published 14-ticket package (`dbe54e1`) → **IMPLEMENT next** (frontier 01/03/04). Full classification block below. |
| GAP-1/GAP-2: inbound email/fax webhook auth fail-open | Signed-webhook invariant violated (`inbound.py:56`, `:220`) | Small, contained | Repair tickets direct from truth §8 wording — **no to-spec needed**; sequence after R1 lands |
| `matter_id` stored in `cases.intake_record_id`; projection `matter_id` holds `case_id` | Identity separation (truth §4) violated by legacy columns | Medium, data-touching | Bounded identity-normalization slice, expand–migrate–contract; schedule after R1 |
| Vestigial `llm_backend` settings field; activation-handler docstrings say "from RETAINER"; AGENTS.md-era drift remnants | Canonical naming/contract wording (truth §4/§9) | Trivial | Tiny repair tickets, no ceremony |
| Orchestrator `config.yaml` shows "Phase-1D-complete" | Ecosystem-side record stale | n/a (outside repo) | Note to CTO orchestrator owner; not a TRACE ticket |

### Class D — DEFINED FEATURE (build when scheduled)

| Unit | Settled requirement | Route |
|---|---|---|
| Matter Readiness Board (capability decided; UI geometry free) | Truth §10 #3 goal statement exists; exact UX unsettled by design | Thin `to-spec` at scheduling time → `to-tickets` |
| Successor inbound-document integration-security slice (closes GAP-1/2 + blocked callbacks) | Fail-closed invariant settled; **resolution contract with Resend/Twilio/SaaS Admin is not** | See Class E below — boundary case routed to E because the trust-resolution mechanism is genuinely undecided |

### Class E — UNRESOLVED FEATURE (no skill until decided)

| Unit | Open question |
|---|---|
| Clerk-org ↔ canonical TrueVow tenant UUID mapping | Mapping mechanism/platform ownership undecided (platform-scope, not TRACE-alone) |
| Inbound-document trust-resolution contract | Who vouches tenant identity for uncommissioned callbacks (SaaS Admin relay? provider envelopes?) |
| Deeper SETTLE integration beyond demand-ready export | Contract undefined |
| TRACE → COMMAND contract | Explicitly NOT DEFINED — do not invent |
| ModernBERT long-context evaluation; historical flag concepts as new capabilities | IDEA/TBD — requires explicit product re-approval before any routing |

## FND-003-R1 classification block

```text
TRACE-FND-003-R1
Maturity:            C — DEFECT / HARDENING GAP
Why:                 Intended tenant-isolation architecture settled; runtime role
                     bypasses RLS and multiple session callers carry no context.
Product ambiguity:   NONE
Architecture ambiguity: NONE
Implementation blast radius: HIGH (~57 session sites)
Entry:               No Wayfinder. Bounded repair spec justified by blast radius +
                     security impact (spec APPROVED @ 53d119b; 14 tickets @ dbe54e1).
Next:                IMPLEMENT — frontier tickets 01, 03, 04 after implement authorization.
```

## Routing rules (binding)

1. No skill invocation precedes its unit's classification here.
2. Reclassification requires new evidence recorded in this ledger (and, where substantive, a truth-doc revision).
3. Class A units are never reopened by methodology adoption; Class B earns proof through verification lanes, not rebuilds.
4. `implement`/`code-review`/independent-gate/writeback apply to every class that produces code — including bare Class-C repairs.
