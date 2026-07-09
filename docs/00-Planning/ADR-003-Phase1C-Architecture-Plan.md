# ADR-003 — TRACE Phase 1C Architecture Plan
## Provider Confirmation, Fax Transmission, Client Upload, OCR Spike

**Status:** Ready for Phase 1C Build  
**Date:** July 2026  
**Supersedes:** Nothing — extends ADR-001 and ADR-002  
**Prerequisite reading:** ADR-001, ADR-002, TRACE PRD §5.1–§5.4, TRACE Technical Implementation Spec §4.3–§4.5a, §5.1b  
**Phase 1B status:** Complete — 37/37 tests passing

**Six tool recommendations updated from July 2026 research:**

1. **OpenMed v1.7.0** (released July 1 2026) adds multimodal document intake, OCR adapters, and FHIR/HL7 de-ID. Phase 1C uses provider NER from intake transcript only. Phase 1D unlocks multimodal.
2. **Fax vendor reopened** — SRFax ($12.60/mo HIPAA, developer libraries) now primary candidate. Documo ($25/mo) backup. Fax.Plus ($79.99) fallback. Sandbox bake-off required before vendor lock.
3. **Mistral OCR 4** self-hosted preferred Tier 2 OCR — treat as preferred candidate, not guaranteed dependency. Only if license/deployment/PHI boundary confirmed. LlamaParse fallback with BAA for flagged pages only.
4. **Client provider confirmation link** — tokenized page for clients to confirm/reject/add providers before attorney lock. Not a client portal. One-page confirmation only.
5. **Inbound fax intake skeleton** — receive/store raw PDFs in Phase 1C, no OCR until Phase 1D.
6. **Docling** (IBM, Apache 2.0) and **BioClinical ModernBERT** evaluated in Phase 1D, not Phase 1C. Placeholder env vars added now.

---

## 1. What Phase 1C Builds

Phase 1C is the first phase that touches real providers. After Phase 1C, an attorney can:

1. See a provider list populated from the intake record using real OpenMed NER
2. Confirm, edit, and add providers through the portal UI
3. Approve the outgoing request list
4. Watch TRACE send HIPAA-compliant fax requests to confirmed providers
5. Give clients a secure upload link to submit documents directly

The handwriting accuracy spike also lives in Phase 1C and must complete **before Phase 1D OCR pipeline build begins**.

**Seven deliverables in build order:**

```
1. OpenMed NER (v1.7.0) — replaces Phase 1B stub
   (real provider extraction from intake transcript text,
    store model_version + source_span + source_quote)

2. NPI candidate matching + confidence labels
   (throttled lookup, exponential backoff, Confirmed/Likely/Review taxonomy)

3. Client provider confirmation link (new — see §3a)
   (tokenized page, confirm/reject/add providers, not a client portal)

4. Provider confirmation UI
   (checklist, confidence taxonomy, confirm gate, Checkpoint 1)

5. Fax vendor sandbox bake-off (preq to transmission)
   (SRFax primary, Documo backup, Fax.Plus fallback. Send/receive/status/BAA)

6. Fax request generation + transmission
   (HIPAA cover sheet PDF, Checkpoint 2, delivery webhook, configurable follow-up)

7. Inbound fax intake skeleton (new — see §6a)
   (receive raw PDF, store in Supabase, create document row, notify attorney)

8. Client secure upload link
   (POST /upload-link + GET/POST /upload/{token} + minimal page)

9. Handwriting accuracy spike (gates Phase 1D)
   (DocTr baseline + Mistral OCR 4 if self-host confirmed + LlamaParse fallback)
```

---

## 2. Research Findings — What Changed Since the Spec Was Written

Before building Phase 1C, three tool evaluations are worth doing. The research below is the basis for each recommendation. These are not blocking changes — they are informed upgrades to consider before the build begins.

### Finding 1 — Mistral OCR 4 Released June 23, 2026

Mistral OCR 4 is the most significant development for the TRACE OCR pipeline since the spec was written. Released two weeks ago with bounding boxes (paragraph-level coordinates for every text block), 170-language support, and a 74% win rate over Mistral OCR 3 on handwriting and forms.

**Benchmark result from May 2026 independent evaluation:**
Mistral OCR, LlamaParse, and Claude Sonnet 4.6 all performed similarly well on complex document types, all outperforming Textract Structured on handwritten notes and messy forms. Mistral OCR was evaluated at $2/1,000 pages (50% batch discount available: $1/1,000 pages).

**Why this matters for the handwriting spike:** Mistral OCR 4 is purpose-built for handwriting, forms, and messy scans — exactly the document types that PI medical records produce (ER notes, chiropractic intake forms, PT progress notes). The self-hosted deployment option means PHI never leaves the Fly.io HIPAA boundary.

**Pricing comparison at early access volume (200 cases × 300 pages = 60,000 pages/month):**
- deepdoctection + DocTr: $0 per page (self-hosted compute ~$1-3/month)
- Mistral OCR 4 (API): $2/1,000 pages = **$120/month** at standard pricing; $60/month with batch API
- Mistral OCR 4 (self-hosted): Fly.io compute only — no per-page cost, similar to DocTr

**Recommendation:** Keep deepdoctection + DocTr as Tier 1 (air-gapped, zero cost). If the handwriting spike fails (DocTr below 80% on handwritten notes), **use Mistral OCR 4 self-hosted as Tier 2 instead of LlamaParse**. Mistral OCR 4 self-hosted keeps PHI in the Fly.io boundary with no BAA needed. LlamaParse is a cloud API that requires a BAA and sends PHI externally. Self-hosted Mistral OCR 4 is the superior choice when self-hosting is feasible.

**Updated OCR_CLOUD_BACKEND values:**

| Value | Tool | When used | PHI boundary |
|-------|------|-----------|-------------|
| `none` | DocTr only | Default (handwriting spike passes) | Air-gapped |
| `mistral_local` | Mistral OCR 4 self-hosted | Spike fails, prefer air-gap | Air-gapped |
| `llamaparse` | LlamaParse API | Spike fails, Mistral self-host not feasible | External (BAA required) |

---

### Finding 2 — BioClinical ModernBERT is the New State-of-the-Art for Clinical NER

BioClinical ModernBERT (released June 2025, updated July 2026) achieves state-of-the-art performance on four of five clinical NLP benchmarks including de-identification (DEID F1: 83.8%) and social history NER (58.5% F1). It is built on ModernBERT's 8,192-token context window — critical for processing full multi-page medical records, not just individual sentences.

The existing OpenMed models are trained on MIMIC-III and PubMed corpora. BioClinical ModernBERT is pretrained on 53.5 billion tokens from the largest biomedical and clinical corpus to date, incorporating 20 datasets.

**Context window comparison — this matters for TRACE:**

| Model | Context window | Relevance |
|-------|---------------|-----------|
| OpenMed NER models | ~512 tokens (BERT-based) | Processes sentence by sentence — misses cross-sentence context |
| BioClinical ModernBERT | 8,192 tokens | Processes full clinical notes in one pass — captures document-level context |

For provider extraction (identifying "referred to Dr. Sarah Chen at Cedars-Sinai" from a 400-word intake transcript), 512 tokens is sufficient. For flag detection across multi-page chronologies (T2-02 changing incident descriptions across providers), 8,192 tokens per document enables cross-page context that 512-token models cannot achieve.

**Recommendation:** Do not replace OpenMed in Phase 1C — it is already stubbed, tested, and deployed. Instead, evaluate BioClinical ModernBERT as a **complementary model** for the two tasks where long context matters most:
1. Cross-record flag detection (T2-02, T2-03, T2-04) in Phase 1D
2. Full-document de-identification where entity boundaries span sentences

Add an `NLP_LONG_CONTEXT_BACKEND` environment variable pointing to BioClinical ModernBERT for long-context tasks, while OpenMed handles sentence-level NER and de-identification. Both models are Apache 2.0 / open weights, self-hosted, zero BAA required.

---

### Finding 3 — Docling (IBM) Now Production-Grade at 37,000 GitHub Stars

Docling was donated to the Linux Foundation AI & Data Foundation in early 2026, surpassed 37,000 GitHub stars, and shipped Granite-Docling-258M (Apache 2.0, January 2026) — a production VLM that avoids traditional OCR entirely by using a vision-language model trained on 81,000 manually labeled pages.

**IBM's claim:** "Avoiding OCR reduces errors and speeds up time-to-solution by 30 times." The VLM path processes digital PDFs without Tesseract or DocTr, producing structure-aware Markdown/JSON that preserves tables, reading order, and clinical note structure.

**What Docling is strong at:** Digital-born PDFs with structured layouts — typed clinical notes, lab reports, imaging reports, billing statements. These are the majority of TRACE's document types.

**What Docling is weak at:** Handwritten notes and low-quality scans — it defaults to EasyOCR for those cases, which is weaker than DocTr for medical handwriting.

**Recommendation:** Evaluate Docling as a Phase 1D option for Tier 1 OCR on **digital PDFs only**. The existing deepdoctection + DocTr handles both digital and handwritten. Docling could replace deepdoctection for the digital PDF path with better structure preservation, while DocTr handles handwritten pages. This is a Phase 1D evaluation item, not a Phase 1C change.

---

## 3. Phase 1C Tool Stack (Confirmed)

| Layer | Tool | Status |
|-------|------|--------|
| Provider NER | OpenMed (replace stub) | Phase 1C Deliverable 1 |
| Fax transmission | Fax.Plus Enterprise or Documo | Decision gate from Phase 1B — must be locked |
| Client upload | Secure link + minimal page | Phase 1C Deliverable 5 |
| Tier 1 OCR (all docs) | deepdoctection + DocTr | Spike in Phase 1C, build in Phase 1D |
| Tier 2 OCR escalation (handwriting) | **Mistral OCR 4 self-hosted** (preferred) or LlamaParse (fallback) | Spike result determines which |
| Long-context NLP (Phase 1D+) | BioClinical ModernBERT | Evaluate for Phase 1D flag detection |
| Clinical NER (sentence-level) | OpenMed | Already deployed |

---

## 4. Handwriting Accuracy Spike — Protocol and Decision Gate

**Must complete before Phase 1D OCR pipeline build begins. Does not block Phase 1C deliverables 2–5.**

### Benchmark set

Assemble 30+ de-identified handwritten clinical note pages covering the document types most common in PI cases:

| Document type | Target pages | Why |
|--------------|-------------|-----|
| ER physician notes (cursive, rushed) | 8 pages | Most common first-contact records |
| Chiropractic SOAP notes | 8 pages | Primary treatment records in MVA cases |
| Physical therapy progress notes | 8 pages | High volume, mixed handwriting/printed |
| Urgent care intake forms (handwritten fields) | 6 pages | Checkbox + handwritten hybrid |

All pages must be de-identified (no real patient names, DOBs, or MRNs). Use synthetic data or existing de-identified research datasets.

### Metrics

For each page and each OCR engine tested:
- **Word Error Rate (WER)** — primary accuracy metric
- **Medical term accuracy** — specifically: provider names, medication names, anatomical terms, procedure descriptions
- **Per-page confidence score** — does the engine's self-reported confidence correlate with actual accuracy?

### Decision gate

```
Run benchmark on: deepdoctection + DocTr
                  Mistral OCR 4 self-hosted
                  (LlamaParse if Mistral self-host not feasible)

DocTr WER on handwritten pages:
  ≥ 80% word accuracy  → Proceed with DocTr-only (Tier 1 sufficient)
                          OCR_CLOUD_BACKEND = none
  65–79% word accuracy → Activate Tier 2 cloud escalation
                          Evaluate: Mistral OCR 4 self-hosted vs LlamaParse
                          Pick based on accuracy delta and PHI boundary preference
                          OCR_CLOUD_BACKEND = mistral_local or llamaparse
  < 65% word accuracy  → Mistral OCR 4 self-hosted (or LlamaParse) mandatory
                          DocTr accuracy insufficient even with 70% threshold
                          OCR_CLOUD_BACKEND = mistral_local (preferred) or llamaparse
```

### If Mistral OCR 4 self-hosted is selected

Deploy Mistral OCR 4 on a Fly.io GPU-enabled machine (if available) or high-memory CPU machine. No external API calls — PHI stays in Fly.io HIPAA boundary. No BAA needed beyond Fly.io. Cost: Fly.io compute only.

Self-hosted model deployment:
```python
# Using Mistral's self-hosted deployment option
# Model: mistral-ocr-4 weights via Mistral's enterprise self-host program
# OR: use mistral-ocr-latest API with Mistral's EU data residency + BAA
# Mistral offers self-hosted deployment for organizations with PHI requirements
```

### If LlamaParse is selected (cloud fallback)

LlamaParse requires:
- BAA with LlamaIndex (execute before Phase 1D begins)
- Individual flagged pages only — not full documents
- PHI-level pages pass through LlamaParse; confirmed by the OpenMed de-ID output before the page is sent

LlamaParse pricing at escalation volume: if 20% of 60,000 pages/month are escalated = 12,000 pages × $0.003/page = ~$36/month. Negligible.

---

## 5. Deliverable 1 — OpenMed NER Replacing Phase 1B Stub

The Phase 1B stub reads structured provider references from the Benjamin intake JSON. Phase 1C replaces this with real OpenMed NER running on the full intake transcript text.

**What the NER pipeline must extract:**

| Entity type | Examples from PI intake transcripts |
|------------|-------------------------------------|
| Healthcare organizations | "Cedars-Sinai ER", "Valley Chiropractic", "Northridge Physical Therapy" |
| Physician names | "Dr. Sarah Chen", "Dr. Michael Torres" |
| Geographic references | "the hospital on Sepulveda", "the urgent care near my office" |
| Treatment references | "they did an X-ray", "I've been doing physical therapy twice a week" |
| Procedure references | "MRI last Tuesday", "they gave me a cortisone shot" |

**Confidence assignment after NPI lookup:**

The NPI lookup result determines the confidence label shown to the attorney:

```python
def assign_confidence_label(npi_results: list[NpiResult], ner_confidence: float) -> str:
    """
    Translates NPI lookup result count + NER confidence into attorney-actionable label.
    These are the labels the attorney sees and acts on — not internal scores.
    """
    if len(npi_results) == 0:
        return "DO_NOT_REQUEST"       # no NPI found — attorney must add manually
    elif len(npi_results) == 1 and ner_confidence >= 0.85:
        return "CONFIRMED"            # single match, high NER confidence
    elif len(npi_results) == 1 and ner_confidence < 0.85:
        return "LIKELY_MATCH"         # single match but low NER confidence
    elif 2 <= len(npi_results) <= 3:
        return "NEEDS_CLIENT_CONFIRMATION"  # multiple candidates
    else:
        return "NEEDS_STAFF_REVIEW"   # too many candidates to auto-select
```

**What the attorney sees per provider in the checklist:**

```
┌──────────────────────────────────────────────────────────────┐
│ ✅ CONFIRMED                                                  │
│ Cedars-Sinai Medical Center                                  │
│ Emergency Department · 8700 Beverly Blvd, Los Angeles, CA   │
│ NPI: 1234567890 · Fax: (310) 423-8000                       │
│ Source: "I went straight to Cedars-Sinai ER" (intake)        │
│                                         [Edit] [Remove]      │
├──────────────────────────────────────────────────────────────┤
│ ⚠️ NEEDS CLIENT CONFIRMATION                                 │
│ Dr. Sarah Chen — 3 matches found                             │
│ ○ Sarah Chen MD, Internal Medicine, Los Angeles              │
│ ○ Sarah Chen DO, Family Medicine, Burbank                    │
│ ○ Sarah T. Chen MD, Orthopedics, Santa Monica                │
│ Please ask the client which Dr. Chen they saw.               │
│                                    [Ask Client] [Add Manual] │
└──────────────────────────────────────────────────────────────┘
```

---

## 6. Deliverable 2 — Provider Confirmation UI (Checkpoint 1)

**This is Checkpoint 1.** No fax is sent until the attorney explicitly confirms the provider list. This is enforced at the API level — the fax transmission endpoint checks for a confirmation timestamp before accepting any request.

**UI requirements:**

- Checklist shows all providers with their confidence label and source quote from the intake transcript
- Attorney can: Confirm, Edit (any field), Remove, Add new provider
- "Add new provider" searches NPI Registry live as the attorney types
- Provider list is locked after confirmation — no edits without explicit "unlock" action (logged to audit_log)
- Confirmation action shows a summary: "You are confirming 4 providers. Record requests will be sent to these providers after you approve the outgoing request list in the next step."
- Confirmation is logged: attorney_id, timestamp, full provider list snapshot

**Checkpoint 1 gate in the API:**

```python
@router.post("/cases/{case_id}/providers/confirm")
async def confirm_provider_list(case_id: UUID, ...):
    providers = await provider_service.get_providers(case_id, firm_id)
    
    confirmed = [p for p in providers if p.status == "CONFIRMED"]
    if not confirmed:
        raise HTTPException(400, detail={
            "message": "At least one provider must be confirmed before proceeding.",
            "code": "NO_CONFIRMED_PROVIDERS"
        })
    
    # Lock the list and timestamp
    await provider_service.lock_provider_list(case_id, attorney_id=current_user.id)
    
    # Log Checkpoint 1 completion
    await audit_logger.log(
        action="PROVIDER_LIST_CONFIRMED",
        resource_type="CASE",
        resource_id=case_id,
        details={"confirmed_provider_count": len(confirmed), 
                 "provider_ids": [str(p.id) for p in confirmed]}
    )
    
    return {"status": "locked", "confirmed_count": len(confirmed)}
```

---

## 7. Deliverable 3 — Fax Request Generation

**Pre-condition:** Checkpoint 1 complete (provider list confirmed and locked).

**What each fax request contains:**

```
HIPAA-Compliant Medical Records Request

TO:     [Provider Name and Facility]
        [Provider Fax Number]

FROM:   [Attorney Name], [Firm Name]
        [Return Fax Number — TRACE dedicated inbound]
        [Attorney Phone — for provider questions]

RE:     Medical Records Request — TRACE Case Ref: [CASE_REFERENCE]
        (This reference number is opaque — no client PII)

PATIENT: [Client Full Name]
         Date of Birth: [DOB]
         Date of Incident: [Incident Date]
         Dates of Service Requested: [From Date] through [Through Date]

RECORDS REQUESTED:
  ☐ Emergency room records
  ☐ Imaging reports and films
  ☐ Physical therapy notes
  ☐ Billing records
  ☐ Pharmacy records
  ☐ All other records related to the above dates of service

Enclosed: Signed HIPAA Authorization (see attached)

[Attorney Bar Number] · [Firm Address] · [Firm Phone]
```

**HIPAA authorization attachment:** Retrieved from Supabase Storage `signed-documents` bucket by `signed_documents.signed_pdf_storage_key`. Appended to the fax as a second page. The authorization covers this specific attorney and firm — it was signed by the client via DocuSeal.

**PDF generation:** Use `reportlab` or `weasyprint` for the cover sheet. Keep it simple — plain text, no TRACE branding. The cover sheet is a legal document, not a marketing piece.

---

## 8. Deliverable 4 — Fax Transmission (Checkpoint 2)

**This is Checkpoint 2.** Attorney approves the outgoing request list before any fax is sent.

**Request preview before sending:**

The attorney sees a table showing exactly what will be sent:

```
┌────────────────────────────────────────────────┬─────────────────┬──────────┐
│ Provider                                        │ Fax Number      │ Records  │
├────────────────────────────────────────────────┼─────────────────┼──────────┤
│ Cedars-Sinai Medical Center ER                 │ (310) 423-8000  │ ER + Billing│
│ Valley Chiropractic Center                     │ (818) 555-1234  │ All records │
│ Northridge Physical Therapy                    │ (818) 444-5678  │ PT notes  │
└────────────────────────────────────────────────┴─────────────────┴──────────┘

[Send 3 Requests →]    [Go Back to Edit Provider List]
```

**Checkpoint 2 gate:**

```python
@router.post("/cases/{case_id}/requests/send")
async def send_record_requests(case_id: UUID, ...):
    case = await get_case_scoped(case_id, firm_id)
    
    # Enforce Checkpoint 2 gate
    if case.provider_list_status != "LOCKED":
        raise HTTPException(403, detail={
            "message": "Provider list must be confirmed before sending requests.",
            "code": "PROVIDER_LIST_NOT_CONFIRMED"
        })
    
    if case.hipaa_auth_status != "SIGNED":
        raise HTTPException(403, detail={
            "message": "Client must sign the HIPAA authorization before records can be requested.",
            "code": "HIPAA_AUTH_NOT_SIGNED"
        })
    
    # Send faxes to all LOCKED providers
    results = await fax_service.send_batch_requests(case_id=case_id)
    
    # Log Checkpoint 2
    await audit_logger.log(
        action="RECORD_REQUESTS_SENT",
        resource_type="CASE",
        resource_id=case_id,
        details={"provider_count": len(results), 
                 "fax_ids": [r.fax_id for r in results]}
    )
    
    return {"sent": len(results), "results": results}
```

**Follow-up scheduler:**

Add a background job that runs daily and checks for non-respondent providers:

```python
async def run_followup_scheduler():
    """
    Day 10: send automated follow-up fax
    Day 20: send second follow-up fax
    Day 25: notify attorney via portal — list of non-respondents
    Day 30: escalation flag in portal — attorney selects action per provider
    """
    cases_with_pending = await db.get_cases_with_pending_providers()
    
    for case in cases_with_pending:
        for provider in case.pending_providers:
            days_since_request = (today() - provider.last_request_sent).days
            
            if days_since_request == 10:
                await fax_service.send_followup(provider, followup_number=1)
            elif days_since_request == 20:
                await fax_service.send_followup(provider, followup_number=2)
            elif days_since_request == 25:
                await notify_portal(case.firm_id, case.case_id,
                    f"Provider {provider.name} has not responded after 25 days.")
            elif days_since_request >= 30:
                await flag_escalation(case.case_id, provider.provider_id)
```

**FaxService abstraction — confirms both vendor APIs are wrapped identically:**

```python
class FaxService(ABC):
    @abstractmethod
    async def send(self, to_fax: str, pdf_bytes: bytes, case_ref: str) -> FaxResult:
        ...
    
    @abstractmethod
    async def get_delivery_status(self, fax_id: str) -> FaxStatus:
        ...

class FaxPlusService(FaxService):
    # Fax.Plus Enterprise API implementation
    ...

class DocumoService(FaxService):
    # Documo API implementation
    ...

def create_fax_service() -> FaxService:
    provider = os.environ["FAX_PROVIDER"]
    if provider == "faxplus":
        return FaxPlusService(api_key=os.environ["FAX_API_KEY"])
    elif provider == "documo":
        return DocumoService(api_key=os.environ["FAX_API_KEY"])
    else:
        raise ValueError(f"Unknown FAX_PROVIDER: {provider}. Must be 'faxplus' or 'documo'.")
        # Fail loudly — never silently fall back to a different provider
```

---

## 9. Deliverable 5 — Client Secure Upload Link

Specified in Spec §4.5a. No changes from spec. Building now that the document upload UI exists in the portal.

**Three endpoints:**

```
POST /api/v1/trace/cases/{case_id}/upload-link
  Auth: Clerk JWT
  Body: { "expires_hours": 48, "label": "Please upload your ER discharge papers" }
  Returns: { "upload_url": "https://truevow.law/upload/{token}", "expires_at": "..." }

GET  /upload/{token}         — no auth, static page (firm name + label + upload area)
POST /upload/{token}         — no auth, multipart upload, triggers dedup + OCR jobs
DELETE /api/v1/trace/cases/{case_id}/upload-link/{token}  — attorney revokes early
```

**Non-negotiable UX rules for the static upload page:**
- Works as a camera button on mobile — `<input type="file" accept="image/*,application/pdf" capture="environment">`
- Only elements: firm name, attorney label, upload area, submit button
- After upload: "Thank you. Your documents have been received by [Firm Name]." — nothing else
- No TRACE branding. No navigation. No account prompt. No TRACE logo.
- Token never logged — log case_id only

**Source provenance:** Documents uploaded via this path get `source = "CLIENT_UPLOAD"` and trigger the deduplication job per Spec §5.1b.

---

## 10. Phase 1C Acceptance Criteria

All must pass before Phase 1D begins.

### 10.1 OpenMed NER

- [ ] Provider extraction produces candidates from a 10-transcript test set (no NPI stub — real OpenMed NER)
- [ ] Confidence labels correctly assigned: CONFIRMED / LIKELY_MATCH / NEEDS_CLIENT_CONFIRMATION / NEEDS_STAFF_REVIEW / DO_NOT_REQUEST
- [ ] Source quote from intake transcript shown per provider in checklist
- [ ] Zero providers extracted → single DO_NOT_REQUEST record with note, attorney notified

### 10.2 Provider Confirmation (Checkpoint 1)

- [ ] Checklist shows all providers with confidence labels and intake source quotes
- [ ] Attorney can confirm, edit, remove, add providers
- [ ] "Add new" searches NPI Registry live
- [ ] Confirmation locks list and timestamps with attorney_id
- [ ] Attempting to advance to fax step without confirmation returns 400
- [ ] Confirmation logged in audit_log with full provider list snapshot

### 10.3 Fax Request Generation

- [ ] Generated PDF contains all required fields (client name, DOB, incident date, dates of service, signed HIPAA auth attached)
- [ ] HIPAA authorization retrieved from signed-documents bucket and appended correctly
- [ ] Case reference number on cover sheet is opaque (no client name or PII in reference)
- [ ] Cover sheet contains no TRACE branding — attorney name and firm name only

### 10.4 Fax Transmission (Checkpoint 2)

- [ ] Preview table shows all providers with fax numbers before send
- [ ] Checkpoint 2 gate blocks transmission if provider_list_status != LOCKED
- [ ] Checkpoint 2 gate blocks transmission if hipaa_auth_status != SIGNED
- [ ] Delivery webhook updates provider retrieval_status to REQUESTED
- [ ] Failed transmission flagged for attorney attention with retry option
- [ ] Follow-up scheduler fires at day 10, 20, 25, 30 for non-respondent providers
- [ ] All transmissions logged in audit_log with fax_id and timestamp

### 10.5 Client Upload Link

- [ ] POST /upload-link creates upload_links record and returns URL
- [ ] GET /upload/{token} returns upload page with firm name + attorney label
- [ ] Upload page works on mobile as camera button
- [ ] POST /upload/{token} stores file in Supabase Storage with source=CLIENT_UPLOAD
- [ ] Post-upload: dedup job fires, attorney portal notification fires
- [ ] Expired token returns 410 Gone (not 401)
- [ ] Revoked token returns 410 Gone
- [ ] Token never appears in any log entry

### 10.6 Handwriting Accuracy Spike

- [ ] 30-page benchmark set assembled (de-identified, covers ER notes, chiro SOAP, PT notes, urgent care forms)
- [ ] deepdoctection + DocTr benchmarked: per-page WER and medical term accuracy recorded
- [ ] Mistral OCR 4 self-hosted (or LlamaParse) benchmarked on same set
- [ ] Decision gate applied and documented: OCR_CLOUD_BACKEND value locked
- [ ] If Tier 2 selected: BAA executed (if LlamaParse) or Mistral OCR 4 deployed (if self-hosted)
- [ ] Spike results shared in PR — not just a decision, a data-backed decision

---

## 11. Decisions Locked for Phase 1C

| Decision | What it is | Why locked |
|----------|-----------|------------|
| Checkpoint 1 enforced at API | No fax without confirmed provider list | HIPAA: cannot send authorization until attorney verifies who is receiving it |
| Checkpoint 2 enforced at API | No fax without SIGNED hipaa_auth_status | HIPAA: cannot send PHI to a third party without the client's signed authorization |
| FaxService abstraction with loud failure | `FAX_PROVIDER` env var, no silent fallback | Misconfigured fax vendor in production must fail loudly — a fax sent to the wrong provider with PHI is a HIPAA breach |
| Client upload page has no TRACE branding | Firm name only | Client does not need to know what software the attorney uses |
| Token never logged | case_id logged instead | Upload tokens are the authentication mechanism — logging them creates a credential leak vector |
| Spike must complete before Phase 1D | Handwriting accuracy determines Tier 2 | Phase 1D builds the OCR pipeline. If the wrong Tier 2 tool is assumed during build, the Phase 1D architecture is wrong |

---

## 12. What Phase 1C Does NOT Build

Explicitly out of scope. If you find yourself building these, stop.

- Document OCR processing (Phase 1D)
- Chronology generation (Phase 1D)
- Any flag detection (Phase 1D)
- Billing reconciliation (Phase 1D+)
- Attorney QA interface (Phase 1E)
- Client portal or client accounts (Phase 3+)
- BioClinical ModernBERT integration (evaluate for Phase 1D)
- Docling integration (evaluate for Phase 1D)

---

## 13. Tool Evaluation Summary — July 2026 Research

| Tool | Current spec | Research finding | Recommendation |
|------|-------------|-----------------|---------------|
| Tier 2 OCR (handwriting) | LlamaParse | Mistral OCR 4 self-hosted preferred — treat as candidate, not guaranteed. License/deployment/PHI boundary must be confirmed. | **Mistral OCR 4 if self-host confirmed. LlamaParse BAA fallback for flagged pages only.** |
| Clinical NER | OpenMed stub | OpenMed v1.7.0 released July 1 2026. Store model_version, source_spans, extraction_source. | **Pin to OpenMed 1.7.x for Phase 1C provider extraction. Phase 1D unlocks multimodal.** |
| Fax vendor | Fax.Plus Enterprise or Documo | SRFax $12.60/mo HIPAA with developer libraries. Documo $25/mo. Fax.Plus $79.99. | **Sandbox bake-off: SRFax primary, Documo backup, Fax.Plus fallback. Send/receive/status/BAA evaluation.** |
| Provider confirmation | Attorney-only UI | Client confirmation reduces missing-provider risk. One-page tokenized link, no portal. | **Add client confirmation link before attorney lock.** |
| Inbound fax | Not designed for Phase 1C | Operational failure if no inbound handling. Store raw PDFs now. | **Inbound fax intake skeleton in Phase 1C. No OCR until Phase 1D.** |
| Digital PDF OCR | deepdoctection + DocTr | IBM Docling (Apache 2.0) for digital PDFs. BioClinical ModernBERT for long-context NER. | **Both Phase 1D evaluation candidates. Placeholder env vars added now.** |
| Handwriting OCR | deepdoctection + DocTr | DocTr baseline + Mistral OCR 4 candidate + LlamaParse fallback | **Spike gates Phase 1D per §19 of ADR-002.** |

---

## 14. Phase 1C Absorbed Changes Summary

The following were absorbed from the July 2026 architecture review:

| Change | Impact |
|--------|--------|
| SRFax as primary fax candidate | $12.60/mo vs $79.99. Sandbox bake-off before Phase 1C transmission |
| Client provider confirmation link | Reduces missing-provider risk. Tokenized page, no portal, no accounts |
| Inbound fax intake skeleton | Receives raw PDFs, stores in Supabase, creates document rows. No OCR |
| OpenMed 1.7.0 pinning | Store model_version, source_span, source_quote, extraction_source |
| Configurable follow-up schedule | Defaults: day 10, 20, 25, 30 — stored as config, not hardcoded |
| Mistral OCR 4 caveat | Preferred candidate, not guaranteed dependency. Self-hosting/licensing unconfirmed |
| NLP_LONG_CONTEXT_BACKEND=disabled | BioClinical ModernBERT evaluated in Phase 1D |

---

*ADR-003 — July 2026. Research refreshed July 9, 2026. SRFax pricing verified June 2026 (FaxRadar). OpenMed v1.7.0 released July 1 2026. Mistral OCR 4 released June 23 2026. Decisions in §11 are locked for Phase 1C.*
