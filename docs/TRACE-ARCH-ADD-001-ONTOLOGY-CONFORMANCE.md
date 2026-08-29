# TRACE-ARCH-ADD-001 — Ontology Conformance Contract

| | |
|---|---|
| **Status** | BINDING COMPANION TO TRACE-ARCH-ADD-001 |
| **Date** | 2026-08-30 |
| **Authority** | Owner ruling 2026-08-30 + TrueVow Operating Ontology v1.0 / Developer Guide v2 |
| **Purpose** | Ensure TRACE damages-development and SETTLE handoff extend the platform ontology rather than creating a parallel truth model |

---

## 1. Binding ontology rule

The TrueVow Operating Ontology remains authoritative.

**Business reality is canonical. Products implement and project that reality.** UI statuses, jobs, emails, dashboards, workflow cards, integrations, caches, and convenience read models may project canonical state but may not redefine it.

This applies to INTAKE, TRACE, SETTLE, COMMAND, shared services, integrations, analytics, and AI-derived outputs.

For `TRACE-ARCH-ADD-001`, no new table, API, UI panel, event, status, or service may become an independent ontology universe.

---

## 2. Canonical product ownership

Product ownership remains:

```text
INTAKE
  owns capture / candidate intake

TRACE
  owns source-linked, attorney-reviewable pre-litigation development records

SETTLE
  owns settlement-context and resolution-support outputs

COMMAND
  owns measurement / operational intelligence projections
```

The new TRACE damages-development capability is therefore a TRACE-owned **development record and readiness layer**, not a settlement-valuation layer.

The SETTLE handoff transfers a governed packet across a contract boundary. It does not transfer ontology ownership of the underlying TRACE records.

---

## 3. TRACE ontology chain must remain intact

The canonical TRACE evidence-development chain remains:

```text
Source Document / Evidence
        ↓
Source Citation
        ↓
Raw Fact
        ↓
Normalized Fact
        ↓
Fact Conflict / Contradiction
        ↓
Timeline Event
        ↓
Chronology Version
        ↓
Issue / Risk Flag / Treatment Gap
        ↓
Readiness Assessment
        ↓
Attorney-Reviewable Handoff / Demand-Preparation Artifact
```

`TRACE-ARCH-ADD-001` extends the lower half of this chain; it does not replace it.

The new concepts map as follows:

| Addendum concept | Ontology role | Rule |
|---|---|---|
| Damages Item | Source-linked operational development record derived from evidence/facts | Must retain provenance; never treated as valuation |
| Lien / Recovery Input | Source-linked operational development record | Status/amount provenance required; legal/net-recovery meaning remains attorney/SETTLE responsibility |
| Treatment Gap | Existing TRACE issue/risk-domain concept | Reuse canonical treatment-gap semantics; do not create a competing gap ontology |
| Damages Readiness Snapshot | Derived readiness assessment / projection | Rebuildable from authoritative records; records blockers/limitations and review semantics |
| SETTLE Handoff Packet | Versioned cross-product contract artifact | Snapshot/export of approved TRACE state; does not become the canonical source of underlying facts |
| “Needs You / Waiting on Others / At Risk” items | Operational projections | Derived from canonical Matter/TRACE state; not standalone business truth |

---

## 4. Source data vs derived data must remain separate

The following must never be collapsed into one field/state:

```text
source evidence
≠ raw fact
≠ normalized fact
≠ contradiction/conflict
≠ risk/treatment-gap signal
≠ readiness assessment
≠ attorney approval
≠ SETTLE handoff state
≠ settlement valuation
```

A damages amount extracted from a bill is not automatically an attorney-verified damages amount.

A treatment gap is not automatically a negative case-value conclusion.

A lien/recovery claim is not automatically a final net-recovery deduction.

A readiness state is not a quality score or settlement prediction.

---

## 5. Provenance contract for every derived output

Every derived damages/readiness output must carry or be reconstructable to:

- source document / evidence reference;
- source citation or source location where applicable;
- derivation/extraction method;
- confidence or review requirement;
- created/derived timestamp;
- staleness semantics where relevant;
- review state;
- reviewing authority where applicable;
- contradiction/limitation state where applicable.

No AI/NLP/extraction output becomes authoritative merely because it was persisted.

Attorney review semantics must remain explicit.

---

## 6. Commands, events, and projections

### Commands

Commands are **requests to change canonical state**. They are not evidence that the change happened.

Examples for future implementation may include:

```text
CreateDamagesItem
ReviewDamagesItem
FlagTreatmentGap
ResolveTreatmentGap
GenerateDamagesReadinessSnapshot
CreateSettleHandoffPacket
ApproveSettleHandoffPacket
SendSettleHandoffPacket
RejectSettleHandoffPacket
```

Exact command names are fixed during `to-spec` / contract registration, not improvised in route handlers.

### Events

Events represent **authoritative facts that occurred** after command/transition validation.

Candidate event names from the addendum are provisional until registered through the ontology/contract process.

Examples:

```text
trace.damages_item.created
trace.damages_item.reviewed
trace.treatment_gap.flagged
trace.treatment_gap.resolved
trace.damages_readiness.snapshot_created
trace.settle_handoff.packet_created
trace.settle_handoff.approved
trace.settle_handoff.sent
trace.settle_handoff.rejected
```

Every emitted event must use the canonical EventEnvelope and must not invent a new root schema.

### Projections

Readiness boards, “Needs You”, “Waiting on Others”, “At Risk”, counts, badges, and dashboard states are rebuildable projections.

They may never become alternate canonical state machines.

---

## 7. Transition contract rule

Every state transition introduced by this addendum must be registered through the canonical transition/state-machine framework.

Each transition must explicitly define:

```text
transition_id
command
aggregate / entity
allowed prior state(s)
target state
authority class
required evidence
guards
emitted event
failure mode
```

Default failure mode is fail-closed.

No route handler, UI button, background job, or integration callback may directly mutate a lifecycle state without the governing transition contract.

---

## 8. Authority contract

Authority remains explicit and separate from authentication.

Examples:

- authenticated staff identity does not itself imply attorney approval authority;
- provider/webhook authenticity does not itself establish tenant or professional authority;
- AI/extraction services have no professional approval authority;
- SETTLE cannot retroactively mutate TRACE source facts by consuming a handoff packet.

Future damages/handoff commands must register the required authority in the existing authority framework (`AuthorityGate` / canonical authority registry).

Attorney approval for SETTLE handoff is a first-class authority event, not a boolean convenience field silently flipped by UI code.

---

## 9. Evidence contract

Transitions with legal/professional significance require explicit evidence references.

Examples:

```text
Damages item VERIFIED
  requires source-backed evidence + authorized review semantics

Treatment gap EXPLAINED
  requires documented source/reason and review authority

Readiness READY_FOR_SETTLE_CONTEXT
  requires the registered readiness guards/evidence set

Handoff APPROVED_FOR_SETTLE
  requires readiness snapshot + attorney authority + de-identification validation

Handoff SENT_TO_SETTLE
  requires approved packet + valid signed delivery contract + idempotency evidence
```

Missing evidence fails closed or produces an explicitly limited/review-required state; it may not be silently inferred.

---

## 10. Aggregate / entity ownership

The canonical Matter remains the cross-product business entity.

TRACE Case remains the TRACE-local operational projection of an activated Matter.

Future damages-development records attach to the TRACE Case / canonical Matter relationship; they do not mint a competing “damages matter” aggregate.

During implementation, the spec must explicitly identify the aggregate root for each new record and avoid duplicating existing entities where extension is sufficient.

Known `matter_id` / `case_id` debt must not be papered over by treating the identifiers as interchangeable.

---

## 11. SETTLE handoff ontology contract

The handoff packet is a **versioned contract artifact**, not an ownership transfer.

```text
TRACE authoritative records
        ↓
TRACE derived readiness snapshot
        ↓
attorney approval transition
        ↓
versioned handoff packet projection
        ↓
signed/versioned API or event contract
        ↓
SETTLE consumes
```

SETTLE may create its own settlement-context projections and authoritative SETTLE-domain records from the accepted contract.

SETTLE must not directly write TRACE persistence.
TRACE must not directly write SETTLE persistence.

Cross-product communication uses versioned commands/events/APIs only.

---

## 12. Readiness ontology rule

The existing Matter Readiness capability and the new Damages Readiness capability must become one coherent readiness ontology, not competing scoring systems.

Preferred conceptual structure:

```text
Matter Readiness Assessment
├── Representation / engagement readiness
├── Treatment readiness
├── Records & bills readiness
├── Evidence readiness
├── Damages-development readiness
├── Lien / recovery-input readiness
├── Treatment-gap / contradiction review
└── SETTLE handoff readiness
```

A readiness assessment is derived and point-in-time.
It must identify blockers, limitations, provenance, and review semantics.
It is never a case-value score.

---

## 13. AI / deterministic boundary

AI/NLP may assist extraction, normalization, classification, or signal generation only within the existing non-authoritative framework.

AI must not:

- approve damages;
- resolve contradictions as professional fact;
- declare legal causation;
- approve a SETTLE handoff;
- calculate settlement value inside TRACE;
- create authoritative state transitions without deterministic guards and required authority.

All operational workflows must remain functional without AI authority.

---

## 14. Implementation gate for TRACE-DMG / TRACE-STL work

Before `TRACE-DMG-001` enters BUILDING, `/to-spec` must include an **Ontology Mapping Appendix** containing, for every proposed new object:

```text
canonical entity / aggregate
source vs derived classification
system/product owner
state machine (if any)
commands
transitions
required authority
required evidence
guards
emitted events
provenance requirements
staleness/review semantics
projection/read-model outputs
cross-product contract impact
```

A ticket may not implement a new state/status/event merely because a proposed database enum or UI design contains it.

If the ontology mapping cannot classify a proposed concept cleanly, implementation stops and the architecture is reconciled before code is written.

---

## 15. Current FND-003 compatibility rule

No current FND-003-R1 ticket is reopened because of this ontology companion.

However, current work must preserve the ontology-supporting infrastructure that later damages/handoff work will reuse:

- canonical tenant UUID and tenant context;
- `internal_tenant_session`;
- explicit tenant predicates + RLS;
- EventEnvelope;
- AuthorityGate / authority registry;
- TransitionContract / StateMachine;
- evidence/source provenance;
- append-only event/audit semantics;
- signed/versioned cross-product contracts;
- fail-closed trust bootstrap and idempotency.

---

## 16. Final ontology rule

> **Do not create a parallel damages ontology. Extend the canonical Matter → evidence → fact → conflict/signal → readiness → attorney-approved handoff chain.**

Every future TRACE damages or SETTLE-handoff implementation must prove where it fits in that chain before it is allowed to persist state or emit events.