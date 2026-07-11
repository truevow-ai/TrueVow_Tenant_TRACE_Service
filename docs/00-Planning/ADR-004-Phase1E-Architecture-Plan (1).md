# ADR-004 — TRACE Phase 1E Architecture Plan
## Case Readiness Board, Tier 2 Flags, Billing Reconciliation, Export

**Status:** Ready for Phase 1E Build  
**Date:** July 2026  
**Supersedes:** Nothing — extends ADR-001 through ADR-003  
**Prerequisite reading:** ADR-001, ADR-002, ADR-003, TRACE PRD §5.5–§5.7, §6, Spec Part 5–7  
**Phase 1D status:** Complete — 43/43 tests passing  
**Handwriting spike:** Framework complete, 30 real images ready. Real WER numbers required before Tier 2 OCR escalation is wired in. OCR_CLOUD_BACKEND must be locked before Phase 1E D2 begins.

---

## 1. What Phase 1E Builds

Phase 1E completes the attorney-facing workflow. After Phase 1E, an attorney can:

1. Open the Case Readiness Board and see at a glance what is missing, pending, received, and reviewed across all five columns
2. See Tier 2 NLP flags surfaced alongside Tier 1 flags with cross-record context
3. Review billing reconciliation — bills matched against clinical records with confidence tiers
4. Export a demand-ready chronology as PDF with disclaimer on every page or as structured JSON
5. Track lien status manually through the Liens column

Phase 1E also evaluates BioClinical ModernBERT as the long-context NLP backend for Tier 2 flag detection. If it outperforms OpenMed on cross-record tasks (the primary use case for Tier 2), it replaces OpenMed for those specific tasks only.

**Five deliverables in build order:**

```
1. Case Readiness Board UI
   (five columns, four statuses each, liens table, next-action column)

2. Tier 2 NLP flags (T2-01 through T2-06)
   (OpenMed cross-record comparison, or BioClinical ModernBERT
    if evaluation confirms it is better for long-context tasks)

3. Billing reconciliation
   (CPT/ICD extraction from faxed bills, match confidence tiers,
    Azure OpenAI GPT-4o-mini for MDM complexity evaluation)

4. Chronology export
   (PDF with disclaimer on every page, structured JSON)

5. BioClinical ModernBERT evaluation
   (benchmark against OpenMed on Tier 2 flag detection tasks,
    lock NLP_LONG_CONTEXT_BACKEND before Phase 1E D2 begins)
```

---

## 2. Pre-Phase-1E Gates

Both must be confirmed before any Phase 1E code is written.

**Gate 1 — Handwriting spike WER numbers locked**

The spike framework exists. The 30 images exist. deepdoctection+DocTr must be installed and run against the real images. `OCR_CLOUD_BACKEND` must be locked based on actual WER, not the stub value.

If this has not happened: install deepdoctection, run the spike, report WER per image, apply the decision gate, set `OCR_CLOUD_BACKEND` in Fly.io secrets. Phase 1E D2 (Tier 2 flags) cannot begin until this is done because the Tier 2 flag pipeline depends on the OCR pipeline being correctly configured.

**Gate 2 — Phase 1D verifications confirmed**

Four tests from the Phase 1D verification pass:
- `test_raw_ocr_text_never_stored` — raw PHI never in any DB column or log
- `test_demand_ready_gate_uses_priority_not_type` — gate checks `flag_priority` not `flag_type`
- `test_case_list_contains_no_client_names` — matter number only in list view
- `test_source_citation_loads_correct_page` — signed URL ≤900 seconds

All four must pass before Phase 1E begins.

---

## 3. Deliverable 1 — Case Readiness Board

The Case Readiness Board is the primary attorney-facing UX for TRACE. It answers one question: *what is missing, what is received, what needs review, and what blocks demand preparation?*

**Five columns, four statuses each:**

| Column | Missing | Requested | Received | Reviewed |
|--------|---------|-----------|---------|---------|
| **Providers** | No providers confirmed | Provider list sent for confirmation | Providers confirmed and locked | Provider list reviewed by attorney |
| **Records** | Records not yet requested | Requests sent, awaiting response | Records received in case file | Records reviewed in chronology |
| **Bills** | No billing records | Bills requested | Bills received | Bills reconciled |
| **Liens** | Not checked | Lien inquiry sent | Lien documentation received | Lien reviewed by attorney |
| **Review Flags** | Flags detected, none annotated | Some flags annotated | All flags annotated | Demand-ready approved |

**What the attorney sees when they open a case:**

```
Matter #1042 — Case Readiness

┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│  Providers   │   Records    │    Bills     │    Liens     │ Review Flags │
├──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│  ✅ Reviewed  │ 📨 Requested │ ⚠️ Missing   │ ❓ Not Checked│ 🔴 3 unread  │
│  4 confirmed │ 2 of 4 rcvd  │              │              │              │
└──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘

Next Action: Review 2 received records → confirm bills are missing
             → check lien status → annotate 3 priority flags

SOL: 612 days — Standard SOL Estimate  [Confirm deadline reviewed]
```

**Next Action column logic:**

The board surfaces one prioritized next action per case. The priority order is fixed:

```python
def get_next_action(case: Case) -> str:
    """
    Returns the single highest-priority action the attorney
    should take on this case right now.
    Order is fixed — never show a later step when an earlier
    step is incomplete.
    """
    if case.hipaa_auth_status != "SIGNED":
        return "Waiting for client signature"
    if case.provider_list_status != "LOCKED":
        return f"Review provider list ({case.unconfirmed_provider_count} need attention)"
    if case.has_unreviewed_records:
        return f"Review {case.unreviewed_record_count} received records"
    if case.has_unannotated_priority_flags:
        return f"Annotate {case.priority_flag_count} priority flags"
    if case.lien_status == "NOT_CHECKED":
        return "Check lien status"
    if case.sol_attorney_confirmed_at is None:
        return "Confirm SOL estimate reviewed"
    if case.case_stage != "DEMAND_READY":
        return "Mark demand ready when review is complete"
    return "Demand ready"
```

**Liens table — Phase 1E schema addition:**

```sql
CREATE TABLE trace.liens (
    lien_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id        UUID NOT NULL REFERENCES trace.cases(case_id)
                   ON DELETE CASCADE,
    firm_id        UUID NOT NULL,
    lien_type      VARCHAR(30) NOT NULL,  -- MEDICARE / MEDICAID / ERISA /
                                          -- WORKERS_COMP / HEALTH_INSURANCE / OTHER
    lienholder     TEXT,
    claimed_amount DECIMAL(12,2),
    status         VARCHAR(20) NOT NULL DEFAULT 'NOT_CHECKED',
    notes          TEXT,
    created_at     TIMESTAMPTZ DEFAULT NOW(),
    updated_at     TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_lien_status CHECK (status IN (
        'NOT_CHECKED', 'REQUESTED', 'RECEIVED', 'REVIEWED'
    ))
);
```

Liens are attorney-managed. TRACE does not detect liens automatically — that is Tier 3 (attorney judgment only). The Liens column surfaces the status the attorney sets. TRACE's job is ensuring liens are not overlooked before demand.

**SOL confirmation fields — already on the model, surface in Phase 1E:**

```
sol_attorney_confirmed_at  — timestamp when attorney confirmed
sol_attorney_confirmed_by  — attorney user_id
```

Show on the board: "SOL: 612 days — Standard SOL Estimate [Confirm deadline reviewed]"
After confirmation: "SOL: 612 days ✅ Confirmed [date] by [attorney name]"

---

## 4. Deliverable 2 — Tier 2 NLP Flags (T2-01 through T2-06)

Tier 2 flags require OpenMed cross-record comparison — not single-note processing. They operate on the complete set of chronology entries for a case, comparing entities across providers and over time. This is where BioClinical ModernBERT's 8,192-token context window matters: OpenMed's 512-token window processes entries sentence by sentence and cannot see across page breaks.

**BioClinical ModernBERT evaluation (before T2 flags are built):**

See §5 for the full evaluation protocol. Run the evaluation first. The result determines which model runs the Tier 2 detection pass.

**Six Tier 2 flags per PRD §5.5.3:**

**T2-01 New Provider Without Referral Context (ADVISORY)**
Track provider introduction events. For providers introduced after the first encounter: check preceding 30 days for referral entity naming that provider or specialty. No referral found and not ER/urgent care: ADVISORY flag.

**T2-02 Changing Incident Description Across Providers (PRIORITY)**
Extract mechanism of injury from first 1–2 entries per provider (ER note, initial intake note, first PT note). Compare across providers. Fundamentally different mechanism: PRIORITY flag. Show verbatim excerpts side by side.

**T2-03 Changing Symptom Complaints Without Progression Logic (ADVISORY)**
Extract body region and symptom entities across all chronology entries. Track primary complaint region over time. New body region appears as primary complaint with no clinical progression explanation: ADVISORY flag.

**T2-04 Pre-Existing Condition Signal (PRIORITY)**
Two modes depending on attorney opt-in for pre-incident records:
- All cases: string match + NER on post-incident notes for prior condition language ("pre-existing", "degenerative", "chronic", "prior history of", "old injury")
- Opted-in cases: full pre/post body region comparison across chronology

**T2-05 Functional Impact Tagging (INFORMATIONAL — not a blocking flag)**
Tag entries containing work restrictions, ADL limitations, ROM measurements, pain scores, future care language. These support the damages calculation. Show as green tags in the QA interface. Filter option: "Show functional impact entries only."

**T2-06 Imaging Cross-Reference Links (INFORMATIONAL — not a blocking flag)**
For each T1-03 follow-up match where an imaging order was detected: check whether an imaging report exists in the set within 90 days. If found: create a cross-reference link between the ordering entry and the imaging report. Show as linked entries in the QA interface.

**Processing job structure:**

```python
async def run_tier2_flags(case_id: UUID) -> None:
    """
    Runs after all Tier 1 flags are complete and the full
    chronology is assembled. Operates on redacted text only.
    Uses long-context NLP backend (BioClinical ModernBERT
    or OpenMed, depending on evaluation result).
    """
    assert_production_for_phi()

    backend = os.environ.get("NLP_LONG_CONTEXT_BACKEND", "disabled")
    if backend == "disabled":
        logger.info("NLP_LONG_CONTEXT_BACKEND=disabled — Tier 2 flags skipped")
        return

    chronology = await load_full_chronology_redacted(case_id)

    await detect_t2_01_new_provider_no_referral(chronology, case_id)
    await detect_t2_02_changing_incident_description(chronology, case_id)
    await detect_t2_03_changing_symptom_complaints(chronology, case_id)
    await detect_t2_04_preexisting_condition_signal(chronology, case_id)
    await tag_t2_05_functional_impact(chronology, case_id)
    await link_t2_06_imaging_cross_references(chronology, case_id)
```

**Alert fatigue mitigation:**

Tier 2 NLP flags have inherent false positive risk. Three mitigations built in:

1. ADVISORY flags (T2-01, T2-03) do not block the demand-ready gate — they surface for awareness without requiring annotation
2. INFORMATIONAL tags (T2-05, T2-06) are positive — they add value without creating friction
3. Per PRD §13 risk table: if any Tier 2 flag type exceeds 30% false positive rate in early access data, that flag type is demoted to INFORMATIONAL or disabled pending model retraining

Track false positive rate per flag type from attorney annotation data: if attorney dismisses a flag type as "not relevant" consistently, that is the signal.

---

## 5. Deliverable 3 — Billing Reconciliation

**Scope — what Phase 1E builds:**

TRACE owns the `medical_bill_line` table (decided in ADR-001 Decision #17 — medical data stays in medical context). Billing data arrives via faxed billing statements processed through the OCR pipeline. The billing repo integration (original Q11 in PRD §12) remains deferred pending prerequisites.

**Two-step reconciliation process:**

**Step 1 — CPT/ICD extraction from faxed billing documents:**

```python
async def extract_billing_lines(document_id: UUID) -> list[BillingLine]:
    """
    Extract billing line items from OCR output of faxed billing statements.
    Uses regex + lookup table for CPT/ICD codes — no LLM for extraction.
    LLM is only used for MDM complexity evaluation (Step 2).
    """
    ocr_text = await load_redacted_ocr_text(document_id)

    # CPT code pattern: 5-digit code with optional modifier
    cpt_pattern = r'\b(\d{5})(-\d{2})?\b'
    # ICD-10 pattern: letter + 2 digits + optional dot + more
    icd_pattern = r'\b([A-Z]\d{2}\.?\d*)\b'
    # Date of service: various formats
    date_pattern = r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b'

    # ... extraction logic ...

    return billing_lines
```

**Step 2 — Match billing lines against chronology entries:**

```python
BILLING_MATCH_CONFIDENCE = {
    "STRONG_MATCH":           "Date + provider + CPT all match a chronology entry",
    "LIKELY_MATCH":           "Date + provider match, CPT differs or absent",
    "POSSIBLE_MATCH":         "Date matches, provider differs or absent",
    "NO_MATCHING_TREATMENT":  "Billing line has no corresponding chronology entry",
    "TREATMENT_WITH_NO_BILL": "Chronology entry has no corresponding billing line",
    "NEEDS_REVIEW":           "Ambiguous — multiple potential matches",
}
```

**LLM use — Azure OpenAI GPT-4o-mini for MDM complexity only:**

```python
async def evaluate_mdm_complexity(
    cpt_code: str,
    clinical_note_redacted: str,
) -> MdmEvaluation:
    """
    Evaluates whether clinical documentation supports the
    medical decision-making (MDM) complexity level implied
    by the billed E&M CPT code (99213, 99214, etc.).

    Uses Azure OpenAI GPT-4o-mini — BAA automatic under
    Microsoft DPA. LLM_PHI_ALLOWED must be true in production.

    Input: REDACTED clinical note only — no raw PHI.
    The LLM sees redacted text with PHI tokens ([NAME], [DATE]).
    """
    assert os.environ.get("LLM_PHI_ALLOWED") == "true", (
        "LLM_PHI_ALLOWED must be explicitly set to 'true' before "
        "billing reconciliation processes any clinical text. "
        "Confirm Azure OpenAI BAA is active."
    )
    # ... LLM call ...
```

**Prohibited output strings apply to all LLM billing output:**

Every LLM response goes through the prohibited string filter before any DB write. No clinical interpretation, no causation language, no case value language may appear in billing reconciliation output.

**medical_bill_line table:**

```sql
CREATE TABLE trace.medical_bill_line (
    bill_line_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id          UUID NOT NULL REFERENCES trace.cases(case_id)
                     ON DELETE CASCADE,
    firm_id          UUID NOT NULL,
    document_id      UUID NOT NULL REFERENCES trace.documents(document_id),
    provider_id      UUID REFERENCES trace.providers(provider_id),
    date_of_service  DATE,
    cpt_code         VARCHAR(10),
    icd10_codes      TEXT[],
    billed_amount    DECIMAL(12,2),
    match_confidence VARCHAR(30),
    matched_entry_id UUID REFERENCES trace.chronology_entries(entry_id),
    needs_review     BOOLEAN DEFAULT FALSE,
    attorney_note    TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_match_confidence CHECK (match_confidence IN (
        'STRONG_MATCH', 'LIKELY_MATCH', 'POSSIBLE_MATCH',
        'NO_MATCHING_TREATMENT', 'TREATMENT_WITH_NO_BILL', 'NEEDS_REVIEW'
    ))
);
```

---

## 6. Deliverable 4 — Chronology Export

**Two export formats:**

**PDF export — disclaimer on every page:**

```python
EXPORT_DISCLAIMER = (
    "ATTORNEY WORK PRODUCT — PRIVILEGED AND CONFIDENTIAL\n"
    "This chronology was generated by TRACE and reviewed by the "
    "attorney of record. It organizes factual records for attorney "
    "review and does not constitute medical advice, clinical "
    "interpretation, causation opinion, injury severity assessment, "
    "or case valuation. The attorney is responsible for all legal "
    "judgments made in reliance on this document."
)
```

Disclaimer appears:
- Cover page — large, above the chronology title
- Footer of every subsequent page — smaller but legible
- Cannot be removed, cannot be suppressed, cannot be reduced below 8pt

PDF structure:
```
Page 1: Cover — Matter reference, attorney name/bar, date exported,
         incident date, SOL estimate with confirmation status,
         full disclaimer
Pages 2+: Chronology entries in date order
         Each entry: date, provider (de-identified display name),
         event type, clinical description, source citation
         Flag annotations shown inline per entry
         Unreviewed entries marked clearly
```

**JSON export — structured for case management system import:**

```json
{
  "trace_export_version": "1.0",
  "exported_at": "2026-07-09T14:23:00Z",
  "matter_reference": "Matter #1042",
  "incident_date": "2024-03-15",
  "sol_estimate": "2026-03-15",
  "sol_table_version": "2026-07-01",
  "sol_attorney_confirmed": true,
  "demand_ready_at": "2026-07-09T14:20:00Z",
  "demand_ready_by": "attorney_uuid",
  "disclaimer": "...",
  "chronology": [
    {
      "entry_id": "uuid",
      "date": "2024-03-15",
      "provider": "Cedars-Sinai Emergency Department",
      "event_type": "Visit",
      "description": "Initial emergency presentation...",
      "source_document": "ER Records - Cedars-Sinai",
      "source_page": 3,
      "review_status": "CONFIRMED",
      "flags": [],
      "functional_impact_tags": ["WORK_RESTRICTION", "PAIN_SCALE"]
    }
  ],
  "flags_summary": {
    "total": 8,
    "priority": 5,
    "advisory": 2,
    "informational": 1,
    "all_priority_annotated": true
  }
}
```

**Export gate — cannot export until demand-ready:**

```python
@router.post("/cases/{case_id}/export")
async def export_chronology(case_id: UUID, format: str, ...):
    case = await get_case_scoped(case_id, firm_id)

    if case.case_stage != "DEMAND_READY":
        raise HTTPException(403, detail={
            "message": "Chronology can only be exported after "
                       "it has been marked demand-ready. "
                       "Please complete your review and approve "
                       "the chronology before exporting.",
            "unannotated_flags": await count_unannotated_priority_flags(case_id)
        })
    # ... generate export ...
```

---

## 7. Deliverable 5 — BioClinical ModernBERT Evaluation

**Why this evaluation exists:**

OpenMed NER has a 512-token context window. It processes chronology entries one at a time and cannot see across entry boundaries. Tier 2 flags require cross-record comparison — T2-02 (changing incident descriptions) needs to compare the ER note from Day 1 against the PT intake note from Week 3. With 512 tokens, these entries cannot be in the same context window.

BioClinical ModernBERT has an 8,192-token context window. It can process an entire 20-entry chronology section in one pass, enabling genuine cross-record entity comparison.

**Evaluation protocol:**

```python
# Before Tier 2 flag detection is built:
# Run this evaluation to determine NLP_LONG_CONTEXT_BACKEND

EVALUATION_TASKS = [
    {
        "task": "t2_02_incident_description",
        "description": "Detect divergent incident descriptions across 2+ providers",
        "test_cases": 20,  # 10 true positives, 10 true negatives
        "metric": "F1 score",
    },
    {
        "task": "t2_04_preexisting_condition",
        "description": "Detect pre-existing condition language in post-incident notes",
        "test_cases": 20,
        "metric": "F1 score",
    },
    {
        "task": "long_doc_retrieval",
        "description": "Match clinical query across 10+ chronology entries",
        "test_cases": 20,
        "metric": "NDCG@10",
    },
]

# Run both models on the same test cases
# Models: openmed-ner-clinical-large vs bioclinical-modernbert
# Compare F1 and NDCG@10 per task

# Decision gate:
# BioClinical ModernBERT wins 2 of 3 tasks → NLP_LONG_CONTEXT_BACKEND=bioclinical_modernbert
# OpenMed wins 2 of 3 tasks → NLP_LONG_CONTEXT_BACKEND=openmed
# Tie → NLP_LONG_CONTEXT_BACKEND=bioclinical_modernbert (8,192-token window is the decisive factor)
```

**Deployment if BioClinical ModernBERT wins:**

BioClinical ModernBERT is a HuggingFace model (Apache 2.0). Download weights to the Fly.io volume alongside OpenMed models. Set `BIOCLINICAL_MODERNBERT_MODEL_BASE` env var. Zero network calls at inference — same air-gap property as OpenMed.

OpenMed stays for PHI de-identification and sentence-level NER. BioClinical ModernBERT handles only the cross-record Tier 2 flag detection tasks.

**If evaluation is not complete before Phase 1E D2 begins:**

Set `NLP_LONG_CONTEXT_BACKEND=disabled`. Tier 2 flags do not run. Surface in the Case Readiness Board as "Tier 2 flag detection pending — contact support." Do not ship Tier 2 flags with a disabled long-context backend without communicating this to early access attorneys.

---

## 8. Phase 1E Acceptance Criteria

All must pass before Phase 1F (load testing + production go-live checklist) begins.

### 8.1 Case Readiness Board

- [ ] Five columns render with correct status per column
- [ ] Status transitions correctly as providers confirmed, records received, flags annotated, liens updated
- [ ] Liens table created and CRUD endpoints working
- [ ] Next Action column shows correct prioritized action per case
- [ ] SOL confirmation flow works: attorney clicks confirm, timestamp + attorney_id stored
- [ ] Board visible from case list with aggregate status per case
- [ ] No client names anywhere in the board or case list

### 8.2 Tier 2 Flags

- [ ] BioClinical ModernBERT evaluation complete with documented F1 scores — `NLP_LONG_CONTEXT_BACKEND` locked
- [ ] All 6 Tier 2 flags detected on test case set
- [ ] T2-02 and T2-04 surface as PRIORITY, T2-01 and T2-03 as ADVISORY, T2-05 and T2-06 as INFORMATIONAL
- [ ] False positive rate tracked per flag type from annotation data
- [ ] ADVISORY flags do not block demand-ready gate
- [ ] INFORMATIONAL tags shown in green, filterable

### 8.3 Billing Reconciliation

- [ ] CPT/ICD extraction from faxed billing statements working
- [ ] Six match confidence tiers assigned correctly
- [ ] `LLM_PHI_ALLOWED=true` gate enforced before any LLM billing call
- [ ] Prohibited string filter runs on all LLM billing output
- [ ] `medical_bill_line` table populated from faxed records
- [ ] Bills summary visible in Case Readiness Board bills column

### 8.4 Export

- [ ] PDF export: disclaimer on cover page AND footer of every page
- [ ] PDF export: only available when `case_stage = DEMAND_READY`
- [ ] PDF export: unreviewed entries clearly marked
- [ ] JSON export: all required fields present per §6 schema
- [ ] Export gate: `403` if case not demand-ready, with count of unannotated flags
- [ ] Export audit log entry written on every export (attorney_id, timestamp, format)

### 8.5 Platform

- [ ] All 43 existing tests still passing
- [ ] `test_raw_ocr_text_never_stored` still passing after billing pipeline runs
- [ ] Handwriting spike WER documented, `OCR_CLOUD_BACKEND` locked

---

## 9. What Phase 1E Does NOT Build

- SETTLE integration (Phase 2)
- Client communication portal (Phase 3)
- Lien resolution letter generation (Phase 2)
- Settlement statement and disbursement (Phase 2 — "CLOSE" product scope)
- Spanish-language signing templates (legal drafting task — not engineering)
- Load testing suite (Phase 1F)
- Production go-live checklist execution (Phase 1F — production-only)

---

## 10. Decisions Locked for Phase 1E

| Decision | What it is | Why locked |
|----------|-----------|------------|
| Liens are attorney-managed | TRACE tracks status, never detects automatically | Lien detection requires legal judgment — Tier 3 only |
| Export blocked until demand-ready | `case_stage = DEMAND_READY` required | Export is the final attorney certification — should not be possible before all flags reviewed |
| Disclaimer on every page, every format | Non-suppressible, non-removable | Every page of a TRACE export could be detached and used in isolation. Every page must carry the disclaimer. |
| LLM_PHI_ALLOWED=true required for billing LLM | Explicit gate, not implied | Billing reconciliation is the first time redacted clinical text goes to an LLM. Explicit opt-in required per Privacy Officer sign-off rule from ADR-002. |
| BioClinical ModernBERT evaluation first | NLP_LONG_CONTEXT_BACKEND locked before Tier 2 build | Tier 2 flags are built against a known backend. Building against "TBD" creates two codepaths to maintain. |
| False positive tracking per flag type | Annotation dismissal data tracked | PRD §13 risk: if any Tier 2 flag type exceeds 30% false positive rate, demote to INFORMATIONAL. Cannot demote without data. |

---

## 11. Phase 1E → Phase 1F Handoff

Phase 1F covers:
- Load testing suite (locust) — target: 100 concurrent fax receipt events, <5s OCR latency
- Production go-live checklist execution (Spec Part 9) — all 6 sections
- First early access attorney onboarding — BAAs signed, templates configured, test case run with support

Phase 1F is when BAAs get signed and PHI enters the system for the first time. Everything before Phase 1F is synthetic data only.

---

*ADR-004 — July 2026. All decisions in §10 are locked for Phase 1E. Evaluation results in §7 determine `NLP_LONG_CONTEXT_BACKEND` value. Agent flags any deviation from locked decisions in PR description.*
