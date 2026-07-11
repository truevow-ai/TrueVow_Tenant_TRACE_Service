# ADR-003 — TRACE Phase 1C Architecture Plan
## Provider Confirmation, Fax Transmission, Client Upload, OCR Spike

**Status:** Ready for Phase 1C Build  
**Date:** July 2026  
**Supersedes:** Nothing — extends ADR-001 and ADR-002  
**Prerequisite reading:** ADR-001, ADR-002, TRACE PRD §5.1–§5.4, TRACE Technical Implementation Spec §4.3–§4.5a, §5.1b  
**Phase 1B status:** Complete — 37/37 tests passing

**Three OCR/NLP tool recommendations from July 2026 research:**
1. Tier 2 OCR escalation: LlamaParse replaced by **Mistral OCR 4 self-hosted** as preferred (no BAA, air-gapped)
2. Clinical NLP: OpenMed stays for Phase 1C; **BioClinical ModernBERT** added as Phase 1D long-context backend (8,192-token window vs OpenMed's 512)
3. Docling (IBM, Apache 2.0, 61k GitHub stars) evaluated for Phase 1D digital PDF Tier 1 — no Phase 1C action

**Full stack audit findings (July 2026) — three changes from prior ADRs:**
4. **Billing LLM: DeepSeek V4 Pro self-hosted → Azure OpenAI GPT-4o-mini** — DeepSeek V4 Pro requires a 4-GPU cluster (minimum 31M tokens/day breakeven). TRACE processes ~1-2.5M tokens/month at early access. Self-hosting is not economically rational. Azure OpenAI GPT-4o-mini has automatic HIPAA BAA under Microsoft DPA and costs ~$0.50/month at TRACE's token volume.
5. **Fax vendor: Documo selected (quality-first)** — HITRUST CSF certification, inbound IDP for document classification, 99.8% delivery rate, purpose-built healthcare confirmation infrastructure. iFax eliminated on transmission quality (below clinical document standard on independent testing). Fax.Plus retained in FaxService abstraction as fallback only.
6. **Auth: Clerk via @truevow/auth-client — no migration.** Clerk is a three-domain platform architecture with shared libraries (`auth-client`, `rbac-engine`, `security-utils`), CSM impersonation, cross-domain service-to-service token exchange, and platform operators who are not firm-scoped. Supabase Auth has no equivalent for these. TRACE consumes the shared `@truevow/auth-client` ClerkWrapper — it never imports Clerk packages directly. AuthContext abstraction wraps the ClerkWrapper for testability and isolation.

---

## 1. What Phase 1C Builds

Phase 1C is the first phase that touches real providers. After Phase 1C, an attorney can:

1. See a provider list populated from the intake record using real OpenMed NER
2. Confirm, edit, and add providers through the portal UI
3. Approve the outgoing request list
4. Watch TRACE send HIPAA-compliant fax requests to confirmed providers
5. Give clients a secure upload link to submit documents directly

The handwriting accuracy spike also lives in Phase 1C and must complete **before Phase 1D OCR pipeline build begins**.

**Five deliverables in build order:**

```
1. OpenMed NER — replaces Phase 1B stub
   (real provider extraction from intake transcript text)

2. Provider confirmation UI
   (checklist, confidence taxonomy, confirm gate, Checkpoint 1)

3. Fax request generation
   (HIPAA cover sheet PDF, signed HIPAA auth attached)

4. Fax transmission via selected vendor API
   (Checkpoint 2, delivery webhook, follow-up scheduler)

5. Client secure upload link
   (POST /upload-link + GET/POST /upload/{token} + minimal page)
```

**Handwriting accuracy spike — between Deliverable 1 and Phase 1D:**
Benchmark deepdoctection + DocTr against real handwritten clinical notes before the Phase 1D OCR pipeline is built. The result of the spike determines which Tier 2 OCR escalation path is activated. See §4.

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

| Layer | Tool | Status | Change from prior ADR |
|-------|------|--------|-----------------------|
| Provider NER | OpenMed (replace stub) | Phase 1C Deliverable 1 | No change |
| Fax transmission | **Fax.Plus Enterprise, Documo, or iFax** | Decision gate — must be locked before fax endpoints built | iFax added as third candidate |
| Client upload | Secure link + minimal page | Phase 1C Deliverable 5 | No change |
| Tier 1 OCR (all docs) | deepdoctection + DocTr | Spike in Phase 1C, build in Phase 1D | No change |
| Tier 2 OCR (handwriting) | **Mistral OCR 4 self-hosted** (preferred) or LlamaParse (fallback) | Spike result determines which | LlamaParse demoted to fallback |
| Long-context NLP | BioClinical ModernBERT | Phase 1D evaluation — not Phase 1C | New addition |
| Digital PDF OCR | Docling (IBM) | Phase 1D evaluation — not Phase 1C | New addition |
| Billing LLM (Phase 1D) | **Azure OpenAI GPT-4o-mini** | Phase 1D deliverable | Changed from DeepSeek V4 Pro self-hosted |
| Signing | DocuSeal self-hosted | Already deployed Phase 1B | Confirmed — no alternative is stronger |
| Auth | Clerk via @truevow/auth-client | Platform standard — three-domain architecture | No direct Clerk imports in TRACE. AuthContext wraps ClerkWrapper. |
| Database + Storage | Supabase | Already deployed | No change |
| Hosting | Fly.io | Already deployed | No change |

---

---

## 4. Full Stack Audit Updates — Three Changes from Prior ADRs

### 4a. Fax Vendor Decision — Documo Selected (Quality-First Evaluation)

**Decision: Documo.**

Price was removed as the evaluation criterion. On quality alone across three dimensions — transmission quality, delivery reliability, and inbound processing — Documo wins clearly for TRACE's specific use case.

**Three quality dimensions evaluated:**

**1. Transmission quality (outbound record requests):**
Independent hands-on testing confirms iFax Standard carries heavier grey background artifacts and more pronounced fine-detail loss than competitors, and does not match Fax.Plus Normal output on clinical documents even at its highest HD+ tier. For TRACE's outbound HIPAA authorization and cover sheet faxes, poor transmission quality means providers cannot read the authorization — the request fails.

Ranking: Fax.Plus ≥ Documo > iFax

**2. Delivery reliability and confirmation infrastructure:**
Documo reports a 99.8% delivery rate with automatic retries on failed transmissions, real-time delivery confirmation, and a status trail per fax. In healthcare and legal work, whether a fax actually went through is a compliance question, not just a UX question. Documo's confirmation layer is purpose-built for this. TRACE's follow-up scheduler at day 10, 20, 25, and 30 depends entirely on accurate delivery status data — a silently failed fax means the attorney waits 30+ days before knowing the request never arrived.

Ranking: Documo ≈ Fax.Plus > iFax

**3. Inbound document processing (medical records arriving via fax):**
This is where Documo separates from both competitors. Documo's AI-powered IDP (Intelligent Document Processing) classifies inbound faxes, extracts structured metadata, and routes documents. Fax.Plus and iFax deliver a raw PDF to TRACE's inbound webhook — no classification, no metadata, no routing. For TRACE, Documo's IDP reduces the volume of misfiled documents, junk faxes, and spam that TRACE's OpenMed pipeline has to process. It does not replace TRACE's de-identification and clinical NLP pipeline, but it filters noise before that pipeline runs.

Ranking: Documo >> Fax.Plus ≈ iFax

**Documo's decisive credential: HITRUST CSF certification.**
HITRUST is the framework many hospital systems require from vendors before accepting their fax transmissions. When TRACE sends record requests to large hospital systems on behalf of PI attorneys, Documo's HITRUST certification reduces friction at those providers. Fax.Plus has SOC 2 Type II + ISO 27001. iFax has SOC 2 Type II + ISO 27001 (Pro plan). Neither carries HITRUST.

**iFax removed from consideration.** Transmission quality below both competitors on clinical documents. No HITRUST certification. No inbound IDP.

**Fax.Plus vs Documo — why Documo:**
Fax.Plus Enterprise is optimized for general enterprise at scale — 190+ country coverage, 20+ data residency regions, SSO, the only MCP server integration among fax vendors. These are features TRACE does not need at early access in the US. Fax.Plus's quality advantages (global carrier network, data residency options) become relevant at Phase 4+ GA scale. Documo's advantages (HITRUST, IDP, healthcare-native delivery confirmation) are relevant on Day 1.

**Decision: Documo. BAA execution is production-only — not now. Configure Documo sandbox credentials immediately.**

```python
# FaxService factory — simplified to two vendors
# iFax removed (quality below threshold for clinical documents)

def create_fax_service() -> FaxService:
    provider = os.environ["FAX_PROVIDER"]
    match provider:
        case "documo":
            return DocumoService(api_key=os.environ["FAX_API_KEY"])
        case "faxplus":
            # Retained as fallback if Documo API integration has blockers
            # Re-evaluate at Phase 4+ GA scale when global coverage matters
            return FaxPlusService(api_key=os.environ["FAX_API_KEY"])
        case _:
            raise ValueError(
                f"Unknown FAX_PROVIDER: '{provider}'. "
                f"Must be 'documo' or 'faxplus'. "
                f"Failing loudly — misconfigured fax vendor "
                f"in production is a HIPAA breach risk."
            )
```

**Set `FAX_PROVIDER=documo` in Fly.io secrets. Default to Documo. Fax.Plus retained in abstraction as fallback only.**

---

### 4b. Billing Reconciliation LLM — DeepSeek V4 Pro Self-Hosted → Azure OpenAI GPT-4o-mini

**This is the most significant correction from the full stack audit.**

ADR-001 and ADR-002 specified DeepSeek V4 Pro self-hosted within the Fly.io HIPAA boundary as the production LLM for billing reconciliation. Research confirms this is not economically viable at TRACE's token volume.

**Why DeepSeek V4 Pro self-hosting is wrong at TRACE's scale:**

DeepSeek V4 Pro is a 1.6 trillion total parameter MoE model (49B active parameters). Self-hosting requires a minimum 4-GPU cluster. The breakeven point where self-hosting costs less than API access is approximately 31–36 million tokens/day on budget INT4 quantization with spot pricing.

TRACE's billing reconciliation token volume at early access: approximately 200 cases × 5,500 tokens = 1.1 million tokens/month. That is roughly 37,000 tokens/day — 0.1% of the breakeven threshold. Self-hosting a 4-GPU cluster for 37,000 tokens/day is the engineering equivalent of renting a warehouse to store one box.

**Corrected production LLM for billing reconciliation:**

Azure OpenAI GPT-4o-mini:
- HIPAA BAA: automatic under Microsoft Data Protection Addendum for EA/MCA/CSP customers — no separate BAA process
- Cost at TRACE early access volume: ~$0.50/month ($0.15/M input + $0.60/M output, ~1.1M tokens/month)
- Already in the LLMService abstraction as the dev/staging backend — promoting to primary production
- No infrastructure to manage — serverless API call

**DeepSeek V4 Flash via API** (not self-hosted) is the cost comparison candidate:
- $0.14/M input, $0.28/M output — roughly 60% cheaper than GPT-4o-mini
- Available via HIPAA-aligned inference providers (DeepInfra: SOC 2 + ISO 27001 certified, zero retention on inference)
- OpenAI-compatible API — drops into LLMService with a base_url change
- Add as `LLM_SERVICE_PROVIDER=deepseek_api` option in LLMService factory for cost benchmarking in Phase 1D

**Updated LLMService factory:**

```python
def create_llm_service() -> LLMService:
    provider = os.environ.get("LLM_SERVICE_PROVIDER", "azure_openai")
    match provider:
        case "azure_openai":
            # Primary production — automatic HIPAA BAA, ~$0.50/month at early access
            return AzureOpenAIService(
                endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
                deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
            )
        case "deepseek_api":
            # Cost comparison — 60% cheaper, HIPAA-aligned provider required
            # Use DeepInfra or similar provider with SOC 2 + zero retention
            return DeepSeekAPIService(
                base_url=os.environ["DEEPSEEK_API_BASE_URL"],
                api_key=os.environ["DEEPSEEK_API_KEY"],
                model="deepseek-v4-flash",
            )
        case "anthropic":
            # Dev/testing only — Claude Sonnet 4.6 BAA requires separate activation
            return AnthropicService(api_key=os.environ["ANTHROPIC_API_KEY"])
        case _:
            raise ValueError(
                f"Unknown LLM_SERVICE_PROVIDER: '{provider}'. "
                f"Must be 'azure_openai', 'deepseek_api', or 'anthropic'. "
                f"Failing loudly — misconfigured LLM in production "
                f"will produce wrong billing reconciliation output."
            )
```

**Note on `deepseek_api` option:** DeepSeek V4 Pro self-hosted is removed from the factory. If DeepSeek is used, it is via API through a HIPAA-aligned inference provider — not self-hosted on Fly.io. The Privacy Officer sign-off requirement from ADR-002 §14 (Fix 6) applies to any DeepSeek API provider: confirm their BAA terms before activating in production.

---

### 4c. DocuSeal and Clerk — Confirmed, No Phase 1C Action

**DocuSeal (electronic signing):** Full market scan confirms DocuSeal is the best self-hosted option. DocuSeal provides the best developer experience among open-source options with exceptional API documentation, HIPAA compliance confirmed, SOC 2 + ISO 27001 certified, and the only alternative (Documenso) lacks confirmed HIPAA compliance. **DocuSeal stays. No alternative warranted.**

**Authentication: Clerk via @truevow/auth-client — no migration.** The TrueVow platform uses a three-domain Clerk architecture (PLATFORM_OPERATORS, SALES_SUPPORT, TENANTS) with shared libraries (`auth-client`, `rbac-engine`, `security-utils`), CSM impersonation (App1→App3), cross-domain service-to-service token exchange, and platform operators who are not firm-scoped. Supabase Auth has no equivalent for any of these. A migration would require rebuilding multi-domain trust, impersonation, and cross-domain token exchange — months of work, not a day.

**TRACE does not import Clerk directly.** It consumes the shared `@truevow/auth-client` library (`ClerkWrapper`) that every TrueVow service imports. Do not add `@clerk/nextjs` or `@clerk/backend` to TRACE's dependencies. Import from `@truevow/auth-client` only.

**AuthContext abstraction wraps the ClerkWrapper** — `AuthContext(user_id, firm_id, role, permissions)` is populated from the ClerkWrapper in `get_auth_context()`. Every TRACE service consumes `AuthContext`, never raw Clerk objects. This is for testability and isolation — not for future migration.

```python
# Every endpoint — AuthContext from ClerkWrapper, never raw Clerk
async def confirm_providers(
    case_id: UUID,
    auth: AuthContext = Depends(get_auth_context),
    provider_service: ProviderService = Depends(get_provider_service),
) -> ProviderConfirmationResponse:
    return await provider_service.confirm_and_lock_provider_list(
        case_id=case_id,
        firm_id=auth.firm_id,
        attorney_id=auth.user_id,
    )
```

---

## 5. Handwriting Accuracy Spike — Protocol and Decision Gate

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

## 6. Deliverable 1 — OpenMed NER Replacing Phase 1B Stub

The Phase 1B stub reads structured provider references from the Benjamin intake JSON. Phase 1C replaces this with real OpenMed NER running on the full intake transcript text. Target: OpenMed 1.7.x (pinned — 1.7.0 added source spans and multimodal de-identification primitives needed for TRACE).

**What the NER pipeline must extract:**

| Entity type | Examples from PI intake transcripts |
|------------|-------------------------------------|
| Healthcare organizations | "Cedars-Sinai ER", "Valley Chiropractic", "Northridge Physical Therapy" |
| Physician names | "Dr. Sarah Chen", "Dr. Michael Torres" |
| Geographic references | "the hospital on Sepulveda", "the urgent care near my office" |
| Treatment references | "they did an X-ray", "I've been doing physical therapy twice a week" |
| Procedure references | "MRI last Tuesday", "they gave me a cortisone shot" |

**Store per provider candidate:**
- `source_quote` — verbatim excerpt from intake transcript (e.g. "I went straight to Cedars-Sinai ER")
- `source_offset` — character offset range in transcript for traceability
- `extraction_source` — `INTAKE_NER` for OpenMed, `INTAKE_STRUCTURED` for stub fields
- `model_version` — OpenMed version used (e.g. "1.7.2") for audit trail

**Critical rule — NPI match is not authorization to fax:**

NPI lookup enriches candidates. It does not authorize a fax. A CONFIRMED match means the provider exists in the public CMS registry. It does not mean the client received treatment there, the fax number is current, or the attorney has approved the request.

The mandatory sequence is:

```
OpenMed NER extraction → candidate created
           ↓
NPI lookup → confidence label assigned (CONFIRMED / LIKELY_MATCH / etc.)
           ↓
Attorney reviews checklist — explicitly confirms each provider (Checkpoint 1)
           ↓
Attorney approves outgoing request list (Checkpoint 2)
           ↓
Fax transmitted
```

**No fax may be sent on the basis of NPI lookup alone.** The Checkpoint 1 gate and the Checkpoint 2 `hipaa_auth_status = SIGNED` check enforce this in code. The `source_quote` field shown per provider in the checklist reminds the attorney exactly what the client said that led to each provider candidate — so the attorney can judge whether the match is correct.

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

## 7. Deliverable 2 — Provider Confirmation UI (Checkpoint 1)

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

## 8. Deliverable 3 — Fax Request Generation

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

## 9. Deliverable 4 — Fax Transmission (Checkpoint 2)

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

## 10. Deliverable 5 — Client Secure Upload Link

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

## 11. Phase 1C Acceptance Criteria

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

## 12. Decisions Locked for Phase 1C

| Decision | What it is | Why locked |
|----------|-----------|------------|
| Checkpoint 1 enforced at API | No fax without confirmed provider list | HIPAA: cannot send authorization until attorney verifies who is receiving it |
| Checkpoint 2 enforced at API | No fax without SIGNED hipaa_auth_status | HIPAA: cannot send PHI to a third party without the client's signed authorization |
| NPI match does not authorize fax | NPI enriches candidates only — attorney confirmation required | A misdirected fax to the wrong provider is a PHI transmission to an unauthorized recipient |
| Clerk via @truevow/auth-client — no direct Clerk imports in TRACE | Three-domain platform architecture with shared libs, CSM impersonation, cross-domain tokens | No Supabase Auth equivalent exists for these capabilities |
| OpenMed pinned to 1.7.x | `openmed>=1.7.0,<1.8.0` in requirements.txt | 1.7.0 added source spans and multimodal de-ID primitives needed by TRACE |
| NLP_PROVIDER_BACKEND=openmed | Explicit env var, never inferred | Misconfigured NLP backend silently produces wrong provider extraction |
| NLP_LONG_CONTEXT_BACKEND=disabled | Disabled in Phase 1C | BioClinical ModernBERT is Phase 1D — not Phase 1C scope |
| LLM_BACKEND=disabled | No LLM in Phase 1C | No billing reconciliation or QA reasoning needed until Phase 1D |
| LLM_PHI_ALLOWED=false | PHI cannot be sent to any LLM in Phase 1C | No LLM provider BAA is confirmed for Phase 1C scope |
| FaxService abstraction with loud failure | `FAX_PROVIDER` env var, no silent fallback | Misconfigured fax vendor in production must fail loudly — a fax sent to the wrong provider with PHI is a HIPAA breach |
| Client upload page has no TRACE branding | Firm name only | Client does not need to know what software the attorney uses |
| Token never logged | case_id logged instead | Upload tokens are the authentication mechanism — logging them creates a credential leak vector |
| Spike must complete before Phase 1D | Handwriting accuracy determines Tier 2 | Phase 1D builds the OCR pipeline. If the wrong Tier 2 tool is assumed during build, the Phase 1D architecture is wrong |

---

## 13. What Phase 1C Does NOT Build

Explicitly out of scope. If you find yourself building these, stop.

- Document OCR processing (Phase 1D)
- Chronology generation (Phase 1D)
- Any flag detection (Phase 1D)
- Billing reconciliation (Phase 1D+)
- Attorney QA interface (Phase 1E)
- Client portal or client accounts (Phase 3+)
- BioClinical ModernBERT integration (Phase 1D) — `NLP_LONG_CONTEXT_BACKEND=disabled` for now
- Docling integration (Phase 1D)
- DeepSeek V4 Pro self-hosted (removed — not viable at TRACE token volume)
- Any LLM call — `LLM_BACKEND=disabled`, `LLM_PHI_ALLOWED=false`

**What Phase 1C DOES add to the data model for Phase 1D readiness:**

The OCR routing fields below are added in Phase 1C as nullable columns. They cost one migration now and save a migration touching all existing records in Phase 1D.

```sql
-- Migration: add_ocr_routing_fields
ALTER TABLE trace.documents ADD COLUMN document_type_guess VARCHAR(50);
ALTER TABLE trace.documents ADD COLUMN page_type_guess VARCHAR(30);
ALTER TABLE trace.documents ADD COLUMN ocr_route VARCHAR(30);
ALTER TABLE trace.documents ADD COLUMN ocr_backend VARCHAR(30);
ALTER TABLE trace.documents ADD COLUMN needs_escalation BOOLEAN DEFAULT FALSE;
ALTER TABLE trace.documents ADD COLUMN source_spans_available BOOLEAN DEFAULT FALSE;
```

All six columns are nullable and default to NULL/FALSE. Phase 1C code never populates them. Phase 1D OCR pipeline populates them. The data model does not assume a single OCR backend.

---

## 14. Tool Evaluation Summary — Full Stack Audit Results

| Tool | Prior spec | Full stack audit finding | Decision | Phase |
|------|-----------|--------------------------|----------|-------|
| Tier 2 OCR (handwriting) | LlamaParse (cloud, BAA required) | Mistral OCR 4 self-hosted: same accuracy class, air-gapped, no BAA | **Switch: Mistral OCR 4 self-hosted preferred. LlamaParse becomes last resort.** | Phase 1C spike |
| Clinical NER (short-context) | OpenMed | OpenMed NER achieves SOTA on 10/12 biomedical benchmarks | **Keep OpenMed** | Phase 1C |
| Clinical NER (long-context) | None | BioClinical ModernBERT: 8,192-token window, 43% better on long-document retrieval vs BioClinicalBERT | **Add as `NLP_LONG_CONTEXT_BACKEND` for Phase 1D flag detection** | Phase 1D |
| Digital PDF OCR Tier 1 | deepdoctection + DocTr | Docling: 97.9% table accuracy, VLM avoids OCR entirely, 30x faster on digital PDFs per IBM | **Evaluate for Phase 1D routing — Docling for digital, DocTr for handwritten** | Phase 1D |
| Billing reconciliation LLM | DeepSeek V4 Pro self-hosted | Requires 4-GPU cluster. Breakeven: 31-36M tokens/day. TRACE processes ~37K tokens/day. Not viable. | **Switch: Azure OpenAI GPT-4o-mini primary. DeepSeek V4 Flash API as cost comparison candidate.** | Phase 1D |
| Electronic signing | DocuSeal self-hosted | DocuSeal: best dev experience among open-source, confirmed HIPAA, SOC 2 + ISO 27001. No alternative stronger. | **Stay with DocuSeal** | Deployed |
| Authentication | Clerk | All TrueVow products use Clerk. Migrating TRACE alone splits attorney identity across two auth systems. Not viable. | **Clerk is the permanent platform standard. No migration.** | Deployed |
| Fax vendor | Fax.Plus Enterprise vs Documo | Quality-first evaluation: Documo wins on HITRUST CSF, inbound IDP, 99.8% delivery rate. iFax eliminated — transmission quality below clinical document standard on independent testing. Fax.Plus retained as abstraction fallback only. | **Documo selected. `FAX_PROVIDER=documo`.** | Phase 1C gate |
| Database + Storage | Supabase | No alternative practical at this stage | **Stay with Supabase** | Deployed |
| Application hosting | Fly.io | No alternative at this stage | **Stay with Fly.io** | Deployed |

---

*ADR-003 — July 2026. Updated with full stack audit findings July 9, 2026. OCR/NLP research: Mistral OCR 4 (June 23, 2026), BioClinical ModernBERT (June 2025), Docling (January 2026). Full stack audit: fax vendor (Documo selected on quality — HITRUST CSF, inbound IDP, 99.8% delivery rate; iFax eliminated on transmission quality; Fax.Plus retained as abstraction fallback), billing LLM (DeepSeek V4 Pro self-hosted removed, Azure OpenAI GPT-4o-mini primary), DocuSeal and Clerk confirmed. Decisions in §12 are locked for Phase 1C. Tool evaluations in §14 are recommendations — agent flags any deviation in PR description.*
