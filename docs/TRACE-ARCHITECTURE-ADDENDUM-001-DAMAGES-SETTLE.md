# TRACE-ARCH-ADD-001 — Damages Development & SETTLE Handoff

| | |
|---|---|
| **Status** | DECIDED-BUT-UNBUILT |
| **Date** | 2026-08-30 |
| **Owner authority** | Owner ruling 2026-08-30 |
| **Applies to** | TRACE — Pre-Litigation Matter Development & Readiness |
| **Implementation timing** | After TRACE-FND-003-R1 / Gate 003, except bounded compatibility adjustments explicitly listed in §10 |
| **Boundary** | TRACE develops and prepares structured Matter inputs. SETTLE values/resolves. |

---

## 1. Decision

TRACE will gain a governed damages-development and SETTLE-handoff capability.

The capability exists to make TRACE the clean, auditable pre-litigation development layer that prepares a Matter for later SETTLE review.

TRACE owns:

- treatment-development state;
- records and bills completeness;
- documented damages inputs;
- lien / reimbursement / recovery-claim inputs;
- wage-loss, property-loss, out-of-pocket, and client-impact support;
- treatment gaps and evidence gaps;
- liability / comparative-fault signals requiring attorney review;
- coverage / limits status where available;
- readiness blockers and limitations;
- source-linked evidence;
- attorney review and approval;
- creation of a de-identified, schema-versioned SETTLE handoff packet.

TRACE does **not** own:

- settlement valuation;
- settlement ranges;
- demand amount recommendations;
- pain-and-suffering multipliers;
- negotiation strategy;
- accept/reject recommendations;
- public benchmark comparisons;
- contribution of settlement outcomes to shared intelligence.

If implementation attempts to calculate or recommend settlement value inside TRACE, it violates this addendum.

---

## 2. Product boundary

Canonical ecosystem language remains:

> **INTAKE Captures. TRACE Develops. SETTLE Resolves. COMMAND Measures.**

The principal processing path remains `INTAKE → TRACE → SETTLE`.

This addendum refines the TRACE→SETTLE seam:

```text
TRACE source-linked Matter development
        ↓
Damages Development Record
        ↓
Damages Readiness Snapshot
        ↓
Attorney review / approval
        ↓
Schema-versioned SETTLE Handoff Packet
        ↓
SETTLE settlement-context / resolution workflow
```

The handoff packet is an input-preparation artifact. It is not a valuation result.

---

## 3. New domain concept — Damages Development Record

A **Damages Development Record** is a structured, source-linked view of the Matter facts and proof needed before settlement context is meaningful.

It may include:

- treatment status;
- medical records completeness;
- billing completeness;
- documented medical expenses;
- wage-loss support;
- property-loss support;
- out-of-pocket support;
- future-care signal requiring attorney review;
- client-impact support;
- lien / reimbursement / subrogation inputs;
- treatment gaps;
- evidence gaps;
- liability / comparative-fault signals;
- coverage / limits status;
- readiness blockers and limitations.

Permitted TRACE statements include:

- “medical bills are missing”;
- “lien status is unknown”;
- “treatment gap exists”;
- “wage-loss support is not documented”;
- “provider records are incomplete”;
- “liability signal requires attorney review.”

Prohibited TRACE statements include:

- “case is worth X”;
- “settlement should be Y”;
- “accept/reject this offer”;
- “apply a pain-and-suffering multiplier.”

---

## 4. Target persistence model

Exact table names may be normalized during `to-spec`, but the following bounded contexts are decided.

### 4.1 Damages items

Target table: `trace_damages_items` or equivalent.

Required concepts:

- `firm_id`, `case_id`;
- category: medical expense, wage loss, property loss, out-of-pocket, future-care signal, client impact, other economic support;
- amount where supported, plus status and currency;
- source document/page references;
- confidence / attorney-review-required status;
- created/reviewed attribution.

Rules:

- tenant-owned and RLS-protected;
- every query carries explicit firm/tenant predicate in addition to RLS;
- no raw client identifiers;
- source references point to governed internal documents.

### 4.2 Lien / recovery inputs

Target table: `trace_lien_recovery_inputs` or equivalent.

Tracks health-insurance, Medicare, Medicaid, provider, workers-comp, ERISA, other subrogation, or unknown recovery claims.

TRACE tracks the input and documentation status. TRACE does not calculate final client net recovery.

### 4.3 Treatment gaps

Target table: `trace_treatment_gaps` or equivalent.

Tracks treatment delay/gap, missing provider, missing records/bills, unexplained discharge, future-care uncertainty, and other gaps.

TRACE may flag and document the gap. TRACE may not infer medical causation or case-value effect.

### 4.4 Damages readiness snapshots

Target table: `trace_damages_readiness_snapshots` or equivalent.

Point-in-time readiness states:

- `READY_FOR_SETTLE_CONTEXT`;
- `READY_WITH_LIMITATIONS`;
- `NOT_READY`;
- `ATTORNEY_REVIEW_REQUIRED`.

The record stores blockers and limitations explicitly.

It is a readiness snapshot, **not a score, case-quality rank, value estimate, or settlement prediction**.

### 4.5 SETTLE handoff packets

Target table: `trace_settle_handoff_packets` or equivalent.

Lifecycle:

```text
DRAFT
→ ATTORNEY_REVIEW_REQUIRED
→ APPROVED_FOR_SETTLE
→ SENT_TO_SETTLE
```

`REJECTED` is allowed as a terminal/rework state.

Required concepts:

- `firm_id`, `case_id`;
- readiness snapshot reference;
- packet schema/version;
- payload;
- excluded fields / limitation notes;
- approval attribution;
- sent timestamp.

Outgoing packet must exclude raw client identifiers unless a later separately governed PHI-bound contract explicitly authorizes otherwise.

---

## 5. Target services

### 5.1 `DamagesReadinessService`

Responsibilities:

- aggregate damages items;
- aggregate records/bills completeness;
- aggregate lien/recovery inputs;
- aggregate treatment/evidence gaps;
- generate a point-in-time readiness snapshot;
- return explicit blockers and limitations.

It must never estimate case value, settlement, demand amount, or negotiation strategy.

Target seam:

```python
async def generate_damages_readiness_snapshot(
    case_id: UUID,
    firm_id: UUID,
    actor_id: UUID,
) -> DamagesReadinessSnapshot:
    ...
```

### 5.2 `NetRecoveryInputsService`

Collects ingredients only:

- fee-model presence if configured;
- case-cost status;
- lien/recovery inputs;
- outstanding bills;
- missing net-recovery inputs.

No final net-recovery calculation is authorized by this addendum.

### 5.3 `SettleHandoffService`

Responsibilities:

- build the packet from an accepted readiness snapshot;
- remove prohibited identifiers;
- attach governed source references;
- require attorney approval;
- emit/send to SETTLE through a signed, versioned cross-product contract;
- audit material actions.

Hard gates:

- active Matter / valid TRACE Case projection;
- firm/tenant match;
- readiness snapshot exists;
- attorney approval before send;
- prohibited-identifier scan passes;
- outgoing payload schema version is present.

No direct cross-product database writes are permitted.

---

## 6. API and UI target

### 6.1 API capability families

Planned API families:

- damages readiness and snapshot generation;
- damages item CRUD/review;
- lien/recovery input CRUD/review;
- treatment-gap CRUD/review;
- SETTLE handoff create/review/approve/send/read.

Exact URL geometry is a spec-time choice. Every endpoint requires authenticated authority, canonical tenant context, case ownership, and role/capability enforcement.

### 6.2 Matter UI — “Damages Readiness”

Planned sections:

1. Medical Expenses
2. Records & Bills
3. Liens / Recovery Inputs
4. Wage Loss
5. Property / Out-of-Pocket
6. Treatment Gaps
7. Evidence Gaps
8. Client Impact Support
9. SETTLE Handoff Readiness

Each section exposes status, source evidence, missing items, responsible actor/party, and attorney-review requirements.

The UI must not display settlement ranges, demand recommendations, multipliers, or negotiation guidance.

### 6.3 SETTLE Handoff Readiness panel

States:

- READY FOR SETTLE CONTEXT
- READY WITH LIMITATIONS
- NOT READY
- ATTORNEY REVIEW REQUIRED

Actions:

- Generate Readiness Snapshot
- Create SETTLE Handoff Packet
- Approve for SETTLE
- Send to SETTLE

`Send to SETTLE` is disabled until attorney approval.

Required boundary copy:

> TRACE prepares structured Matter inputs for SETTLE. TRACE does not value the case, recommend a demand, or recommend settlement.

---

## 7. Operational next-action integration

The existing operational readiness model may derive, rather than manually invent, items such as:

**Needs You**
- review unresolved treatment gap;
- confirm lien/recovery input status;
- review missing wage-loss support;
- approve SETTLE handoff packet.

**Waiting on Others**
- itemized bill pending;
- provider records pending;
- client wage documentation pending;
- lien response pending.

**At Risk**
- readiness blocked by missing records;
- lien status unknown before settlement review;
- treatment gap unresolved;
- evidence source incomplete.

These remain deterministic projections of Matter state, not generic free-form tasks.

---

## 8. Events and audit

Target business events:

- `trace.damages_item.created`
- `trace.damages_item.updated`
- `trace.treatment_gap.flagged`
- `trace.lien_input.updated`
- `trace.damages_readiness.snapshot_created`
- `trace.settle_handoff.packet_created`
- `trace.settle_handoff.approved`
- `trace.settle_handoff.sent`
- `trace.settle_handoff.rejected`

Events follow the canonical EventEnvelope and contain tenant/case/resource/actor references without raw client PII.

Material actions require durable audit evidence, including before/after state where applicable and reason/comment for overrides.

---

## 9. PHI / de-identification boundary

Reuse TRACE’s existing PHI separation and opaque-identity posture.

TRACE’s internal Matter workflow may use source-linked PHI only under existing TRACE PHI controls.

The default outgoing SETTLE handoff packet must not contain:

- client name;
- phone;
- email;
- street address;
- date of birth;
- claim number;
- medical record number;
- raw medical identifiers/notes not explicitly authorized by a later PHI-bound contract.

Use opaque case/matter references and governed source references.

If SETTLE later requires PHI-bound access, that is a separate cross-product security/privacy contract and is not implied here.

---

## 10. Incorporation timing — now vs after Gate 003

### 10.1 Adjust now — architecture and seam compatibility only

While FND-003-R1 is still active:

1. Record this addendum in canonical governance and maturity routing.
2. Do **not** add damages migrations, models, endpoints, UI, or SETTLE feature code to the FND-003-R1 branch.
3. Preserve the new canonical tenant-context seam (`internal_tenant_session`) as mandatory for all future damages tables/services.
4. Preserve explicit tenant predicates in addition to RLS for future damages queries.
5. Preserve `EventEnvelope` as the event format for future damages/handoff events.
6. Preserve append-only audit/event semantics needed by readiness snapshots and handoff approvals.
7. T06B and Portal Trust work may not create a new identity pattern; future SETTLE handoff must reuse canonical tenant UUID and signed/versioned cross-service contracts.
8. T10’s zero-bypass guard must remain extensible so future damages modules cannot introduce raw operational session opens.
9. T11/T12/T13 acceptance evidence becomes the security foundation required before this addendum can enter BUILDING.

No current FND-003 ticket is reopened solely because of this addendum.

### 10.2 Build after Gate 003

After FND-003-R1 receives independent Gate 003 PASS and truth writeback:

```text
TRACE-DMG-001  Domain/data contract + migration
TRACE-DMG-002  Damages item + treatment-gap + lien input services
TRACE-DMG-003  Damages readiness snapshot service
TRACE-DMG-004  API + deterministic next-action projection
TRACE-DMG-005  Matter UI / Damages Readiness tab
TRACE-STL-001  SETTLE handoff packet schema + de-identification
TRACE-STL-002  Attorney approval + audit/event lifecycle
TRACE-STL-003  Signed TRACE→SETTLE delivery contract + mocked receiver
TRACE-STL-004  PHI/PII leakage adversarial tests + feature-flag commissioning
```

The exact ticket decomposition may change during `to-spec`/`to-tickets`, but these bounded capabilities are the approved implementation sequence.

---

## 11. Maturity / lifecycle routing

This addendum is **Class D — DEFINED FEATURE**.

Product boundary: settled.
Architecture direction: settled.
Implementation: absent.

Correct route after Gate 003:

```text
Canonical Truth + this addendum
        ↓
thin /to-spec
        ↓
/to-tickets
        ↓
implement
        ↓
/code-review
        ↓
independent TrueVow verification
        ↓
PASS / merge / freeze
        ↓
truth + maturity writeback
```

No Wayfinder is required unless implementation uncovers a genuinely unresolved cross-product contract that this addendum does not settle.

---

## 12. Feature flags

Initial commissioning flags:

```text
TRACE_DAMAGES_READINESS_ENABLED=false
TRACE_SETTLE_HANDOFF_ENABLED=false
```

Production defaults remain false until backend tests, tenant-isolation tests, PHI/PII leakage tests, portal QA, and SETTLE contract tests pass.

---

## 13. Minimum acceptance contract

The addendum is not implementation-complete until all are proven:

1. TRACE generates a source-linked damages readiness snapshot.
2. Blockers and limitation notes are explicit and deterministic.
3. Lien/recovery inputs and treatment gaps are tracked.
4. TRACE can create a schema-versioned SETTLE handoff packet.
5. Attorney approval is required before send.
6. Outgoing packets contain no raw client identifiers under the default contract.
7. TRACE UI communicates readiness, never valuation.
8. No settlement ranges or demand recommendations exist anywhere in TRACE output/UI.
9. Material actions are audited.
10. Tenant-isolation adversarial tests pass.
11. PHI/PII leakage tests pass.
12. A mocked/contract-tested SETTLE receiver accepts the packet.
13. The full workflow can be disabled by feature flags.

Non-negotiable leakage test: serialized outgoing handoff packets are searched for seeded client name, DOB, phone, email, address, claim number, and MRN; expected matches = zero.

---

## 14. Non-goals

This addendum does not authorize:

- settlement valuation;
- settlement range display;
- demand amount recommendation;
- pain-and-suffering multiplier;
- negotiation recommendation;
- insurer “lowball” scoring;
- Settlement Commons contribution;
- public benchmark comparisons;
- client-facing settlement advice;
- direct TRACE writes into SETTLE persistence.

---

## 15. Final architecture rule

> **Do not make TRACE into SETTLE. Build the damages-development and readiness architecture that makes SETTLE possible.**

TRACE owns facts, documents, liens/recovery inputs, treatment/evidence gaps, readiness blockers, source links, attorney review, and handoff preparation.

SETTLE owns settlement context, comparable signals, valuation/resolution support, and settlement-facing economics.