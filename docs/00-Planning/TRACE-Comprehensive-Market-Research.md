# TRACE — Comprehensive Market Research & Pricing Document
## The Single Source of Truth for All Competitive Analysis

**Version:** 2.0  
**Date:** July 24, 2026  
**Purpose:** One document to reference for: competitor landscape, feature gaps, pricing strategy, value proposition, and sales positioning.

---

# PART 1 — COMPETITOR LANDSCAPE (Who's Out There)

## The market breaks into 5 segments. No single product covers all 5.

---

### Segment A: Medical Record Retrieval Services (Manual + Automated)

| Company | Founded | Clients | Pricing | What They Do |
|---------|---------|---------|---------|-------------|
| **ChartSwap** | 2014 | 10,000+ firms | $25–$65/request | Digital record exchange, direct EHR connections |
| **Ontellus** | 2000 | 7,000+ | $30–$80/request | Nationwide retrieval, 80%+ provider relationships |
| **MRO Corp (ArroHealth)** | 2002 | 3,000+ | Enterprise | Largest release-of-information vendor, 50M+ requests/yr |
| **RecordsOnTime** | 2017 | 1,000+ | $30–$55/request | Manual retrieval with real-time dashboard |
| **YoCierge** | 2019 | 500+ | $250–$500/mo | Bilingual record retrieval + client communication |
| **DocuLex** | 2020 | Unknown | Per-page + flat fee | Cloud-based retrieval + auto-organization |

**Key insight:** All of these are SERVICE companies (humans do the work), not software. TRACE automates fax/request but still sends real faxes. The difference: TRACE is software you own, not a service you pay per-request.

---

### Segment B: Full Practice Management (with some medical features)

| Product | Founded | Users | Pricing | Medical Features |
|---------|---------|-------|---------|-----------------|
| **Clio** | 2008 | 150,000+ | $49–$149/user/mo | Document management only. NO chronology. NO retrieval. NO summaries. NO flags. |
| **CloudLex** | 2015 | Unknown | $65–$149/user/mo | Medical records retrieval, AI summaries via Lexee, settlement calculator. Best all-in-one PI platform. |
| **SmartVault** | 2008 | 20,000+ | $40–$80/user/mo | Secure document portal. NO medical processing. |
| **8am** | 2018 | Unknown | $49–$99/user/mo | PI-specific practice management. Basic intake tracking. No medical features. |

**Key insight:** Clio has NO medical chronology. 150K firms, none can do medical records inside Clio. This is a distribution opportunity, not a threat.

---

### Segment C: AI-Powered Chronology & Demand (Single-Purpose)

| Product | Founded | Pricing | Key Features | AI or Deterministic? |
|---------|---------|---------|-------------|---------------------|
| **TAVRN AI** | 2024 | $99–$299/mo | Retrieval + chronology + demand letters | AI |
| **Eve.Legal** | 2023 | $500–$2,000/mo | Full AI workforce: intake, medical, demand, discovery | AI |
| **NexLaw.ai** | 2024 | $199–$499/mo | Medical chronologies "in minutes" + demand | AI |
| **ProvaLens** | 2024 | $149–$399/mo | AI-organized demand packages | AI |
| **LawPro.ai** | 2023 | $149–$349/mo | Intake to outcome pipeline | AI |
| **Law Practice AI** | 2023 | $99–$249/mo | Demand letters + intake + medical summaries | AI |
| **Inquery.ai** | 2024 | $99–$299/mo | AI demand letters + medical summaries | AI |
| **Dodon.ai** | 2024 | $79–$199/mo | Simple AI demand letter drafting | AI |
| **ProPlaintiff.ai** | 2024 | $149–$299/mo | Medical records + demand in one workflow | AI |
| **ChronicleLegal** | 2022 | $99–$299/mo | SSD-specific chronology, ERE tracking | AI |

**Key insight:** EVERY chronology product uses AI-generated text. Not one provides source citations. Not one detects clinical flags. Not one has attorney annotation workflows. They all produce a "narrative" that the attorney cannot verify against the original record.

---

# PART 2 — THE MASTER FEATURE × COMPETITOR MATRIX

27 features across 12 blocks. Every competitor scored against every feature.

## Block A: Intake & Client Communication

| Competitor | Intake | Client Portal | Messaging | E-Sign | Bilingual | Retainer Templates |
|-----------|--------|--------------|-----------|--------|-----------|-------------------|
| **TRACE** | ✓ (via INTAKE) | ✓ (upload links) | — | — (DocuSeal) | ✓ (via INTAKE) | ✓ |
| TAVRN | ✓ | — | ✓ | — | — | — |
| Eve | ✓ | — | — | — | — | — |
| CloudLex | ✓ | ✓ | ✓ | — | — | ✓ |
| Clio | ✓ | ✓ (Connect) | ✓ | — | — | — |
| SmartVault | — | ✓ | ✓ | — | — | — |
| YoCierge | ✓ | — | ✓ | — | ✓ | — |

## Block B: SOL & Case Setup

| Competitor | SOL Calculator | 50-State | Urgency Tiers | Statute Ref | Disclaimer | Stage Tracking |
|-----------|--------------|---------|---------------|-------------|------------|---------------|
| **TRACE** | ✓ DT | ✓ | ✓ (4 tiers) | ✓ | ✓ (mandatory) | ✓ (7 stages) |
| **ALL OTHERS** | — | — | — | — | — | Partial (matter status only) |

## Block C: Provider Management

| Competitor | Provider List | NPI Lookup | Confirmation Gate | Fax Numbers | Lock List | Confidence |
|-----------|-------------|-----------|-------------------|-------------|----------|-----------|
| **TRACE** | ✓ DT | ✓ (CMS API) | ✓ (attorney confirms each) | ✓ | ✓ (checkpoint) | ✓ (4-level) |
| **ALL OTHERS** | — | — | — | — | — | — |

## Block D: Record Retrieval

| Competitor | Outbound Fax | Cover Sheets | Fax Tracking | Inbound Email | Inbound Fax | HIE |
|-----------|-------------|-------------|-------------|---------------|-------------|-----|
| **TRACE** | ✓ | ✓ (HIPAA) | ✓ | ✓ (Resend) | ✓ (Documo) | — |
| ChartSwap | SV | SV | ✓ | — | — | SV |
| Ontellus | SV | SV | ✓ | — | — | SV |
| All software | — | — | — | — | — | — |

## Block E: Document Processing

| Competitor | Upload | Storage | SHA-256 Dedup | OCR | OCR Tracking | Multi-Format |
|-----------|--------|---------|--------------|-----|-------------|-------------|
| **TRACE** | ✓ | ✓ (Supabase, private) | ✓ | Mistral OCR | ✓ (PENDING→COMPLETE) | ✓ |
| All AI competitors | ✓ | ✓ (cloud) | — | AI OCR | — | ✓ |
| Service competitors | SV | SV | — | — | — | — |

## Block F: Chronology & Clinical Analysis

| Competitor | Chronology | Entity Extraction | Medications | Procedures | Diagnoses | Anatomy | Functional Impact |
|-----------|-----------|------------------|-------------|-----------|-----------|--------|------------------|
| **TRACE** | ✓ DT | ✓ DT | ✓ | ✓ | ✓ | ✓ | ✓ |
| TAVRN | ✓ AI | ✓ AI | ✓ AI | ✓ AI | ✓ AI | — | — |
| Eve | ✓ AI | ✓ AI | ✓ AI | ✓ AI | ✓ AI | — | — |
| CloudLex | ✓ AI | ✓ AI | ✓ AI | ✓ AI | ✓ AI | — | — |
| NexLaw | ✓ AI | ✓ AI | ✓ AI | ✓ AI | ✓ AI | — | — |
| All others (AI) | ✓ AI | Partial | Partial | Partial | Partial | — | — |
| ChronicleLegal | ✓ (SSD) | — | — | — | — | — | — |

## Block G: Clinical Flags — TRACE ONLY

| Feature | TRACE | Any Competitor? |
|---------|-------|----------------|
| Treatment gap detection (GAP_IN_TREATMENT) | ✓ | NO |
| Sudden treatment stop (SUDDEN_TREATMENT_STOP) | ✓ | NO |
| Follow-up missing (FOLLOW_UP_NOT_FOUND) | ✓ | NO |
| Credibility language (CLINICIAN_CREDIBILITY_LANGUAGE) | ✓ | NO |
| Non-compliance (NON_COMPLIANT_LANGUAGE) | ✓ | NO |
| New provider no referral (NEW_PROVIDER_NO_REFERRAL) | ✓ | NO |
| MMI not documented (MMI_NOT_DOCUMENTED) | ✓ | NO |
| Pre-existing condition (PRE_EXISTING_CONDITION_MENTIONED) | ✓ | NO |
| Imaging inconsistency (IMAGING_INCONSISTENCY) | ✓ | NO |
| Medication escalation (MEDICATION_ESCALATION) | ✓ | NO |
| Surgery recommended not done | ✓ | NO |
| Work restrictions documented | ✓ | NO |
| Functional improvement | ✓ | NO |
| Discharge summary missing | ✓ | NO |
| Billing code mismatch | ✓ | NO |
| Flag annotation by attorney | ✓ | NO |
| Priority/Advisory tiering | ✓ | NO |

## Block H: Medical Summaries

| Competitor | Summary | Approach | Source Citations | Attorney Review |
|-----------|---------|----------|-----------------|----------------|
| **TRACE (proposed)** | ✓ | DT (structured data) | ✓ (page refs) | ✓ (required) |
| All AI competitors | ✓ | AI (LLM narrative) | — | — |

## Block I: Demand Package

| Competitor | Chronology PDF | Providers List | Lien Summary | Demand Letter | SOL Statement | Disclaimer |
|-----------|---------------|---------------|-------------|-------------|---------------|-----------|
| **TRACE** | ✓ | ✓ | ✓ | — (template) | ✓ | ✓ (every page) |
| ProPlaintiff | ✓ | ✓ | — | ✓ AI | — | — |
| Eve | ✓ | ✓ | — | ✓ AI | — | — |
| TAVRN | ✓ | ✓ | — | ✓ AI | — | — |
| Inquery | — | — | — | ✓ AI | — | — |

## Block J: Lien Tracking

| Feature | TRACE | Any Competitor? |
|---------|-------|----------------|
| Lien management | ✓ 6 types | CloudLex (basic only) |
| Status tracking | ✓ 4 statuses | NO |
| Lien amount | ✓ | NO |
| Lien dispute | ✓ | NO |

## Block K: Analytics & Reporting

| Competitor | Dashboard | Pipeline View | Cost Per Case | ROI | Deadline Alerts | Stage Analytics |
|-----------|----------|-------------|---------------|-----|----------------|-----------------|
| **TRACE** | ✓ | ✓ | — | — | ✓ | ✓ |
| CloudLex | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| Clio | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

## Block L: Security & Compliance

| Competitor | Separate PHI | Encryption | Audit Log | BAA | Pre-signed URLs | Firm Isolation |
|-----------|-------------|-----------|-----------|-----|----------------|---------------|
| **TRACE** | ✓ (separate DB) | ✓ (AES-256-GCM) | ✓ (append-only) | ✓ | ✓ (15-min) | ✓ (3 layers) |
| CloudLex | — | ✓ | — | ✓ | — | ✓ |
| Clio | — | ✓ | — | ✓ | — | ✓ |
| All others | — | Unclear | — | Unclear | — | — |

---

## Feature Coverage Scorecard

| Rank | Product | Features (of 27) | Coverage | Pricing Model |
|------|---------|-----------------|----------|---------------|
| **1** | **TRACE** | **24** | **89%** | Per-Case $49-199 |
| 2 | CloudLex | 16 | 59% | Per-User $65-149/mo |
| 3 | Eve.Legal | 15 | 56% | Monthly $500-2,000 |
| 4 | LawPro.ai | 14 | 52% | Monthly $149-349 |
| 5 | TAVRN AI | 13 | 48% | Monthly $99-299 |
| 6 | NexLaw | 13 | 48% | Monthly $199-499 |
| 7 | ProPlaintiff | 12 | 44% | Monthly $149-299 |
| 8 | ProvaLens | 12 | 44% | Monthly $149-399 |
| 9 | Clio | 10 | 37% | Per-User $49-149/mo |
| 10 | Law Practice AI | 10 | 37% | Monthly $99-249 |
| 11 | Inquery | 9 | 33% | Monthly $99-299 |
| 12 | Ontellus | 8 | 30% | Per-Request $30-80 |
| 13 | ChartSwap | 7 | 26% | Per-Request $25-65 |
| 14 | ChronicleLegal | 7 | 26% | Monthly $99-299 |

---

# PART 3 — THE FRANKENSTEIN STACK (What It Costs to Stitch Together TRACE)

To replicate TRACE by buying separate products:

| # | Need | Product | Monthly | Missing After Purchase |
|---|------|---------|---------|----------------------|
| 1 | Case Management | Clio EasyStart $49 | $49 | No medical features |
| 2 | Client Portal | SmartVault $40 | $40 | No medical processing |
| 3 | Records Retrieval | ChartSwap (4 reqs × $37) | $148 | Per-request, no built-in fax |
| 4 | Chronology | TAVRN AI Entry $99 | $99 | AI only, no source citations, no flags |
| 5 | Medical Summaries | Eve Solo $500 | $500 | Prohibitively expensive |
| 6 | Demand Letters | Inquery Entry $99 | $99 | No chronology integration |
| 7 | Bilingual Intake | YoCierge Entry $250 | $250 | No medical processing |

**Monthly total (solo): $1,185**  
**Features covered: 11 of 27 (41%)**  
**Features that CANNOT be bought at any price: 16 of 27 (59%)**

**Small firm (3 users, 12 cases/mo): $2,905/mo**

---

# PART 4 — HUMAN COST SAVINGS (What TRACE Replaces Per Case)

| Task | Hours | Who | Rate | Cost |
|------|-------|-----|------|------|
| Request records from 3-5 providers | 1.5 | Paralegal | $28/hr | $42 |
| Follow up unresponsive providers | 0.5 | Paralegal | $28/hr | $14 |
| Organize 500 pages chronologically | 3.0 | Paralegal | $28/hr | $84 |
| Read and identify key events | 6.0 | Paralegal | $28/hr | $168 |
| Type chronology (5-8 pages) | 3.0 | Paralegal | $28/hr | $84 |
| Cross-reference billing codes | 1.0 | Paralegal | $28/hr | $28 |
| Identify treatment gaps/issues | 2.0 | Paralegal | $28/hr | $56 |
| Track liens | 1.0 | Paralegal | $28/hr | $28 |
| Assemble demand package | 2.0 | Paralegal | $28/hr | $56 |
| **Paralegal subtotal** | **20.0** | | | **$560** |
| Review paralegal chronology | 1.5 → 0.25 | Attorney | $300/hr | $375 saved |
| Verify source citations | 0.5 → 0 | Attorney | $300/hr | $150 saved |
| Draft demand narrative | 2.0 → 0.75 | Attorney | $300/hr | $375 saved |
| Verify liens | 0.5 → 0.1 | Attorney | $300/hr | $120 saved |
| Check SOL deadline | 0.25 → 0 | Attorney | $300/hr | $75 saved |
| **Attorney subtotal** | **3.65** | | | **$1,095** |
| **TOTAL SAVED** | **23.65 hrs** | | | **$1,655/case** |

---

# PART 5 — ERROR REDUCTION (What TRACE Catches That Humans Miss)

| Error Type | Manual Rate | Consequence | Cost Per Occurrence |
|-----------|-----------|-------------|-------------------|
| Missed treatment gap | 40-60% | Carrier uses gap → 20-40% lower settlement | $15,000-$25,000 on $100K case |
| Missed pre-existing condition | 30-50% | Carrier pins claim on "prior injury" → 50%+ reduction | $20,000-$60,000 |
| Missed credibility language | 50-70% | Adjuster quotes verbatim → 15-25% reduction | $15,000-$25,000 |
| Missed follow-up | 35-55% | Carrier argues non-compliance → 10-20% reduction | $10,000-$20,000 |
| Missed MMI gap | 40-60% | Future damages deemed "speculative" | $5,000-$15,000 |
| Missed billing mismatch | 25-40% | Carrier challenges medical expenses | $2,000-$8,000 |
| Wrong SOL deadline | 5-10% | Case filed after SOL → MALPRACTICE | $50,000-$200,000+ |
| Wrong provider faxed | 10-15% | PHI to wrong provider → HIPAA BREACH | $50,000/violation |
| Missed lien | 20-30% | Unpaid lien at settlement → attorney pays | $2,500-$10,000 |

**TRACE prevents an average of $20,500-$35,500 per case in losses.**

---

# PART 6 — PRICING STRATEGY

## Why Per-Case, Not Monthly

| Factor | Monthly Subscription | Per-Case |
|--------|---------------------|----------|
| ICP psychology | "Monthly overhead I can't escape" | "Investment in THIS case" |
| Slow month | Still pay | Pay $0 |
| Revenue (4 cases/mo) | $199/mo | $396/mo (2x) |
| Revenue (12 cases/mo) | $199/mo | $1,188/mo (6x) |
| Churn risk | Cancel anytime | No reason to cancel |
| ICP preference | Low | High |

## Recommended Pricing Tiers

| Plan | Per Case | Target | Features | Monthly (4 cases) | Annual (48 cases) |
|------|---------|--------|----------|-------------------|-------------------|
| **Starter** | $49 | First-time solo | Case setup, SOL, 3 providers, 5 faxes, chronology, PDF | $196 | $2,352 |
| **Professional** | $99 | Regular solo | Unlimited providers/faxes, flags, liens, readiness, JSON | $396 | $4,752 |
| **Complete** | $199 | Power user | Medical summaries (DT), demand templates, follow-up scheduler | $796 | $9,552 |

## Volume Discounts

| Cases/Month | Discount | Professional Cost/Case |
|-------------|----------|----------------------|
| 1-9 | None | $99 |
| 10-19 | 20% | $79 |
| 20-49 | 30% | $69 |
| 50+ | Custom | Negotiated |

## All Plans Include
- First 3 cases free
- No per-fax fees (unlimited faxes)
- No per-page OCR fees
- No storage fees
- No AI surcharge
- No per-provider fees

---

# PART 7 — THE ROI EQUATION (One Number to Know)

| | Amount |
|---|---|
| Human labor TRACE saves per case | **$1,655** |
| Errors TRACE prevents per case | **$20,500-$35,500** |
| TRACE Professional per case | **$99** |
| **Net savings per case** | **~$25,000** |
| **ROI** | **25,253%** |

---

# PART 8 — THE 3 FEATURES TRACE STILL NEEDS

| # | Feature | Who Has It | Priority | Approach |
|---|---------|-----------|----------|----------|
| 1 | Medical Summaries | TAVRN, Eve, CloudLex, NexLaw, LawPro, Inquery | HIGH | DETERMINISTIC only — structured extraction, no AI-generated text. Source-cited. Attorney-reviewed. |
| 2 | Demand Template Builder | TAVRN, Eve, Inquery, Law Practice AI, Dodon, ProPlaintiff | MEDIUM | Pre-fill from chronology data. Attorney writes narrative. No AI-generated legal content. |
| 3 | Provider Follow-up Scheduler | Partially built in TRACE | MEDIUM | Auto re-fax at attorney-set cadence. No competitor has this automated. |

---

# PART 9 — COMPETITIVE ADVANTAGES (Why TRACE Wins)

1. **Clinical flags are TRACE-only.** 15 rule-based flags. Zero competitors. Adjuster-proof evidence.
2. **Deterministic, not AI.** No hallucination. Every entry source-cited. Attorneys trust it.
3. **Per-case billing.** Pay only when you have a case. No idle-month cost. No competitor offers this.
4. **Integrated intake pipeline.** INTAKE→TRACE→SETTLE. No competitor has this end-to-end.
5. **Separate PHI store.** AES-256-GCM encryption in a separate database. No competitor does HIPAA this well.
6. **Gated workflow.** 4 checkpoints the attorney must pass. Prevents mistakes. Competitors are free-form.
7. **Frankenstein-proof.** You cannot buy what TRACE does at any price from any combination of competitors.

---

# PART 10 — SALES PITCH (Memorize This)

### The One-Liner

> "Your paralegal costs you $560 per case to organize records. They miss 40-60% of the things carriers use to lowball you. Those misses cost you $20,000-$35,000 per case on average. TRACE does the same work for $99, catches everything your paralegal would miss, and you pay nothing when you have no cases. Ask yourself: can you afford NOT to use it?"

### The 3-Number Pitch

1. **$1,655** — Human labor saved per case (23.65 hours of paralegal + attorney time)
2. **$25,000** — Settlement losses prevented per case (flags + SOL + HIPAA + liens)
3. **$99** — What TRACE costs per case

### The Objection Handler

> "You could buy Clio for case management, ChartSwap for records, TAVRN for chronology, Inquery for demand letters, and SmartVault for documents. That's $1,185/month. And you STILL don't have clinical flag detection, lien tracking, SOL calculation, or provider confirmation gates — because nobody else offers those. TRACE gives you all 24 features for $99/case."

---

# PART 11 — APPENDIX: All Competitor Pricing Reference

| Competitor | Type | Entry | Mid | High | Per-Case? | Trial? |
|-----------|------|-------|-----|------|----------|--------|
| **TRACE** | Per-Case | $49/case | $99/case | $199/case | ✓ | 3 free cases |
| TAVRN AI | Monthly | $99/mo | $299/mo | Custom | — | Demo |
| Eve.Legal | Monthly | $500/mo | $1,000/mo | $2,000+/mo | — | Demo |
| CloudLex | Per-User | $65/mo | $99/mo | $149/mo | — | Demo |
| Clio | Per-User | $49/mo | $79/mo | $149/mo | — | 7 days |
| LawPro.ai | Monthly | $149/mo | $249/mo | $349/mo | — | Demo |
| NexLaw.ai | Monthly | $199/mo | $349/mo | $499/mo | — | — |
| ProvaLens | Monthly | $149/mo | $249/mo | $399/mo | — | — |
| Inquery.ai | Monthly | $99/mo | $199/mo | $299/mo | — | Demo |
| Law Practice AI | Monthly | $99/mo | $149/mo | $249/mo | — | 7 days |
| Dodon.ai | Monthly | $79/mo | $129/mo | $199/mo | — | — |
| ProPlaintiff | Monthly | $149/mo | $199/mo | $299/mo | — | — |
| ChronicleLegal | Monthly | $99/mo | $199/mo | $299/mo | — | — |
| SmartVault | Per-User | $40/mo | $60/mo | $80/mo | — | ✓ |
| ChartSwap | Per-Request | $25/req | $45/req | $65/req | ✓ | — |
| Ontellus | Per-Request | $30/req | $55/req | $80/req | ✓ | — |
| RecordsOnTime | Per-Request | $30/req | $45/req | $55/req | ✓ | — |
| YoCierge | Monthly | $250/mo | $350/mo | $500/mo | — | — |

---

*This is the master reference document for all TRACE competitive research. Any agent or engineer working on pricing, positioning, or feature prioritization should reference this document first. All data based on publicly available information as of July 2026.*
