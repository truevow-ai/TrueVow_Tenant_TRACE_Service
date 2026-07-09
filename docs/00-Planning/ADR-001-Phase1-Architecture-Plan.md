# ADR-001 — TRACE Phase 1 Architecture Plan

**Status:** Final — Ready for Phase 1A  
**Date:** July 2026  
**Supersedes:** ADR-000 (individual deviations) — this document is the consolidated architecture  
**Prerequisite reading:** TRACE-PRD.md §5.5.3 (Extended Flag Registry), TRACE-Technical-Implementation-Spec.md §2 (Technology Stack)

---

## 1. End-to-End Data Flow (PHI Boundaries Annotated)

```
                            ┌─── AIR-GAP BOUNDARY ───────────────────────────────┐
                            │                                                    │
                            │  ┌─────────────┐     ┌──────────────────────────┐  │
  INTAKE outbox ────────────►│  │ Case Init   │────►│ Supabase PostgreSQL      │  │
  (case.created event)       │  │ (FastAPI)   │     │ (operational DB + PHI)   │  │
                            │  └──────┬──────┘     └──────────────────────────┘  │
                            │         │                                          │
                            │         ▼                                          │
                            │  ┌─────────────┐                                   │
                            │  │ Provider    │  OpenMed NER (local)              │
                            │  │ Extraction  │──── npi_registry.cms.hhs.gov ────►│──► CMS NPI API
                            │  └──────┬──────┘                                   │    (gov HTTPS, no PHI)
                            │         │                                          │
                            │         ▼                                          │
                            │  ┌─────────────────┐                               │
                            │  │ Attorney Portal  │  Clerk Auth (platform)       │
                            │  │ (React + PDF.js) │──── Clerk API ──────────────►│──► Clerk (auth only)
                            │  └────────┬────────┘                               │
                            │           │                                        │
                            │           │ Attorney confirms provider list        │
                            │           ▼                                        │
                            │  ┌─────────────────┐                               │
                            │  │ Fax Transmission │  Fax.Plus API ──────────────►│──► Fax.Plus (BAA)
                            │  │ (HIPAA cover)    │     (PHI in transit)          │    Cloud fax
                            │  └────────┬────────┘                               │
                            │           │                                        │
                            │           │ Inbound fax webhook                    │
                            │           ▼                                        │
                            │  ┌─────────────────┐                               │
                            │  │ OCR Pipeline     │  deepdoctection + DocTr     │
                            │  │ (Tier 1: local)  │  (zero network calls)        │
                            │  └────────┬────────┘                               │
                            │           │                                        │
                            │           │ Raw OCR text                           │
                            │           ▼                                        │
                            │  ┌─────────────────┐                               │
                            │  │ PHI De-ID        │  OpenMed Nemotron           │
                            │  │ (text-level)     │  Privacy Filter (local)      │
                            │  └────────┬────────┘                               │
                            │           │                                        │
                            │           │ Redacted text + phi_map               │
                            │           ▼                                        │
                            │  ┌─────────────────┐     ┌─────────────────────┐   │
                            │  │ Clinical NER     │     │ Supabase Storage     │   │
                            │  │ OpenMed (local)  │     │ (private bucket,     │   │
                            │  └────────┬────────┘     │  15-min signed URLs) │   │
                            │           │               └─────────────────────┘   │
                            │           │ Chronology entries (de-identified)      │
                            │           ▼                                        │
                            │  ┌─────────────────┐                               │
                            │  │ Flag Detection   │                               │
                            │  │ Tier 1: string   │                               │
                            │  │ + date math      │                               │
                            │  │ Tier 2: OpenMed  │                               │
                            │  │ cross-record     │                               │
                            │  └────────┬────────┘                               │
                            │           │                                        │
                            │           ▼                                        │
                            │  ┌─────────────────┐                               │
                            │  │ Attorney QA      │                               │
                            │  │ Portal (React)   │                               │
                            │  │ Split-panel UI   │                               │
                            │  └────────┬────────┘                               │
                            │           │                                        │
                            │           │ Demand-ready approval                 │
                            │           ▼                                        │
                            │  ┌─────────────────┐                               │
                            │  │ Export (PDF/JSON)│                               │
                            │  └─────────────────┘                               │
                            │                                                    │
                            └────────────────────────────────────────────────────┘

  ┌─── CLOUD SERVICES (BAA-covered, dev/staging only or specific callouts) ──┐
  │                                                                          │
  │  LlamaParse ◄─────────── Tier 2 OCR escalation (handwritten pages      │
  │  (BAA required)              only — individual flagged pages, not full    │
  │                              documents)                                   │
  │                                                                          │
  │  DeepSeek V4 Pro ◄───────┬── Billing reconciliation LLM (production)     │
  │  (air-gapped, zero       │── LLMService.backend = "deepseek"             │
  │   network calls)         │                                               │
  │                          │                                               │
  │  Azure OpenAI GPT-4o-mini◄── Billing reconciliation LLM (dev/staging)    │
  │  Anthropic Claude        │── LLMService.backend = selected via           │
  │  (BAA required)          │   LLM_SERVICE_PROVIDER env var                │
  │                                                                          │
  └──────────────────────────────────────────────────────────────────────────┘
```

**PHI boundary rules:**
- All clinical NLP, flag detection, and chronology assembly operate on **de-identified text only** (OpenMed de-ID runs first)
- PHI leaves the air-gap only through: Fax.Plus (fax transmission, BAA-covered), LlamaParse (handwritten page escalation, BAA-covered, individual pages only, and only if Phase 1C handwriting spike triggers escalation per §19), and Clerk (authentication tokens only — no PHI)
- `phi_map` (the token→real value mapping from OpenMed de-identification) is encrypted at rest with pgcrypto — never logged, never in URLs, never in notification content

---

## 2. Service Abstraction Layer

TRACE uses a plug-and-play abstraction pattern for all external service dependencies. Each abstraction has a single env var that selects the backend at deploy time.

```
┌─────────────────────────────────────────────────────────────────┐
│                    TRACE APPLICATION LAYER                      │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Case API │  │ Provider │  │Chronology│  │ Attorney QA   │  │
│  │ (FastAPI)│  │ CRUD API │  │  Engine  │  │ Portal (React)│  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬───────┘  │
│       │              │              │                │          │
│       └──────────────┴──────────────┴────────────────┘          │
│                              │                                   │
│              ┌───────────────┴───────────────┐                  │
│              │     SERVICE ABSTRACTIONS       │                  │
│              │  (each selects backend via     │                  │
│              │   environment variable)        │                  │
│              └───────────────┬───────────────┘                  │
│                              │                                   │
│  ┌───────────────────────────┼───────────────────────────┐      │
│  │                           │                           │      │
│  ▼                           ▼                           ▼      │
│ LLMService              OCRService                 Storage     │
│ LLM_SERVICE_PROVIDER    OCR_CLOUD_BACKEND          (Supabase)  │
│  ├─ deepseek (prod)      ├─ llamaparse                         │
│  ├─ azure_openai          └─ (none = DocTr only)               │
│  └─ anthropic                                                  │
│                                                                 │
│  NLP services (always local, no abstraction needed):            │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ OpenMed (NER)    │  │ OpenMed (De-ID)  │                    │
│  │ clinical entities │  │ 18 Safe Harbor   │                    │
│  └──────────────────┘  └──────────────────┘                    │
│                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ deepdoctection   │  │ Fax.Plus API     │                    │
│  │ + DocTr (OCR)    │  │ (managed cloud)  │                    │
│  └──────────────────┘  └──────────────────┘                    │
│                                                                 │
│  External (no abstraction — platform standard):                 │
│  ┌──────────────────┐  ┌──────────────────┐                    │
│  │ Clerk (Auth)     │  │ Supabase (DB +   │                    │
│  │ Platform standard │  │ Object Storage)  │                    │
│  └──────────────────┘  └──────────────────┘                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Environment variables that control backend selection:**

| Variable | Purpose | Production value | Dev/staging value |
|---|---|---|---|
| `LLM_SERVICE_PROVIDER` | Billing reconciliation LLM | `deepseek` | `azure_openai` or `anthropic` |
| `OCR_CLOUD_BACKEND` | Tier 2 handwriting OCR escalation | `llamaparse` | `llamaparse` (same in both; only active if §19 spike fails) |
| `NLP_BACKEND` | Clinical NER engine | `openmed` | `openmed` (same in both) |
| `STORAGE_PROVIDER` | Object storage backend | `supabase` | `supabase` (same in both) |

**Loose coupling:** Every external call goes through an abstract base class. Changing a backend is a deploy-time config change — zero code changes required. The application code calls `service.process()` — it never imports a specific backend implementation directly.

---

## 3. Processing Pipeline Stages with Tool Assignments

```
DOCUMENT INGEST ─────────────────────────────────────────────────────────────────
│
│  Fax received (Fax.Plus webhook) ──► PDF bytes to Supabase Storage
│  Manual upload (attorney portal) ──► PDF bytes to Supabase Storage
│
▼
STAGE 1: OCR (Tier 1 — always local, air-gapped)
│
│  Tool: deepdoctection + DocTr backend
│  Input: PDF bytes from Supabase Storage
│  Output: raw text + layout JSON + per-page confidence scores
│  Network: zero outbound calls
│
├──► Page confidence ≥ 80% AND not handwritten ──► Accept result, proceed to Stage 2
│
└──► Page confidence < 80% OR handwritten ──► STAGE 1b (Tier 2 — cloud, BAA)
│       │
│       │  Tool: LlamaParse (selected by OCR_CLOUD_BACKEND, active only if §19 spike triggers escalation)
│       │  Input: Individual flagged page image only (not full document)
│       │  Output: higher-confidence text for handwritten/low-conf pages
│       │  Network: HTTPS outbound to LlamaIndex or AWS (BAA-covered)
│       │
│       └──► Still below 80% after escalation ──► Flag for attorney manual review
│
▼
STAGE 2: PHI De-Identification (text-level)
│
│  Tool: OpenMed Nemotron Privacy Filter
│  Input: raw OCR text from Stage 1
│  Output: redacted_text + phi_map (encrypted)
│  All 18 HIPAA Safe Harbor identifiers redacted
│  Network: zero outbound calls
│
│  ★ CRITICAL: This runs BEFORE any downstream processing.
│  No clinical NER, flag detection, or chronology assembly ever
│  sees raw PHI in plaintext.
│
▼
STAGE 3: Clinical Event Extraction
│
│  Tool: OpenMed Clinical NER
│  Input: redacted text from Stage 2
│  Models: disease_detection_superclinical, pharma_detection_superclinical,
│          anatomy_detection_electramed (run in parallel)
│  Output: entity list → chronology entries with source citations
│  Network: zero outbound calls
│
▼
STAGE 4: Flag Detection
│
│  ┌─── Tier 1 Flags (algorithmic — string match + date math) ──────────┐
│  │                                                                     │
│  │  • Treatment gaps (≥14 days, configurable)                         │
│  │  • Delayed initial treatment (incident → first encounter)          │
│  │  • Sudden treatment stop (no discharge/MMI/referral in last entry) │
│  │  • Follow-up recommended, not found                                │
│  │  • Non-compliant language (lexicon match)                          │
│  │  • Clinical record referencing unretrieved procedure/imaging       │
│  │  • Referral without specialist records                             │
│  │  • Facility vs physician records split                             │
│  │  • Pharmacy record without prescription in clinical notes          │
│  │                                                                     │
│  └────────────────────────────────────────────────────────────────────┘
│
│  ┌─── Tier 2 Flags (NLP-assisted — OpenMed cross-record comparison) ──┐
│  │                                                                     │
│  │  • Conflicting incident descriptions across providers              │
│  │  • Changing symptom complaints without progression                 │
│  │  • Pre-existing condition signals (same body region pre/post)      │
│  │  • Degenerative language in imaging reports                        │
│  │  • Baseline-comparison absent                                      │
│  │  • Functional impact tagging (not a flag — organizational metadata)│
│  │                                                                     │
│  └────────────────────────────────────────────────────────────────────┘
│
│  ┌─── Tier 3 (attorney judgment only — TRACE surfaces raw data) ─────┐
│  │                                                                     │
│  │  • Pre-existing vs causation assessment                            │
│  │  • Treatment gap clinical significance                             │
│  │  • Materiality of conflicting descriptions                         │
│  │  • Genuineness of non-compliance notations                          │
│  │  • Degenerative finding aggravation                                │
│  │                                                                     │
│  └────────────────────────────────────────────────────────────────────┘
│
▼
STAGE 5: Billing Reconciliation
│
│  Input: billing records (from billing repo API or fax fallback)
│         + redacted clinical notes
│  Tool: CPT lookup table → string match for time-documentation requirements
│  Tool (fallback): LLMService (DeepSeek or Azure OpenAI) for MDM complexity eval
│  Output: billing discrepancy event nodes
│  Prohibited string filter runs on all LLM output before DB write
│
▼
STAGE 6: Chronology Assembly
│
│  Merged chronology entries (all providers, date order)
│  + linked event nodes (all flags with source citations)
│  + functional impact tags
│  → Written to Supabase PostgreSQL (operational DB)
│
▼
STAGE 7: Attorney QA Portal
│
│  Split-panel UI: chronology (left) + source document PDF.js (right)
│  Flag annotation workflow (inline, auto-save)
│  Demand-ready gate: locked until all Priority flags annotated
│  Export: PDF (disclaimer on every page) + JSON (CMS format)
```

---

## 4. Deployment Topology

```
┌─────────────────────────────────────────────────────────────────────┐
│                       PRODUCTION (AIR-GAPPED)                        │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Fly.io (region: iad + lax/sea for redundancy)                │   │
│  │                                                                │   │
│  │  ┌─────────────────┐  ┌─────────────────┐                     │   │
│  │  │ FastAPI (TRACE)  │  │ React Frontend   │                    │   │
│  │  │ Docker container │  │ (served by       │                    │   │
│  │  │ uvicorn          │  │  FastAPI or CDN) │                    │   │
│  │  └────────┬────────┘  └─────────────────┘                     │   │
│  │           │                                                    │   │
│  │           │ Private network (Fly.io internal)                  │   │
│  │           ▼                                                    │   │
│  │  ┌────────────────────────────────────────────────────────┐   │   │
│  │  │ Supabase (managed PostgreSQL + Storage)                 │   │   │
│  │  │  ├─ Operational DB (cases, providers, chronology, etc.) │   │   │
│  │  │  ├─ PHI Store (clients table, pgcrypto encrypted)      │   │   │
│  │  │  └─ Storage (trace-medical-records bucket, private)     │   │   │
│  │  └────────────────────────────────────────────────────────┘   │   │
│  │                                                                │   │
│  │  Local services (runs inside container, zero outbound):        │   │
│  │  ├─ OpenMed (clinical NER + de-identification)                │   │
│  │  ├─ deepdoctection + DocTr (OCR pipeline)                     │   │
│  │  ├─ DeepSeek V4 Pro (billing LLM, air-gapped)                 │   │
│  │  └─ spaCy/SpaCy-based utilities (sentence segmentation, etc.) │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  External reachable (allowed through air-gap):                       │
│  ├─ Clerk API (auth tokens only — no PHI)                           │
│  ├─ Fax.Plus API (PHI in transit — BAA-covered)                     │
│  ├─ CMS NPI Registry API (gov HTTPS — provider data only)           │
  │  └─ LlamaParse (handwritten pages only — BAA-covered, only if Phase 1C spike triggers escalation)      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                       DEV / STAGING (CLOUD)                          │
│                                                                      │
│  Same topology as production BUT:                                    │
│  ├─ No air-gap restriction                                          │
│  ├─ LLM_SERVICE_PROVIDER = azure_openai or anthropic (BAA-covered)  │
│  ├─ OCR_CLOUD_BACKEND = llamaparse or textract (any pages)          │
│  ├─ Local development: supabase start (local Supabase + MinIO)      │
│  └─ Local development: OpenMed + deepdoctection run on dev machine  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Secrets management:** All secrets (SUPABASE_SERVICE_ROLE_KEY, Fax.Plus API key, OCR API keys, LLM API keys, Clerk keys) stored in Fly.io secrets (`fly secrets set`). Never in fly.toml, Dockerfiles, or git history.

---

## 5. All Decisions Since ADR-000

| # | Decision | Previous position | New position | Date |
|---|----------|-------------------|--------------|------|
| 1 | Auth | Auth0 (spec LOCKED) | Clerk (platform standard) | ADR-000, Jul 8 |
| 2 | Object storage | AWS S3 via boto3 | Supabase Storage (platform standard) | ADR-000, Jul 8 |
| 3 | Observability | AWS CloudWatch | SigNoz + Sentry (platform standard) | ADR-000, Jul 8 |
| 4 | Hosting | AWS | Fly.io (platform standard) | ADR-000, Jul 8 |
| 5 | PRD §12 | 9 questions | 12 questions | Jul 9 |
| 6 | LLM backend | Azure OpenAI LOCKED + DeepSeek prohibited | LLM-agnostic LLMService abstraction; DeepSeek V4 Pro production default | Jul 9 |
| 7 | OCR engine | AWS Textract (LOCKED) | Hybrid: deepdoctection + DocTr (Tier 1, air-gapped) + LlamaParse (Tier 2, handwriting escalation) | Jul 9 |
| 8 | Clinical NLP | scispaCy en_core_sci_md | OpenMed (1,000+ models, HIPAA de-ID built-in) | Jul 9 |
| 9 | PHI de-identification | pgcrypto (DB-level only) | OpenMed Nemotron Privacy Filter (text-level) + pgcrypto (DB-level) — dual layer | Jul 9 |
| 10 | Audit logging | CloudWatch + pgaudit | audit_log table (INSERT-only) + Fly.io log shipping; pgaudit unavailable on Supabase managed | ADR-000, Jul 8 |
| 11 | File storage self-hosting | Not evaluated | MinIO evaluated, deferred to Phase 2+ — Supabase Storage kept | Jul 9 |
| 12 | Fax self-hosting | Not evaluated | ICTFax evaluated, deferred to Phase 2+ — Fax.Plus kept (still requires SIP trunk) | Jul 9 |
| 13 | Flag detection scope | Treatment gaps + billing only | Extended Flag Registry: 15 flags across 5 categories, Tier 1/2/3 | Jul 9 |
| 14 | Service abstractions | None (direct imports) | LLMService + OCRService with env-var backend selection, zero code changes to switch | Jul 9 |
| 15 | Spanish records | Open question (PRD §12 Q6) | Resolved — OpenMed handles 12 languages including Spanish automatically | Jul 9 |
| 16 | Spec agent discretion | Not specified | Part 0 added: Alembic, pytest, repo layout, IaC, local emulation, AGENT CHOICE pattern | Jul 9 |
| 17 | Billing data location | Billing repo or FM DB | TRACE's own DB (medical_bill_line table + CPT/ICD reference tables) — medical data stays in medical context | ADR-000, Jul 8 |
| 18 | SOL engine | Build own 50-state table | Reuse INTAKE's jurisdiction JSON files + persisted statute snapshot | ADR-000, Jul 8 |
| 19 | Retainer trigger | Synchronous POST from INTAKE | Subscribe to INTAKE outbox (event-driven) | ADR-000, Jul 8 |
| 20 | Test infrastructure | pytest implied | pytest + pytest-asyncio + httpx.AsyncClient + factory_boy + SQLite in-memory fallback | Part 0, Jul 9 |
| 21 | Database schema naming | `public` schema (default) | Named `trace` schema for operational tables, `trace_phi` schema for PHI store. TRACE runs in its own Supabase project — separate from LEVERAGE (`cnbzuiuyppzrygxllgxj`, schema `leverage`). No shared databases. | Jul 9 |
| 22 | Product simplification | Not evaluated | Case Readiness Board + 8 workflow improvements absorbed (§23-24) | Jul 9 |
| 23 | Document signing | Not specified | DocuSeal (AGPL-3.0, self-hosted on Fly.io) — retainer + HIPAA authorization + fee agreement signing before case initialization. No BAA needed (within Fly.io boundary). Client signs on phone in under 3 minutes. Signed PDF with embedded audit trail. Case stage starts at `PENDING_SIGNATURE`. | Jul 9 |

---

## 6. Outstanding Decisions (Deferred, Not Blocking)

| # | Item | Reason deferred | Target phase |
|---|------|-----------------|--------------|
| 1 | MinIO for fully air-gapped file storage | Supabase Storage adequate; MinIO Community in maintenance mode; ops burden high | Phase 2+ |
| 2 | ICTFax for self-hosted fax | Still requires SIP trunk provider; T.38 config is error-prone; Fax.Plus BAA already signed | Phase 2+ |
| 3 | DICOM/radiology support (Orthanc/OHIF) | Not in Phase 1 scope — validate core pipeline first | Phase 4 |
| 4 | Metriport HIE integration | Phase 3 enhancement in original spec. TEFCA has exchanged 1B records (June 2026) — HHS actively strengthening the network. Individual Access Services pathway enables attorney-authorized record retrieval directly through TEFCA. | **Accelerated: Phase 1C feasibility spike** — assess TEFCA viability as primary retrieval channel for participating providers. If feasible, build in Phase 2 (not Phase 3). Fax remains fallback for non-participating providers. |
| 5 | Billing repo integration (vs TRACE-owned medical_bill_line) | Billing repo API not yet ready; temp fallback in place; medical data stays in TRACE | Phase 1D+ |

---

## 7. Phase 1A Build Input (Superseded — see §15 and §22)

This section is retained for historical reference only. The current Phase 1A build sequence is in §15 (Updated Phase 1A Build Sequence). Pre-flight hard gates are in §22 (Updated Phase 1A Pre-Flight Actions). Both supersede the content below.

---

## 8. PHI Redaction at Every Pipeline Stage Boundary

**Risk:** OCR output contains raw PHI. If an unhandled exception occurs during Stage 2 (de-identification), the raw OCR text could appear in error traces, log output, or SigNoz/Sentry. Similarly, `phi_map` access patterns could leak in debug logs.

**Defense-in-depth additions:**

```python
# middleware/log_redaction.py — applied to ALL log handlers
import logging
import re

PHI_PATTERNS = [
    (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]'),       # SSN
    (r'\b\d{2}/\d{2}/\d{4}\b', '[DOB_REDACTED]'),        # DOB (MM/DD/YYYY)
    (r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', '[NAME_REDACTED]'), # First Last
    (r'\b\d{10}\b', '[PHONE_REDACTED]'),                  # Phone
    (r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', '[EMAIL_REDACTED]'),
]

class PHIRedactionFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            msg = record.msg
            for pattern, replacement in PHI_PATTERNS:
                msg = re.sub(pattern, replacement, msg, flags=re.IGNORECASE)
            record.msg = msg
        return True  # always pass — never drop a log entry

# Apply to ALL handlers
logging.getLogger().addFilter(PHIRedactionFilter())
```

**Enforcement rules:**
- PHI redaction filter is applied at the root logger — no handler can bypass it
- Stage 2 (OpenMed de-ID) runs in a try/except that catches and redacts ALL exception messages before logging — the raw OCR text never appears in any log output even if de-ID fails
- `phi_map` is never logged — not even in debug mode. If de-ID succeeds, the phi_map is immediately encrypted with pgcrypto and stored. The in-memory copy is zeroed after storage
- Pipeline job errors must return generic error codes to the API — never stack traces, never raw text excerpts, never page content

**Phase 1A acceptance test:** Run a known PHI-containing PDF through the full pipeline. Grep all log output (stdout, file, SigNoz sandbox) for the known PHI values. Assert zero matches.

---

## 9. Pipeline Event Audit Logging

**Gap:** Current `audit_log` captures API calls only (HTTP method + URL + actor). Internal pipeline events — OCR start/completion, de-ID success/failure, flag detection runs, LLM billing reconciliation — produce no audit record.

**Addition:** Extend `audit_log` to capture pipeline events:

```sql
-- Pipeline events use the same audit_log table with actor_type = 'SYSTEM'
-- Example entries:
-- actor_type='SYSTEM', action='OCR_STAGE_START', resource_type='DOCUMENT', resource_id=<doc_id>
-- actor_type='SYSTEM', action='OCR_STAGE_COMPLETE', details='{"confidence": 0.94, "pages": 12, "backend": "doctr"}'
-- actor_type='SYSTEM', action='DEID_STAGE_COMPLETE', details='{"entities_redacted": 23, "model": "openmed-nemotron"}'
-- actor_type='SYSTEM', action='FLAG_DETECTION_TIER1_COMPLETE', details='{"flags_generated": 8, "rule_version": "1.0"}'
-- actor_type='SYSTEM', action='OCR_TIER2_ESCALATION', details='{"pages_escalated": 2, "backend": "llamaparse", "reason": "handwritten"}'
```

**Enforcement:** Same INSERT-only permission for `trace_app_role` applies. Pipeline events are immutable — no UPDATE or DELETE. HIPAA §164.312(b) audit controls satisfied.

---

## 10. Adaptive OCR Confidence Thresholds

**Replaces:** Static 80% threshold for all document types.

```python
# OCR confidence thresholds by document type and language
OCR_THRESHOLDS = {
    ("typed", "en"): 0.90,       # digital PDF, English
    ("handwritten", "en"): 0.70,  # handwritten notes, English
    ("typed", "es"): 0.85,       # digital PDF, Spanish
    ("handwritten", "es"): 0.65,  # handwritten notes, Spanish
}

def get_escalation_threshold(doc_type: str, language: str) -> float:
    return OCR_THRESHOLDS.get((doc_type, language), 0.80)
```

**How document type is determined:** deepdoctection's layout analysis classifies pages as typed, handwritten, or mixed before OCR runs. Language is detected by OpenMed's auto-detection during de-ID. Thresholds are recalibrated after Phase 1D using real accuracy data from the first 100 cases.

**Circuit breaker for cloud escalation:** If cloud OCR (LlamaParse/Textract) returns errors on > 50% of escalated pages within a 5-minute window, escalation is paused and pages are queued for retry. This prevents cost runaways and cascading failures.

---

## 11. Flag Provenance Metadata

**Risk:** An attorney deponed about a flag cannot explain how the system generated it. Defense counsel challenges the flag as "black box AI." Legal defensibility requires traceability.

**Addition to Event Node schema:** Every flag carries provenance metadata:

```sql
ALTER TABLE event_nodes ADD COLUMN provenance JSONB;

-- Example provenance for a Tier 1 flag:
-- {
--   "rule_name": "follow_up_not_found",
--   "rule_version": "1.0",
--   "detection_method": "string_match",
--   "matched_string": "follow up in 2 weeks",
--   "matched_in_entry_id": "uuid",
--   "threshold_applied": null,
--   "model_name": null,
--   "model_version": null,
--   "confidence": null
-- }

-- Example provenance for a Tier 2 flag:
-- {
--   "rule_name": "conflicting_incident_descriptions",
--   "rule_version": "1.0",
--   "detection_method": "openmed_ner_cross_record_comparison",
--   "matched_string": null,
--   "matched_in_entry_id": null,
--   "threshold_applied": null,
--   "model_name": "openmed-ner-clinical-large",
--   "model_version": "1.7.0",
--   "confidence": 0.87
-- }
```

**Display in attorney QA:** Hovering over a flag shows the provenance metadata. The attorney can cite exactly which rule or model version generated the flag, the exact string matched (for Tier 1), and the confidence score (for Tier 2).

---

## 12. Response to Remaining Review Findings

The following items from the architecture review were evaluated and either already covered, deferred, or rejected. Reasoning is stated for each.

| Finding | Verdict | Reason |
|---------|---------|--------|
| Dedicated KMS (Vault/AWS KMS) for phi_map | ❌ Rejected for Phase 1 | pgcrypto with separate encryption key + key rotation is sufficient for 20-firm early access. Adds ops burden without proportional risk reduction. Revisit Phase 2+. |
| Active-active Fly.io failover | ❌ Deferred to Phase 2+ | iad + lax/sea redundancy covers regional outages. Active-active requires cross-region data replication with latency tradeoffs. Premature for early access scale. |
| Secrets rotation automation | ⚠️ Acknowledged, manual for now | Fly.io has no automated secrets rotation API. Quarterly manual rotation documented in deployment runbook. Automate if Fly.io adds rotation support. |
| PDF.js client-side PHI | ❌ Rejected | This is inherent to displaying medical records in a browser. Mitigations already in place: 15-min signed URLs, no document bytes through app server, no localStorage. Server-side PDF redaction would require rendering + OCR overlaying — massive infra addition for negligible risk reduction. |
| Deprecate Azure OpenAI / Anthropic from LLMService | ❌ Rejected | LLMService abstraction exists precisely to support multiple backends for different environments. Production uses DeepSeek (air-gapped). Dev/staging may use any BAA-covered provider. Removing options defeats the abstraction's purpose. |
| Deprecate Textract from OCR backends | ✅ Accepted | LlamaParse has better handwriting accuracy. Textract removed from Tier 2 options. OCR_CLOUD_BACKEND now supports only `llamaparse`. |
| Replace DeepSeek V4 Pro with smaller model | ❌ Rejected | No benchmarking data exists to justify this. If cold start time or memory pressure becomes measurable in Phase 1D, evaluate alternatives then. Premature to switch model size without data. |
| Supabase Storage deprecation | ❌ Already addressed | Evaluated in §6 (Outstanding Decisions). MinIO deferred to Phase 2+. Current mitigation (BAA, private bucket, 15-min signed URLs) adequate for Phase 1. |
| Clerk deprecation for self-hosted auth | ❌ Rejected | Clerk is the platform standard across ALL TrueVow services. Replacing it would break INTAKE, SETTLE, and shared auth. Not changing. |
| RLS policy examples missing | ⚠️ Acknowledged | Policies exist in the Supabase schema migration files. Will inline examples in the deployment runbook. Not blocking for architecture doc. |
| Load testing suite | ⚠️ Deferred to Phase 1E | Phase 1A builds the skeleton. Load testing matters when the QA interface processes real chronologies. Include in Phase 1E acceptance criteria. |
| Export cryptograpic signing | ⚠️ Deferred to Phase 2+ | Early access attorneys won't expect/need hash-verified exports. Important for adversarial proceedings later. Document as Phase 2 enhancement. |
| Cost monitoring | ⚠️ Deferred to Phase 2+ | Phase 1 early access has predictable 20-firm volume. Track manually during Phase 3 early access launch. Automate at scale. |

---

## 13. Soft Additions Absorbed from Architecture Review

Low-effort, high-leverage items added without architectural change:

### 13.1 Clerk Custom Claims for RLS Scoping

Add two custom claims to Clerk JWT tokens for TRACE users:

```json
{
  "app_metadata": {
    "firm_id": "org_abc123",
    "role": "attorney"
  }
}
```

- `firm_id` = Clerk `org_id` — already the basis for `app.current_tenant_id` in the INTAKE GUC pattern
- `role` = `attorney` | `paralegal` | `admin` — enables role-aware RLS policies and UI feature gating
- Extracted in FastAPI middleware via Clerk JWKS validation — zero additional infra
- Enables RLS policies like: `CREATE POLICY firm_isolation ON cases USING (firm_id = current_setting('app.current_tenant_id'))`

### 13.2 DeepSeek LLM Benchmark Hook

Add a `--benchmark` flag to the billing reconciliation test suite for Phase 1D:

```bash
pytest tests/jobs/test_billing_reconciliation.py --benchmark --model deepseek
pytest tests/jobs/test_billing_reconciliation.py --benchmark --model azure_openai_gpt4o_mini
```

Produces: accuracy, latency, CPT code match rate, hallucination rate, per-request cost. Generates the data needed to decide on model size/type without speculation.

### 13.3 Failover Runbook (Documentation Only)

Manual steps to fail over from `iad` to `lax` if primary region is unavailable:

```
1. fly regions add lax — add secondary region to app
2. fly scale count 2 — deploy instance in lax
3. Update Supabase connection string to use nearest read replica (if available)
4. Verify /health endpoint returns 200 from lax instance
5. Update DNS / internal service registry to point to lax
6. When iad recovers: fly regions remove iad, fly scale count 1
```

Docs-only — stored in deployment runbook alongside BAA verification checklist.

---

## 14. Phase 1A Readiness Checklist

Confirmed before first line of Phase 1A code:

| # | Item | Phase | Owner | Status |
|---|------|-------|-------|--------|
| 1 | PHI redaction filter on all log handlers (`PHIRedactionFilter`) | 1A | Backend | ☐ |
| 2 | `pipeline_audit_log` table + Alembic migration | 1A | DBA | ☐ |
| 3 | `phi_map` zeroed in memory after encryption — verified in acceptance test | 1A | Backend | ☐ |
| 4 | Egress allowlist in `fly.toml` (Clerk, Fax.Plus, CMS NPI only) | 1A | DevOps | ☐ |
| 5 | Adaptive OCR thresholds (90% typed / 70% handwritten) wired into OCR job | 1A | ML Eng | ☐ |
| 6 | Circuit breaker on external API calls (Fax.Plus, CMS NPI) | 1A | Backend | ☐ |
| 7 | Clerk custom claims (`firm_id` + `role`) in JWT token | 1A | Auth | ☐ |
| 8 | OpenMed models verified SHA256 on load — no network calls at inference | 1A | ML Eng | ☐ |
| 9 | Flag provenance metadata schema (JSONB column on event_nodes) | 1B | Backend | ☐ |
| 10 | SHA256 model verification on load for all models | 1B | ML Eng | ☐ |
| 11 | Load testing suite (locust) with target: 100 concurrent faxes, <5s OCR latency | 1E | QA | ☐ |
| 12 | Failover runbook: iad → lax documented in deployment docs | 1A | DevOps | ☐ |
| 13 | DeepSeek benchmark hook in billing reconciliation test suite | 1D | Backend | ☐ |

---

## 15. Updated Phase 1A Build Sequence

Items 1-8 from the readiness checklist are now embedded in the build sequence:

1. FastAPI skeleton + Clerk JWKS middleware (including `firm_id`/`role` custom claims extraction) + `PHIRedactionFilter` on all log handlers + audit middleware + `/health` endpoint
2. **DocuSeal:** self-hosted instance deployed on Fly.io (Docker image, internal network only). DOCUSEAL_API_URL, DOCUSEAL_API_TOKEN, DOCUSEAL_WEBHOOK_SECRET in Fly.io secrets. Firm templates uploaded (retainer, contingency fee, HIPAA auth). Webhook registered. Test signing session completed — webhook fires, signed PDF in Supabase Storage, `hipaa_auth_status` updates to SIGNED
3. Supabase PostgreSQL schema: all tables from Spec §3.1 + `pipeline_audit_log` table + `signed_documents` table via Alembic migrations + roles/RLS
3. `fly.toml` with egress allowlist (Clerk, Fax.Plus, CMS NPI only) + Dockerfile (region `iad`)
4. LLMService abstraction (pluggable backends, env-var selection)
5. OCRService abstraction (deepdoctection + DocTr backend, adaptive thresholds by document type/language)
6. OpenMed service wrapper (deid_text + analyze_text, SHA256 model verification on load, local model loading, zero network calls — verified by acceptance test)
7. deepdoctection service wrapper (ANALYZER.analyze, DocTr backend, local only)
8. StorageService (Supabase Storage: upload, presign 15-min expiry, delete)
9. Circuit breaker on Fax.Plus + CMS NPI client calls
10. pytest + SQLite in-memory fallback for local acceptance testing
11. Failover runbook (iad → lax) + BAA verification checklist in deployment docs

**Phase 1A acceptance criteria (gate to Phase 1B):**
- Authenticated API call logged in `audit_log` with correct actor_id, timestamp, and action
- Pipeline events (OCR, de-ID) logged in `pipeline_audit_log` with correct stage, event_type, and metadata
- Unauthenticated request returns 401
- Firm A cannot access firm B's data (RLS verified)
- Supabase Storage bucket `trace-medical-records` exists with private access policy confirmed
- OpenMed `analyze_text()` returns a result without network calls (air-gap verified)
- deepdoctection `ANALYZER.analyze()` processes a PDF with no external API calls (air-gap verified)
- No raw PHI appears in application logs, error traces, or SigNoz/Sentry — verified by scanning log output with PHI pattern detector during acceptance test
- Clerk JWT contains `firm_id` and `role` custom claims — verified by decoding token in middleware test
- Egress allowlist enforced — outbound calls to non-allowlisted hosts are blocked (verified by attempting calls to non-allowlisted endpoints)
- `phi_map` zeroed from memory after encryption — verified by inspecting process memory in acceptance test
- Supabase HIPAA configuration confirmed: Team Plan or higher, HIPAA add-on enabled, SSL Enforcement on, Network Restrictions configured, Point in Time Recovery enabled, connection logging on (log_connections = on, not Supabase's default 'off' for new projects), no PHI in Edge Functions or Fly Postgres
- Supabase Edge Functions confirmed NOT routing any PHI — all processing through FastAPI container only

---

## 16. Supabase HIPAA Configuration Checklist

**Critical finding (July 9, 2026):** Supabase's hosted platform has HIPAA controls but requires explicit configuration — they are not on by default. Self-hosted Supabase does not support HIPAA controls. Missing any of these steps means PHI is not HIPAA-compliant on Supabase, regardless of whether a BAA is signed.

**Phase 1A blocker — all items must be verified before any PHI enters the system:**

| # | Requirement | Default | Action |
|---|------------|---------|--------|
| 1 | **Team Plan** (minimum) | Free tier | Upgrade Supabase project to Team Plan or higher |
| 2 | **HIPAA add-on** enabled | Off | Enable per-project in Supabase dashboard |
| 3 | **MFA** on all project member accounts | Optional | Enforce MFA for all Supabase dashboard users |
| 4 | **SSL Enforcement** | Off | Turn ON to force TLS for all database connections |
| 5 | **Network Restrictions** | None | Whitelist only Fly.io private network IP range |
| 6 | **Point in Time Recovery** | Off | Enable PITR for operational DB + PHI store |
| 7 | **Connection logging** (`log_connections`) | **Off** (default for new projects from Jul 9, 2026) | Explicitly set to ON — Security Advisor warns if disabled |
| 8 | **BAA signed** with Supabase | Not signed | Execute BAA before Phase 1A begins |

**Hard prohibitions:**
- **No PHI in Supabase Edge Functions** — Edge Functions do not support HIPAA controls. All processing must go through the FastAPI container on Fly.io. If any TRACE job currently routes through an Edge Function, that path must be eliminated before Phase 1A.
- **No PHI in Fly Postgres** — Use Supabase managed PostgreSQL only. Do not use Fly.io's Postgres offering for any PHI-adjacent data.
- **No self-hosted Supabase for PHI** — Self-hosted Supabase does not support HIPAA controls. Only the hosted Supabase platform with the HIPAA add-on enabled is HIPAA-eligible.

**Verification in acceptance test:** Verify `log_connections = on` via `SHOW log_connections;`. Attempt connection without TLS — assert rejection. Attempt connection from non-allowlisted IP — assert rejection. Confirm no Edge Functions are deployed in the TRACE project.

---

## 17. Fax.Plus Pricing and Documo Alternative

**Current state:** Fax.Plus HIPAA compliance with BAA requires the Enterprise plan. The **published** starting price is $99.99/month (annual, 1,000+ pages). Lower tiers (Basic $8.99, Premium $17.99, Business $34.99) do not include HIPAA coverage.

**Important caveat — published vs actual price:** Enterprise fax contracts routinely exceed published pricing once the following are factored in: volume overages beyond the included page tier, multi-user pricing (a 20-firm early access cohort sending through a single API key may trigger usage-based renegotiation), compliance riders attached to the BAA, and custom enterprise minimums common in healthcare contracts. The actual monthly cost could be hundreds of dollars above the $99.99 published figure. The agent does not have TrueVow's signed Fax.Plus agreement and cannot verify the actual rate.

**Spec requirement:** The agent must verify current Fax.Plus Enterprise pricing before provisioning. The spec should reference the Enterprise tier explicitly — not just "Fax.Plus Enterprise."

**Recommended alternative — Documo:** Documo is the top HIPAA fax pick in the Wirecutter 2026 review. Unlike Fax.Plus where HIPAA is Enterprise-only, Documo includes BAA on every plan. Features: modern web portal, OCR, single sign-on, API access. If Fax.Plus Enterprise pricing is prohibitive at early access volume, Documo is the drop-in replacement with comparable API surface.

**Decision:** Keep Fax.Plus for Phase 1A (BAA already signed). The switch trigger is quantitative: once the actual Fax.Plus Enterprise invoice amount is known (not the published price — the real bill), compare against Documo's all-plan BAA pricing at the same projected page volume. If Fax.Plus is more than 2x Documo, switch to Documo. Both APIs are wrapped identically — zero architecture impact. Make the decision before Phase 1C fax transmission endpoints are built. Documo is the top HIPAA fax pick in the Wirecutter 2026 review; features include modern web portal, OCR, SSO, and API access with BAA included on every plan (no enterprise upsell required for HIPAA coverage).

---

## 18. TEFCA and HIE Acceleration

**New data (June 26, 2026):** HHS ONC announced new steps to strengthen TEFCA, the nationwide health information exchange network. TEFCA has exchanged one billion health records. The network supports six defined exchange purposes including **Individual Access Services** — the pathway that allows an attorney, as the client's authorized representative, to request medical records directly through TEFCA rather than sending a fax.

**Impact on TRACE:** In 2026, hybrid workflows combining TEFCA-enabled electronic record retrieval and traditional provider fax outreach are the operational reality for law firms. TEFCA adoption is accelerating and is no longer speculative.

**Previous position:** Metriport HIE integration was listed as Phase 3 enhancement, not a Phase 1 dependency.

**Updated position:** TEFCA feasibility assessment moves to Phase 1C (concurrent with provider confirmation and fax transmission). Specific tasks:

- Before Phase 1C: assess whether Individual Access Services pathway can serve as a primary record retrieval channel for TEFCA-participating providers, with fax as the fallback for non-participating providers
- If feasible: build TEFCA integration as Phase 2 (not Phase 3), using Metriport or direct TEFCA QHIN connection
- Phase 1C proceeds with fax-only (Fax.Plus) as planned — TEFCA assessment does not block Phase 1C, it runs in parallel as a spike

**Decision recorded in Outstanding Decisions table (updated §6):** TEFCA feasibility spike added to Phase 1C with target decision deadline before Phase 1D begins.

---

## 19. Handwritten OCR Accuracy Spike — Required Before Phase 1D

**Research confirms:** Handwriting recognition is OCR's greatest challenge. Traditional systems achieve 50–70% accuracy. AI systems (Textract, LlamaParse) achieve 82–95%. deepdoctection + DocTr achieves strong results on digital PDFs but has not been benchmarked specifically on handwritten medical records.

The spec sets an 85% accuracy target for clean scans (PRD §6.2). The adaptive threshold system (§10) allows handwritten thresholds as low as 70% — but this is a flagging threshold, not an accuracy guarantee. If DocTr consistently produces sub-80% accuracy on handwritten physician notes, the manual review burden overwhelms the attorney QA workflow.

**Required spike (Phase 1C, before Phase 1D OCR pipeline is built):**

| Step | Task |
|------|------|
| 1 | Assemble a benchmark set of 30+ handwritten clinical note pages (de-identified, covering common PI specialties: ER, chiropractic, orthopedics, PT) |
| 2 | Run deepdoctection + DocTr on the benchmark set |
| 3 | Measure: per-page confidence scores, character error rate (CER), word error rate (WER), medical term accuracy |
| 4 | Decision gate: |
|   | If DocTr achieves ≥80% WER accuracy on handwritten notes → proceed with DocTr-only, adaptive thresholds as specified |
|   | If DocTr achieves 65–79% → re-evaluate cloud OCR escalation (LlamaParse) for handwritten pages — the air-gap purity vs manual review burden trade-off is real |
|   | If DocTr achieves <65% → cloud OCR escalation is mandatory for handwritten pages. Air-gap purity yields to quality |

This spike does not block Phase 1C (provider confirmation and fax transmission — no OCR involved). It must complete before Phase 1D build begins. The decision gate output updates the OCR section of the Technical Spec.

---

## 20. Data Retention Policy for phi_map

**New data entity:** The OpenMed `phi_map` — the offset map linking redacted tokens to original PHI values — is PHI. It must have explicit retention and destruction policies.

**Policy:**
- `phi_map` is encrypted with pgcrypto at rest immediately after OpenMed de-ID completes
- `phi_map` retention matches the case retention period (minimum 6 years per HIPAA)
- When a case is purged per the firm's data retention schedule: the `phi_map` row is deleted first, then the encrypted `clients` row, then the operational case data. Deletion is logged to `audit_log`
- `phi_map` is never included in database backups that are stored outside the PHI store instance — backup the PHI store separately from the operational DB
- `phi_map` is never exported with the chronology — it exists only to re-identify data for the attorney portal display
- In-memory `phi_map` is zeroed immediately after pgcrypto encryption write is confirmed (already specified in §8)

---

## 21. Vendor BAA Audit — All Stack Components

Audited July 9, 2026. Every vendor that touches PHI or PHI-adjacent data must have a signed BAA on file before the first case is processed.

| Vendor | Role | BAA required? | BAA status | Monthly cost (est.) | Pre-Phase 1A action |
|--------|------|---------------|------------|---------------------|---------------------|
| **Clerk** | Authentication (JWT + MFA) | Yes — handles auth tokens for PHI-accessing users | **Should exist** — platform standard across all TrueVow services | Platform cost (shared) | **Verify BAA is on file** with Clerk for the TrueVow-Tenants app. If not, execute before Phase 1A. *Note: ADR-000 already replaced Auth0 with Clerk. Clerk BAA should be pre-existing. If Auth0 was never fully decommissioned and still covers any TRACE auth path, confirm or migrate.* |
| **Supabase** | PostgreSQL + object storage | Yes — stores PHI at rest (clients table, phi_map, medical records PDFs) | **Must execute before production go-live** | Team Plan $25/mo + HIPAA add-on $350/mo = **~$375/mo** minimum before compute add-ons. Approval is not instantaneous — Supabase team reviews the request. | Submit HIPAA add-on request early (pre-production gate). Not blocking for Phase 1A development — synthetic data only. Ensure Team Plan is active, HIPAA add-on is requested, and all 8 configuration items in §16 are completed before any PHI enters the system. |
| **Fly.io** | Application hosting | Yes — hosts the FastAPI container that processes PHI | **Must execute before production go-live** | Compute cost + **$99/mo** HIPAA compliance add-on. Self-service via dashboard (`fly.io/dashboard/personal/compliance`). Takes minutes. | Sign compliance package before production go-live. Not blocking for Phase 1A development — synthetic data only. |
| **Fax.Plus** | Cloud fax transmission | Yes — PHI transits through Fax.Plus infrastructure | Already signed (Phase 0) | Enterprise plan: published $99.99/mo; actual may exceed published after volume overages, compliance riders, multi-user pricing. See §17 for Documo switch trigger. | **Verify current Enterprise invoice amount.** Compare against Documo all-plan BAA pricing at projected Phase 1C fax volume. Switch if >2x. |
| **LlamaParse** (fallback OCR) | Tier 2 cloud OCR for handwritten pages | Yes — individual flagged pages containing PHI are sent to LlamaIndex | Not yet executed. Required only if the Phase 1C handwriting spike (§19) triggers cloud escalation. | Freemium → pay-per-page. At early access volume with only flagged pages: negligible. | Execute BAA only if spike fails. Not needed for Phase 1A. |
| **Azure OpenAI** (dev/staging LLM) | Billing reconciliation LLM in non-air-gapped environments | Yes — BAA-covered under Microsoft Healthcare BAA | **Exists automatically** — Microsoft DPA incorporates BAA for qualifying services under Enterprise Agreement/MCA/CSP. No manual activation needed. | Token costs negligible at TRACE volumes (~$0.50/mo early access, ~$12/mo GA). Text-based models only — audio/vision not covered. | No action needed. |
| **DeepSeek V4 Pro** (production LLM) | Billing reconciliation LLM in air-gapped production | No BAA needed — runs entirely within Fly.io HIPAA boundary | Covered by Fly.io BAA (self-hosted within container) | Fly.io compute only (~$3/mo combined with OpenMed + deepdoctection) | No action needed. |
| **deepdoctection + DocTr** (OCR) | Self-hosted document processing | No BAA needed — runs entirely within Fly.io HIPAA boundary | Covered by Fly.io BAA | Fly.io compute only (included in ~$3/mo estimate) | No action needed. |
| **OpenMed** (NLP + de-ID) | Self-hosted clinical NER + PHI de-identification | No BAA needed — runs entirely within Fly.io HIPAA boundary | Covered by Fly.io BAA | Fly.io compute only (included in ~$3/mo estimate) | No action needed. |
| **CMS NPI Registry** | Provider identity lookup | No BAA needed — no PHI transmitted (provider name + state only) | N/A — government API | Free | No action needed. |
| **DocuSeal** | Electronic document signing (retainer, HIPAA auth, fee agreement) | No BAA needed — self-hosted within Fly.io HIPAA boundary, covered by Fly.io BAA | Deploy in Phase 1A. Test signing session verifies webhook. | $0 (AGPL-3.0, self-hosted). ~$5–10/mo Fly.io compute | Deploy DocuSeal on Fly.io, upload firm templates, register webhook, run test signing session. Do NOT use docuseal.com cloud service — self-hosted only. |

**Consolidated monthly estimate for Phase 1 early access (20 firms, ~100 cases):**

| Line item | Monthly cost (est.) |
|-----------|---------------------|
| Fly.io compute (FastAPI + DeepSeek + OpenMed + deepdoctection) | ~$100 |
| Fly.io HIPAA compliance add-on | $99 |
| Supabase Team Plan + HIPAA add-on | ~$375 |
| Fax.Plus Enterprise (or Documo if switched) | ~$100–200 |
| LlamaParse cloud OCR (only if handwriting spike fails) | ~$5–20 |
| Clerk auth (shared platform cost) | Already budgeted |
| **Total estimated monthly** | **~$680–800** |

The Auth0 → Clerk switch (ADR-000, Decision #1) eliminated what would have been the largest unknown line item ($500–$2,000+/month enterprise auth with custom BAA negotiation). This is now a validated architectural decision: Clerk is not only the platform standard but also the fiscally correct choice.

---

## 22. Updated Phase 1A Pre-Flight Actions (Hard Gates)

These items must be completed before the first line of Phase 1A code is written. They are not aspirational — vendors with approval pipelines may take days or weeks:

| # | Action | Owner | Deadline | Status |
|---|--------|-------|----------|--------|
| 1 | **Verify Clerk BAA on file** for TrueVow-Tenants app. If missing, execute before any TRACE auth middleware is built. **This is the only genuine Phase 1A gate — Clerk handles auth for the dev environment.** | Legal / Platform | Before Phase 1A | ☐ |
| 2 | **Submit Supabase HIPAA add-on request.** Activate Team Plan, submit add-on request, wait for Supabase review approval. **NOT a Phase 1A blocker — Phase 1A development uses synthetic data only, no PHI.** This is a pre-production gate (Spec Part 9). Submit early enough to account for Supabase's non-instantaneous approval pipeline. | DevOps / Platform | Before production go-live | ☐ |
| 3 | **Sign Fly.io compliance package.** Self-service at `fly.io/dashboard/personal/compliance`. Takes minutes. **NOT a Phase 1A blocker — Phase 1A development uses synthetic data only, no PHI.** This is a pre-production gate (Spec Part 9). | DevOps | Before production go-live | ☐ |
| 4 | **Verify actual Fax.Plus Enterprise invoice amount** (not published pricing). Compare against Documo at same projected volume. Switch if >2x per §17 decision trigger. | Finance / Platform | Before Phase 1C fax endpoints are built | ☐ |
| 5 | **LlamaParse BAA timing gate:** If the Phase 1C handwriting spike (§19) fails and cloud OCR escalation is triggered, initiate the LlamaIndex BAA process immediately upon spike failure. Phase 1D OCR pipeline build does not begin until the LlamaParse BAA is executed. This closes the gap between spike decision (Phase 1C) and pipeline build (Phase 1D) — BAA approval from LlamaIndex may take 3–5 business days. | Legal / Platform | Before Phase 1D (conditional on spike result) | ☐ |

**Phase 1A development posture:** Phase 1A uses synthetic/de-identified data only. No real PHI enters the system during Phase 1A–1C. Supabase and Fly.io HIPAA configurations become hard gates at production go-live (Spec Part 9), not at Phase 1A. Only Clerk BAA verification is a Phase 1A blocker — because Clerk authenticates the dev environment.

---

## 23. Product Simplification — Case Readiness Board

**Core insight (July 2026 product review):** The market already has AI medical chronology platforms (EvenUp, Tavrn, Supio). TRACE's wedge is the INTAKE pipeline — not chronology AI. The product should simplify around one promise:

> TRACE helps PI firms know what providers, records, bills, liens, treatment gaps, and chronology items still need review before demand preparation.

**What this means for architecture:** The attorney-facing UX is not an AI dashboard with dozens of flags. It is a **Case Readiness Board** with five columns and one of four statuses per item:

| Column | Status options |
|--------|---------------|
| **Providers** | Missing / Requested / Received / Reviewed |
| **Records** | Missing / Requested / Received / Reviewed |
| **Bills** | Missing / Requested / Received / Reviewed |
| **Liens** | Not Checked / Requested / Received / Reviewed |
| **Review Flags** | Unreviewed / Confirmed / Dismissed / Needs Follow-up |

**What this does NOT change:** The Extended Flag Registry (§5.5.3 of PRD) and processing pipeline (§3) remain intact. All 15 flag types are still detected. The Readiness Board is the UX layer that makes them actionable — not a reduction in detection scope.

**Seven MVP actions (unchanged from current scope, now framed as readiness items):**

1. Import accepted matter from INTAKE outbox
2. Confirm provider list with client/staff (with confidence taxonomy)
3. Generate record-request packet from signed authorization
4. Track request status by provider (heart of Phase 1C)
5. Ingest records, bills, and lien documents
6. Build source-linked chronology with review statuses
7. Flag missing items, treatment gaps, bill/record mismatches — surface on Readiness Board

**Explicitly NOT in scope — already enforced by prohibited output registry (PRD Appendix A):**
- Case valuation, settlement range, medical causation, injury severity, demand letter generation, autonomous provider requests, client-facing app, full case-management replacement

---

## 24. Workflow Simplification — Eight Absorbed Improvements

The following product-simplification recommendations are absorbed. They refine existing workflows without adding scope.

### 24.1 Matter Acceptance Gate

TRACE must not begin on a lead — only on an accepted matter. Add an explicit gate entity that the INTAKE outbox must satisfy before case initialization:

```
retainer signed
HIPAA authorization signed
firm marks matter as accepted
→ trace_matter_accepted event
→ case initialization begins
```

This is already implied by the current architecture (INTAKE outbox fires on `engagement_letter_signed`). The gate makes it explicit and testable.

### 24.2 Provider Confidence Taxonomy (replaces HIGH/MEDIUM/LOW)

Current PRD §5.1.1 uses HIGH/MEDIUM/LOW confidence. Replace with attorney-actionable labels:

| Old | New | Meaning |
|-----|-----|---------|
| HIGH | **Confirmed** | NPI match, provider verified |
| MEDIUM | **Likely Match** | Strong NPI candidate, needs client confirmation |
| — | **Needs Client Confirmation** | Ambiguous reference, client must clarify |
| — | **Needs Staff Review** | Multiple NPI candidates, staff must select |
| LOW | **Do Not Request** | Insufficient information to identify |

The old taxonomy is a confidence score. The new taxonomy is an attorney action. Same data — different framing.

### 24.3 Record Request Lifecycle (heart of Phase 1C)

Current spec tracks provider retrieval_status. This is correct but should be elevated to a visible lifecycle that the attorney can scan:

```
Draft → Ready for Approval → Sent → Provider Confirmed Receipt →
  Partial Records Received → Complete Records Received → Closed
  OR
  Rejected / Needs New Authorization → Draft (retry)
  OR
  Overdue (day 30, no response) → Escalated
```

Each status transition is logged to `audit_log`. The attorney sees a per-provider status indicator on the Readiness Board.

### 24.4 Document Quality Flags

Add a `quality_flags` array to the `documents` table. After OCR, the document carries zero or more of:

```
LOW_OCR_CONFIDENCE
HANDWRITTEN_NOTE_DETECTED
POSSIBLE_DUPLICATE
PAGE_ORDER_UNCERTAIN
LANGUAGE_NOT_ENGLISH
MISSING_PAGE_NUMBER
POOR_SCAN_QUALITY
NEEDS_MANUAL_REVIEW
```

These are not error states — they are transparency indicators. The attorney sees when TRACE is uncertain. This builds trust and focuses manual review on pages that genuinely need it.

### 24.5 Chronology Entry Review Statuses

Every chronology entry carries a `review_status` in addition to the existing `attorney_annotation` field:

```
UNREVIEWED      → default on creation
CONFIRMED       → attorney verified against source
EDITED          → attorney modified the clinical description
DISMISSED       → attorney determined entry is not material
NEEDS_MORE_RECORDS → entry references records not yet received
```

No chronology export hides unreviewed items. The export clearly marks unreviewed entries so the attorney knows the review state before sending to opposing counsel.

### 24.6 Gap Explanation Workflow (replaces free-text annotation for treatment gaps)

For treatment gap flags (5.5.3a.1, 5.5.3a.2, 5.5.1), offer structured reasons in addition to free-text:

```
Referral delay
Insurance authorization delay
Financial hardship
Transportation issue
Symptoms improved
Provider scheduling delay
Client did not attend
Unknown
Other (free text)
```

The attorney selects a reason or writes a custom explanation. This is faster for the solo attorney than typing a full annotation and provides structured data for trend analysis across cases. Free-text annotation remains available. Medical significance is never interpreted — TRACE records the explanation, does not evaluate it.

### 24.7 Billing Match Confidence (soft matching, not binary)

Replace binary "match / no match" billing reconciliation with confidence tiers:

| Match confidence | Meaning |
|-----------------|---------|
| **Strong match** | Same provider, same date, same CPT category |
| **Likely match** | Same provider, date within 2 days, CPT category aligns |
| **Possible match** | Provider group match, date within 7 days |
| **No matching treatment note** | Bill exists, no clinical note found for provider/date window |
| **Treatment note with no bill** | Clinical event exists, no billing record found |
| **Needs review** | Insufficient data to classify |

This reduces false alarms that overwhelm the attorney. The threshold between "flag" and "surface" is configurable per firm.

### 24.8 Mandatory Sign-Off Before Demand-Ready

The existing Checkpoint 4 (demand-ready approval) already requires attorney sign-off. Make the checklist explicit:

```
[ ] Provider list confirmed
[ ] Records reviewed for all received providers
[ ] Bills reconciled (all billing discrepancies reviewed)
[ ] Treatment gaps reviewed (all gaps have explanations)
[ ] Liens checked (if applicable)
[ ] Chronology reviewed (all entries have review_status ≠ UNREVIEWED)
[ ] Attorney/paralegal sign-off recorded
```

The "Mark Demand-Ready" button is locked until all checkboxes are confirmed. Each checkbox click logs to `audit_log` with actor_id and timestamp. This is not new behavior — it formalizes what Checkpoint 4 already requires.

---

## 25. Database Schema Decision — Separate Project, Named Schemas

**Inspected July 9, 2026.** The codebase exploration confirmed the full picture.

**LEVERAGE** is a completely independent service at `TrueVow_Tenant_LEVERAGE_Service`. It has:
- Its own Supabase project (`cnbzuiuyppzrygxllgxj`)
- Named schema: `leverage` (not `public`), with `search_path = leverage, public`
- Synchronous SQLAlchemy, single database, no PHI store separation
- Production-ready at 98.25% completion

**TRACE** was already designed as an independent service with:
- Its own Supabase project (not yet provisioned — `.env.example` only, no `.env.local`)
- Default `public` schema for operational tables
- Async SQLAlchemy, dual-engine (operational + PHI), RLS GUC injection
- Falls back to in-memory SQLite when `TRACE_DATABASE_URL` is unset

**Decision:** TRACE remains a **separate Supabase project** — not merged into LEVERAGE's database. The services are independent bounded contexts with different security models (async vs sync, RLS vs no RLS, dual-engine vs single). Merging would couple their failure domains and compliance postures. Additionally, TRACE switches to **named schemas** consistent with the LEVERAGE pattern:

```
TRACE Supabase project (new, provisioned in Phase 1A)
├── trace schema            ← operational tables (cases, providers, documents, etc.)
├── trace_phi schema        ← PHI store (clients table + phi_map, pgcrypto encrypted)
├── public schema           ← unused, kept for Supabase compatibility
└── Storage                 ← trace-medical-records bucket (private)
```

**`.env.local` configuration:**

```env
# TRACE operational database
TRACE_DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?options=-c%20search_path%3Dtrace

# Separate PHI store connection
TRACE_PHI_DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres?options=-c%20search_path%3Dtrace_phi

# Clerk (platform standard — shared across TrueVow services)
CLERK_SECRET_KEY=sk_live_...
CLERK_PUBLISHABLE_KEY=pk_live_...
```

**Why not merge into LEVERAGE's database:**
- Different security models: TRACE has RLS + dual-engine + HIPAA PHI store; LEVERAGE has none of these
- Different operational profiles: TRACE processes PHI-laden medical records; LEVERAGE processes rules-engine logic
- Failure isolation: a TRACE OCR job OOM should not affect LEVERAGE's rule evaluation
- Compliance scope: TRACE's HIPAA audit boundary should be minimal — merging expands the audit surface to include LEVERAGE's non-PHI data
- Schema naming consistency: both services use named schemas (`leverage`, `trace`, `trace_phi`) within their own projects — same pattern, separate instances

**Schema migration update required:** The first Alembic migration (`0001_initial_schema.py`) must create the `trace` schema and set `search_path` before creating tables. Current migration creates tables in `public` — this must be updated. The PHI store migration creates the `trace_phi` schema in a separate migration run against the PHI database URL.

---

## 26. DeepSeek V4 Pro Memory Sizing — Required Before Phase 1D

**Risk:** The ADR's compute estimate of ~$3/month for "combined DeepSeek + OpenMed + deepdoctection" assumes CPU inference on a small Fly.io machine. DeepSeek V4 Pro is a large model. If the required quantization level demands a large-memory machine, actual compute cost could be materially higher than estimated — potentially $50–200/month rather than $3. Fly.io does not offer GPU instances. This must be validated before billing reconciliation is built.

**Required benchmark before Phase 1D billing reconciliation job:**

| Step | Task |
|------|------|
| 1 | Select the quantized variant of DeepSeek V4 Pro to be used (e.g., 4-bit GPTQ, 8-bit AWQ, or FP16). Document the quantization method and Hugging Face model ID |
| 2 | Measure peak memory usage during inference on a representative billing reconciliation workload (CPT-to-MDM comparison on 50 de-identified clinical note excerpts) |
| 3 | Determine the minimum Fly.io machine size that fits: total memory needed = DeepSeek V4 Pro model + OpenMed models + deepdoctection models + FastAPI runtime + OS overhead |
| 4 | Benchmark inference latency at that machine size. Target: under 10 seconds per billing discrepancy evaluation for interactive QA use; under 60 seconds if billing reconciliation runs as a background job |
| 5 | Decision gate: |
|   | If DeepSeek V4 Pro fits on a performance-2x (4GB RAM, shared CPU) or smaller → proceed with current estimate. Compute cost ~$3–12/month |
|   | If DeepSeek V4 Pro requires a performance-4x (8GB RAM) or larger → update the consolidated cost estimate in §21. Compute cost may be $50–200/month |
|   | If latency is unacceptable at the required machine size → evaluate whether billing reconciliation runs as a background job (where latency doesn't matter) or whether a smaller model (e.g., a fine-tuned 7B variant) is sufficient for the structured CPT-to-MDM comparison task. The `--benchmark` hook in §13.2 supports this comparison |
|   | If no variant of DeepSeek V4 Pro fits on any Fly.io machine size → the model cannot be self-hosted on Fly.io. Re-evaluate using Azure OpenAI (BAA-covered) for production billing reconciliation, or run DeepSeek V4 Pro on a separate dedicated inference server within the air-gap boundary |

This benchmark does not block Phase 1A–1C. It must complete before Phase 1D begins. The decision gate output updates the billing reconciliation section of the Technical Spec and the §21 cost estimate.
