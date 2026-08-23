# TRACE

TRACE is TrueVow's pre-litigation matter development and readiness layer: it takes a captured matter and develops it — representation, conflicts, agreements, activation, treatment records, evidence — until an attorney can judge it demand-ready.

## Language

### Entities

**Matter**:
The canonical platform/product business entity representing the activated legal matter. Identified across service contracts by `matter_id`.
_Avoid_: using "case" when speaking about the platform entity; treating `matter_id` and `case_id` as interchangeable

**TRACE Case**:
TRACE-local operational projection of a Matter used by legacy TRACE tables, routes, and models. Identified by `case_id`.

**Activation**:
The authoritative transition of a Matter to activated, owned by SaaS Admin as canonical Matter authority. When TRACE accepts `matter.activated` it has successfully *projected* an already-activated Matter; acceptance is not the activation transition itself.
_Avoid_: saying TRACE "activates" a Matter

### Operations

**Flag Registry**:
The shipped 15-value set of clinical/administrative flag types (`FLAG_TYPES`) with priorities PRIORITY / ADVISORY / INFORMATIONAL. Canonical v1. Historical PRD/Market/ADR flag taxonomies are superseded — their names are never backlog items unless explicitly re-approved.
_Avoid_: T1-xx/T2-xx identifiers; MEDICATION_ESCALATION-style legacy names

**Matter Readiness Board**:
The decided attorney-facing view of what is complete, waiting, missing or contradictory in a Matter, and whether it is ready for the next pre-litigation milestone. Capability is decided; the historical five-column layout is a superseded design reference, not a binding contract.
_Avoid_: treating the current slim `/readiness` summary as the Board

**Demand-Ready**:
The final stage at which every PRIORITY flag is attorney-annotated and the Matter may be exported for settlement.
_Avoid_: "done", "complete"

### Product

**TRACE**:
The pre-litigation matter development & readiness product. Full canonical descriptor: "TRACE — Pre-Litigation Matter Development & Readiness".
_Avoid_: Treatment Record Acquisition and Chronology Engine (retired), Client Engagement and Case Readiness (superseded intermediate descriptor)

**TrueVow pipeline**:
Four products, not four sequential stages: INTAKE Captures. TRACE Develops. SETTLE Resolves. COMMAND Measures. The case-processing path is principally INTAKE → TRACE → SETTLE; COMMAND measures across the ecosystem.
_Avoid_: describing COMMAND as the fourth processing stage after SETTLE
