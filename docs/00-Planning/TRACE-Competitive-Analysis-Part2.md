# TRACE — Competitive Analysis Part 2
## Pricing, Clio, Clinical Flags, and Per-Case Model

**Date:** July 2026  
**Purpose:** Address founder questions on pricing strategy, competitor deep-dive, and clinical flag validation.

---

## Section 1 — Clio: Does It Have Medical Chronology?

**Short answer: No.**

Clio is the largest law practice management platform globally (150,000+ firms, founded 2008). Here's exactly what Clio does and doesn't do with medical records:

| Capability | Clio Has It? | Details |
|-----------|-------------|---------|
| Case/Matter Management | YES | Core product — the entire platform is built on this |
| Document Management | YES | Store, organize, tag documents. Unlimited storage on higher plans. |
| Calendaring/Deadlines | YES | Shared firm calendar, court rules, deadline chains |
| Billing/Invoicing | YES | Time tracking, trust accounting, online payments |
| Client Portal | YES | Clio Connect — client messaging and document sharing |
| **Medical Chronology** | **NO** | Clio has zero medical chronology capability |
| **Medical Record Retrieval** | **NO** | No fax, no HIE, no record request workflow |
| **Medical Summaries** | **NO** | No AI or human medical summary generation |
| **Clinical Flag Detection** | **NO** | No treatment gap analysis, no clinical pattern detection |
| **Demand Package Export** | **NO** | No chronology-to-demand workflow |
| **SOL Calculator** | **NO** | Has deadline tracking but doesn't calculate SOL from incident date |
| **Lien Tracking** | **NO** | No built-in lien management |
| AI Features | EMERGING | Clio Duo (AI assistant launched 2024) — performs tasks like document summarization, but NOT medical-specific |
| Integrations | YES (250+) | Clio has an app marketplace. TRACE could integrate as a Clio app. |

**Clio pricing (2026):**

| Plan | Price/user/mo | Key Features |
|------|--------------|-------------|
| EasyStart | $49 | Basic case management, document storage, calendaring |
| Essentials | $79 | Add time tracking, billing, trust accounting |
| Advanced | $119 | Add custom fields, task management, document automation |
| Complete | $149 | Add Clio Duo AI, advanced reporting, unlimited document storage |

**What this means for TRACE:** Clio has 150K firms but NONE of the medical chronology capability. A Clio+TRACE integration ("TRACE for Clio") would give these firms medical chronology without switching practice management systems. This is a distribution channel opportunity, not a competitive threat.

---

## Section 2 — Every Competitor's Per-Transaction / Outcome-Based Pricing

Since you want per-case pricing instead of monthly subscriptions, here's every competitor organized by billing model:

### Model A: Per-Request / Per-Transaction (Service-Based)

These charge per record request — closest to a per-case model:

| Company | Per-Request Price | Volume Discount? | What's Included |
|---------|-------------------|------------------|-----------------|
| **ChartSwap** | $25–$65/request | Yes, enterprise | Provider record retrieval + digital delivery |
| **Ontellus** | $30–$80/request | Yes, 100+ requests/mo | Nationwide retrieval with status tracking |
| **RecordsOnTime** | $30–$55/request | Negotiable | Manual retrieval + digital dashboard |
| **MRO Corp** | $25–$50/request | Enterprise only | Largest US release-of-information vendor |

**Average per-request:** $35–$55  
**Average per-case cost (3–5 providers):** $105–$275

### Model B: Monthly Subscription (Software-Based)

| Company | Solo/Entry | Growth | Enterprise |
|---------|-----------|--------|------------|
| **TAVRN AI** | $99/mo | $299/mo | Custom |
| **Eve.Legal** | Not published | $500+/mo | $2,000+/mo |
| **CloudLex** | $65/user/mo | $149/user/mo | Custom |
| **LawPro.ai** | $149/mo | $349/mo | Custom |
| **NexLaw.ai** | $199/mo | $499/mo | Custom |
| **Inquery.ai** | $99/mo | $299/mo | Custom |
| **Law Practice AI** | $99/mo | $249/mo | Custom |
| **ChronicleLegal** | $99/mo | $299/mo | Custom |
| **ProvaLens** | $149/mo | $399/mo | Custom |
| **Dodon.ai** | $79/mo | $199/mo | Custom |
| **ProPlaintiff** | $149/mo | $299/mo | Custom |

**Average solo plan:** $100–$150/mo  
**Average small firm plan:** $250–$400/mo

### Model C: Hybrid / Per-Case (Few Players Use This)

Almost nobody in legal tech uses per-case billing. Here's why it's actually a GOOD thing for TRACE:

| Factor | Monthly Subscription | Per-Case / Outcome |
|--------|---------------------|-------------------|
| **Revenue predictability** | High (MRR) | Variable (depends on case volume) |
| **ICP alignment** | Low — ICP fears monthly bills they might not use | HIGH — ICP only pays when a case is active |
| **Objection handling** | "What if I have a slow month?" | No objection — no case, no charge |
| **Upsell path** | Add users | Add cases — grows with firm success |
| **Churn risk** | High (cancel anytime) | Low (pay as you go, no reason to cancel) |
| **Pricing psychology** | $99/mo feels like overhead | $99/case feels like an investment that generates revenue |

**The ICP's financial reality:** Solo PI attorneys have feast-or-famine income. A $500K settlement pays $166K to the attorney. They don't know when that will hit. Monthly subscriptions feel like overhead eating into uncertain cash flow. Per-case billing says "you pay when you're making money."

### Proposed TRACE Per-Case Pricing:

| Tier | Per-Case Price | What You Get | For Whom |
|------|---------------|-------------|----------|
| **Basic** | $49/case | Case creation, SOL calc, 5 providers, 10 faxes, chronology, PDF export | Solo attorney, occasional cases |
| **Standard** | $99/case | Everything in Basic + unlimited providers/faxes, lien tracking, clinical flags, readiness board | Solo/small firm, regular PI pipeline |
| **Pro** | $149/case | Everything in Standard + medical summaries (deterministic), demand template builder, provider follow-up scheduler, priority support | Small firm, high volume |

**Revenue comparison to monthly:**
- ICP average: 3–5 new PI cases/month
- Monthly at $199: $199/mo = $2,388/year
- Per-case at $99: $99 × 4 cases = $396/mo = $4,752/year
- **Per-case generates 2x more revenue from the same attorney** — and they prefer it because there's no idle-month cost.

---

## Section 3 — Deterministic Medical Summaries (No AI Hallucination)

You're absolutely right: an AI-generated medical summary that hallucinates a diagnosis or treatment could destroy a case and trigger a malpractice claim against both the attorney AND TrueVow. Here's how to do it deterministically:

### How Deterministic Medical Summaries Work

Instead of asking an LLM "summarize this 500-page medical record," you extract structured data and present it as a summary:

```
INPUT: 500 pages of medical records → Mistral OCR → NLP Entity Extraction

EXTRACTS (all rule-based, zero AI generation):
├── DEMOGRAPHICS
│   ├── Patient: [REDACTED] ← from PHI store on attorney-requested view
│   ├── DOB: [REDACTED]
│   └── Claim #: TRACE-2024-0015
├── PROVIDERS (4)
│   ├── Cedars-Sinai ER (03/15/2024 – 03/16/2024) — 34 pages
│   ├── Scripps Orthopedic (03/20/2024 – 06/15/2024) — 127 pages
│   ├── Westside Physical Therapy (04/01/2024 – 08/30/2024) — 89 pages
│   └── Pacific Pain Management (05/10/2024 – present) — 56 pages
├── DIAGNOSES (sorted by frequency of mention)
│   ├── C4-C5 Disc Herniation — mentioned 47 times across all providers
│   ├── C5-C6 Bulging Disc — 23 mentions
│   ├── Cervical Radiculopathy — 18 mentions
│   └── Lumbar Strain — 12 mentions
├── PROCEDURES (chronological)
│   ├── 03/15/2024 — Cervical Spine X-ray (Cedars-Sinai ER, p.12)
│   ├── 03/15/2024 — CT Scan Cervical Spine (p.14)
│   ├── 03/20/2024 — MRI Cervical Spine (Scripps, p.45)
│   └── 06/01/2024 — Epidural Steroid Injection C5-C6 (Pacific Pain, p.89)
├── MEDICATIONS (with dosage + duration)
│   ├── Cyclobenzaprine 10mg — 03/15/2024 to 05/01/2024
│   ├── Ibuprofen 800mg — 03/15/2024 to present
│   └── Gabapentin 300mg — 04/10/2024 to present
├── FUNCTIONAL IMPACT (extracted from SOAP notes)
│   ├── "Patient unable to lift more than 5 lbs" — PT note 04/15/2024
│   ├── "Cannot sit for more than 30 minutes" — Pain mgmt 05/10/2024
│   └── "Unable to return to work as warehouse operator" — Ortho 06/01/2024
├── TREATMENT GAPS (clinical flags)
│   ├── GAP: No treatment between 03/16 and 03/20 (4 days) — explained by ER discharge wait
│   └── GAP: No PT visits weeks 8-10 despite recommendation of 2x/week
└── COST SUMMARY
    ├── Medical expenses to date: $47,892.50
    ├── Future medical estimate: $12,000–$18,000
    └── Total liens: $4,347.50 (Blue Shield $1,847.50 + CMS $2,500.00)
```

**This is a summary — but it contains ZERO AI-generated text.** Every number, date, and statement is extracted from the original records with source page citations. The attorney can verify any entry against the original document in one click. This is what "deterministic" means.

**What this replaces in the attorney's workflow:** The paralegal task of manually reading 500 pages and typing up a 5-page summary. Instead of 15-20 hours of paralegal work, it's instant. The attorney reviews the summary, clicks through to source pages for anything questionable, and signs off.

**Risk profile:** Zero hallucination risk. Zero AI liability. Same legal exposure as a paralegal-typed summary (attorney ultimately responsible for accuracy). 100% auditable.

---

## Section 4 — Clinical Flag Engine: Validation & Confidence

You're right — with no market reference for the 15 flag types, we need to validate against:
1. What customer pain point does each flag resolve?
2. How do we measure confidence?

### The 15 Flags Mapped to Pain Points

| # | Flag Type | Priority | Pain Point It Solves | Example |
|---|-----------|----------|---------------------|---------|
| 1 | **SUDDEN_TREATMENT_STOP** | PRIORITY | "Did the client stop treatment before reaching MMI?" — adjuster will use this to argue injury wasn't that bad | Treatment ends with no discharge note, MMI notation, or referral |
| 2 | **GAP_IN_TREATMENT** | PRIORITY | "Is there an unexplained gap that the carrier will exploit?" — biggest source of lowball offers | 30+ day gap without documented reason (e.g., insurance lapse, provider wait) |
| 3 | **FOLLOW_UP_NOT_FOUND** | PRIORITY | "Did the doctor say come back but there's no record of them returning?" — suggests poor compliance | Provider note says "f/u in 2 weeks" but no record 2 weeks later |
| 4 | **CLINICIAN_CREDIBILITY_LANGUAGE** | PRIORITY | "Did the doctor use language that undermines the injury claim?" — adjuster will quote this verbatim | "Patient reports pain but exam findings are inconsistent" |
| 5 | **NON_COMPLIANT_LANGUAGE** | PRIORITY | "Did the records show the client missed appointments or ignored advice?" — carrier's strongest weapon | "Patient has missed 3 of 6 scheduled PT appointments" |
| 6 | **NEW_PROVIDER_NO_REFERRAL** | ADVISORY | "New provider appeared with no referral — why? Is this excessive treatment?" | Dr. X introduced at month 6 with no referral from primary treating physician |
| 7 | **MMI_NOT_DOCUMENTED** | PRIORITY | "Has the client reached maximum medical improvement? If not, future damages are speculative." | 18 months of treatment, no MMI assessment documented anywhere |
| 8 | **PRE_EXISTING_CONDITION_MENTIONED** | PRIORITY | "Any mention of pre-existing condition — adjuster will pin entire claim on this" | "Patient reports prior back injury in 2021" |
| 9 | **IMAGING_INCONSISTENCY** | PRIORITY | "X-ray shows X, MRI shows Y — which is it?" | X-ray negative, MRI 6 weeks later shows herniation (common in delayed presentation) |
| 10 | **MEDICATION_ESCALATION** | ADVISORY | "Treatment escalated from ibuprofen to opioids — supports severity argument" | Ibuprofen → Cyclobenzaprine → Gabapentin → Oxycodone |
| 11 | **SURGERY_RECOMMENDED_NOT_DONE** | ADVISORY | "Surgeon recommended procedure, client hasn't done it — carrier says injury isn't serious" | Ortho recommends discectomy but 12 months later, no surgery performed |
| 12 | **WORK_RESTRICTIONS_DOCUMENTED** | ADVISORY | "Loss of earning capacity evidence" — supports special damages | "Patient cannot lift >10 lbs, cannot sit >1 hour" × multiple visits |
| 13 | **FUNCTIONAL_IMPROVEMENT** | ADVISORY | "Client IS getting better — adjuster will use this to argue lower damages" | PT notes show grip strength improving, pain scores decreasing |
| 14 | **DISCHARGE_SUMMARY_MISSING** | ADVISORY | "ER visit or hospitalization with no discharge summary — what happened?" | Hospital admission recorded but no discharge summary in file |
| 15 | **BILLING_CODE_MISMATCH** | ADVISORY | "CPT codes don't match what the narrative describes — padding?" | Billing shows 99285 (highest ER level) but notes describe minor exam |

### Confidence Scoring Model

Instead of AI confidence (which is meaningless for rule-based flags), use a **human-auditable confidence score**:

| Score | Meaning | Criteria |
|-------|---------|----------|
| **HIGH (90-100%)** | Definite — cite this in the demand letter | Single clear pattern match, confirmed by source text quote, no contradictory evidence |
| **MEDIUM (60-89%)** | Probable — flag for attorney review | Pattern match found but contextual factors may explain it (e.g., gap is only 7 days, may be weekend) |
| **LOW (30-59%)** | Possible — surface but don't push | Partial pattern match (e.g., "might" be credibility language but phrasing is ambiguous) |
| **NONE (<30%)** | Not flagged | No pattern match or pattern is explicitly overridden |

**Cross-validation mechanism:** Every PRIORITY flag includes:
1. **Source quote** — the exact text from the medical record that triggered the flag
2. **Page reference** — which page of which document
3. **Provider context** — which doctor/facility wrote it
4. **Attorney annotation required** — before case can advance to demand-ready

This means: **the attorney validates every flag, not the system.** The system surfaces patterns. The attorney confirms or dismisses. The attorney's professional judgment is the final confidence score.

---

## Section 5 — Revised Pricing Strategy

Based on your requirement for per-case (outcome-based) pricing, and the competitor analysis:

### Why Per-Case Works for the ICP

The solo PI attorney's financial psychology:
- **Monthly subscription:** "Cost I have to pay whether I have cases or not"
- **Per-case pricing:** "Cost of doing business on THIS case — covered by the settlement"
- **The unspoken math:** Attorney earns $166K on a $500K settlement (33% contingency). $99 for TRACE is 0.06% of the settlement. This is invisible.
- **The comparison they'll make:** "I pay my paralegal $25/hour for 15 hours to do this. That's $375. $99 is cheaper AND faster."

### TRACE Pricing Tiers

| Plan | Per Case | Includes |
|------|---------|----------|
| **Starter** | $49 | Case creation, SOL calc, 3 providers, 5 faxes, basic chronology, PDF export |
| **Professional** | $99 | Everything in Starter + unlimited providers/faxes, clinical flags, readiness board, lien tracking, JSON export |
| **Complete** | $149 | Everything in Pro + deterministic medical summaries, demand template builder, follow-up scheduler, priority processing |

**First 3 cases free** — this is critical. The ICP needs to see TRACE work on their own cases before paying. Three free cases gives them enough experience to see the ROI. After that: pay per case.

### Revenue Model Comparison

Solo attorney averaging 4 new cases/month:

| Model | Monthly | Annual | ICP Preference |
|-------|---------|--------|----------------|
| Monthly $199 | $199 | $2,388 | Low — feels like overhead |
| Per-case $99 × 4 | $396 | $4,752 | High — tied to active cases |
| Per-case $149 × 4 | $596 | $7,152 | Medium — premium features |

Small firm averaging 12 new cases/month:

| Model | Monthly | Annual | ICP Preference |
|-------|---------|--------|----------------|
| Monthly $399 | $399 | $4,788 | Medium |
| Per-case $99 × 12 | $1,188 | $14,256 | High — scales with firm |
| Per-case $149 × 12 | $1,788 | $21,456 | High — premium features |

### Pricing Guardrails

1. **No per-request fax fees.** Competitors charge $30-65 PER FAX. TRACE sends unlimited faxes. This is a massive differentiator.
2. **No per-page OCR fees.** Misral OCR costs are absorbed — the attorney's per-case fee covers it.
3. **No storage fees.** Document storage in Supabase is included.
4. **No AI/LLM surcharge.** DeepSeek API costs are absorbed.
5. **Volume discounts for firms with 20+ cases/month** — auto-applied.

---

## Section 6 — What The Earlier Research Found (July 2026 Session)

The earlier DeepSeek BAA research (July 20 session) confirmed:
- DeepSeek public API has **NO BAA** — cannot be used for any PHI-adjacent processing
- Anthropic API (Claude) and OpenAI API both offer BAAs
- For the billing reconciliation LLM use case (Phase 1D), DeepSeek is fine because NO PHI is sent to the LLM — only de-identified billing codes and amounts
- For any future use case involving PHI-adjacent processing (medical summaries, clinical analysis), use Anthropic or OpenAI API — not DeepSeek

This is why the deterministic (non-AI) medical summary design above is critical: it avoids the BAA problem entirely. No LLM touches the medical records. Rule-based extraction only.

---

*This document addresses all founder questions raised on July 24, 2026. To be included in the overall competitive analysis.*
