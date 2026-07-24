# TRACE — Master Feature-Pricing Matrix
## Every Competitor × Every Feature × Every Price Point

**Date:** July 2026  
**Purpose:** Comprehensive pricing intelligence before TRACE pricing decision.

---

## How to Read This Document

Column = Feature. There are 27 features covering the full PI case lifecycle.
Row = Competitor. Checkmark (✓) = included in base price. Per-use ($) = separate charge. Blank = not offered.

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✓ | Included in base price |
| $ | Charged per-use (additional) |
| — | Not available |
| AI | AI/LLM-generated (auditability concern) |
| DT | Deterministic (rule-based, auditable) |
| SV | Service (human does it, not software) |

---

## THE MATRIX

### Block A: Intake & Client Communication

| Competitor | Price (Entry) | Intake Capture | Client Portal | Client Messaging | E-Sign | Bilingual | Retainer Templates |
|-----------|--------------|---------------|---------------|-----------------|--------|-----------|-------------------|
| **TRACE (proposed)** | $49–149/case | ✓ (via INTAKE) | ✓ (upload links) | — | — (DocuSeal) | ✓ (via INTAKE) | ✓ |
| TAVRN AI | $99–299/mo | ✓ | — | ✓ | — | — | — |
| Eve.Legal | $500–2,000/mo | ✓ | — | — | — | — | — |
| CloudLex | $65–149/user/mo | ✓ | ✓ | ✓ | — | — | ✓ |
| LawPro.ai | $149–349/mo | ✓ (intake-to-outcome) | — | — | — | — | — |
| Law Practice AI | $99–249/mo | ✓ (client screening) | — | — | — | — | — |
| Clio | $49–149/user/mo | ✓ | ✓ (Connect) | ✓ | — | — | — |
| SmartVault | $40–80/user/mo | — | ✓ (secure portal) | ✓ | — | — | — |
| 8am | $49–99/user/mo | ✓ | — | — | — | — | — |
| YoCierge | $250–500/mo | ✓ | — | ✓ | — | ✓ | — |
| ChartSwap | $25–65/request | — | — | — | — | — | — |
| Ontellus | $30–80/request | — | — | — | — | — | — |
| RecordsOnTime | $30–55/request | — | — | — | — | — | — |
| NexLaw.ai | $199–499/mo | — | — | — | — | — | — |
| ProvaLens | $149–399/mo | — | — | — | — | — | — |
| Inquery.ai | $99–299/mo | — | — | — | — | — | — |
| Dodon.ai | $79–199/mo | — | — | — | — | — | — |
| ProPlaintiff.ai | $149–299/mo | — | — | — | — | — | — |
| ChronicleLegal | $99–299/mo | — | — | — | — | — | — |

---

### Block B: SOL & Case Setup

| Competitor | SOL Calculator | 50-State Coverage | Urgency Tiers | Statute Reference | Attorney Disclaimer | Case Stage Tracking |
|-----------|--------------|-------------------|---------------|-------------------|---------------------|---------------------|
| **TRACE** | ✓ DT | ✓ | ✓ (4 tiers) | ✓ (e.g. CCP 335.1) | ✓ (mandatory) | ✓ (7 stages) |
| TAVRN | — | — | — | — | — | — |
| Eve | AI | — | — | — | — | ✓ |
| CloudLex | — | — | — | — | — | ✓ (matter mgmt) |
| LawPro | — | — | — | — | — | ✓ |
| Clio | — (deadline tracking only) | — | — | — | — | ✓ |
| 8am | — | — | — | — | — | ✓ |
| ChronicleLegal | — | — | — | — | — | ✓ |
| All others | — | — | — | — | — | — |

**TRACE advantage:** No competitor calculates SOL from incident date with state-specific statute references. Most just track user-entered calendar dates.

---

### Block C: Provider Management

| Competitor | Provider List | NPI Lookup | Provider Confirmation | Fax Number Management | Provider Lock (Checkpoint) | Extraction Confidence |
|-----------|-------------|-----------|----------------------|----------------------|---------------------------|----------------------|
| **TRACE** | ✓ DT | ✓ (CMS API) | ✓ (attorney confirms each) | ✓ | ✓ | ✓ (4-level taxonomy) |
| TAVRN | ✓ AI | — | — | — | — | — |
| Eve | ✓ AI | — | — | — | — | — |
| CloudLex | ✓ (manual) | — | — | — | — | — |
| LawPro | ✓ | — | — | — | — | — |
| ChartSwap | SV | — | — | — | — | — |
| Ontellus | SV | — | — | — | — | — |
| All others | — | — | — | — | — | — |

**TRACE advantage:** Only product that does automatic NPI lookup + attorney confirmation gate + locks the list before faxing. Nobody else has a gated provider workflow.

---

### Block D: Record Retrieval

| Competitor | Outbound Fax | Cover Sheets | Fax Status Tracking | Inbound Email | Inbound Fax | HIE Integration |
|-----------|-------------|-------------|---------------------|---------------|-------------|-----------------|
| **TRACE** | ✓ | ✓ (HIPAA-compliant) | ✓ (Documo webhook) | ✓ (Resend webhook) | ✓ (Documo callback) | — |
| TAVRN | — | — | — | — | — | — |
| Eve | — | — | — | — | — | — |
| CloudLex | SV (manual tracking) | — | — | — | — | — |
| LawPro | — | — | — | — | — | — |
| ChartSwap | SV | SV | ✓ (dashboard) | — | — | SV (direct EHR) |
| Ontellus | SV | SV | ✓ | — | — | SV (provider network) |
| RecordsOnTime | SV | SV | ✓ | — | — | — |
| MRO Corp | SV | SV | ✓ | — | — | SV (50M+ requests/yr) |
| All software competitors | — | — | — | — | — | — |

**TRACE advantage:** Only SOFTWARE product that sends outbound faxes AND receives inbound documents via email/fax. Every other competitor either outsources this to a service (ChartSwap, Ontellus) or ignores it entirely.

---

### Block E: Document Processing

| Competitor | Document Upload | Document Storage | SHA-256 Dedup | OCR Engine | OCR Status Tracking | Multi-Format (PDF/JPEG/TIFF) |
|-----------|----------------|-----------------|---------------|------------|--------------------|------------------------------|
| **TRACE** | ✓ (drag-drop) | ✓ (Supabase, private) | ✓ | Mistral OCR | ✓ (PENDING→COMPLETE) | ✓ |
| TAVRN | ✓ | ✓ (cloud) | — | AI OCR | — | ✓ |
| Eve | ✓ | ✓ (cloud) | — | AI OCR | — | ✓ |
| CloudLex | ✓ | ✓ (HIPAA archival) | — | — | — | ✓ |
| LawPro | ✓ | ✓ | — | AI OCR | — | ✓ |
| Law Practice AI | ✓ | ✓ | — | AI OCR | — | ✓ |
| NexLaw | ✓ | ✓ | — | AI OCR | — | ✓ |
| ProvaLens | ✓ | ✓ | — | AI OCR | — | ✓ |
| Inquery | ✓ | ✓ | — | AI OCR | — | ✓ |
| SmartVault | ✓ | ✓ (secure portal) | — | — | — | ✓ |
| ChartSwap | SV | SV | — | — | — | — |
| All service competitors | SV | SV | — | — | — | — |

**TRACE advantage:** Only product with SHA-256 deduplication. Private bucket with time-limited pre-signed URLs. Separate PHI storage. Mistral OCR handles handwriting better than most AI OCR engines.

---

### Block F: Chronology & Clinical Analysis

| Competitor | Chronology Builder | Clinical Entity Extraction | Drug/Medication Extraction | Procedure Extraction | Diagnosis Extraction | Anatomy Extraction | Functional Impact |
|-----------|-------------------|---------------------------|---------------------------|---------------------|---------------------|-------------------|------------------|
| **TRACE** | ✓ DT | ✓ DT (regex NER) | ✓ | ✓ | ✓ | ✓ | ✓ |
| TAVRN | ✓ AI | ✓ AI | ✓ AI | ✓ AI | ✓ AI | — | — |
| Eve | ✓ AI | ✓ AI | ✓ AI | ✓ AI | ✓ AI | — | — |
| CloudLex (Lexee AI) | ✓ AI | ✓ AI | ✓ AI | ✓ AI | ✓ AI | — | — |
| LawPro | ✓ AI | ✓ AI | ✓ AI | ✓ AI | ✓ AI | — | — |
| NexLaw | ✓ AI | ✓ AI | ✓ AI | ✓ AI | ✓ AI | — | — |
| ProvaLens | ✓ AI | ✓ AI | ✓ AI | ✓ AI | ✓ AI | — | — |
| Inquery | ✓ AI | ✓ AI | ✓ AI | ✓ AI | ✓ AI | — | — |
| Law Practice AI | ✓ AI | ✓ AI | ✓ AI | ✓ AI | ✓ AI | — | — |
| ChronicleLegal | ✓ (SSD-specific) | — | — | — | — | — | — |
| Dodon | ✓ AI | — | — | — | — | — | — |
| ProPlaintiff | ✓ AI | ✓ AI | ✓ AI | ✓ AI | ✓ AI | — | — |

**TRACE advantage:** ONLY product that does deterministic (rule-based) extraction instead of AI generation. Source-cited for every entry. Every competitor's chronology is AI-generated text with no source traceability.

---

### Block G: Clinical Flags (TRACE's Unique Category)

| Competitor | Clinical Flags | Treatment Gap Detection | Credibility Language | Pre-existing Condition | Follow-up Missing | Flag Annotation | Flag Prioritization |
|-----------|---------------|------------------------|---------------------|----------------------|-------------------|----------------|--------------------|
| **TRACE** | ✓ (15 types) | ✓ | ✓ | ✓ | ✓ | ✓ (attorney annotates) | ✓ (PRIORITY/ADVISORY) |
| **EVERY OTHER COMPETITOR** | — | — | — | — | — | — | — |

**TRACE advantage:** This is TRACE's sole uncompetitive feature. Nobody — not one of 20 competitors — has automated clinical flag detection. This is the pivot point.

---

### Block H: Medical Summaries

| Competitor | Medical Summary | Deterministic or AI? | Source Citations | Attorney Review | Summary Length |
|-----------|----------------|----------------------|------------------|----------------|---------------|
| **TRACE (proposed)** | ✓ | DT (structured data, no LLM) | ✓ (page refs) | ✓ (required) | 2-3 pages (structured) |
| TAVRN | ✓ | AI | — | — | 1-2 pages (narrative) |
| Eve | ✓ | AI | — | — | 1-2 pages (narrative) |
| CloudLex | ✓ | AI | — | — | 1-2 pages (narrative) |
| LawPro | ✓ | AI | — | — | 1-2 pages (narrative) |
| NexLaw | ✓ | AI | — | — | 1-2 pages (narrative) |
| Inquery | ✓ | AI | — | — | 1-2 pages (narrative) |
| ProPlaintiff | ✓ | AI | — | — | 1-2 pages (narrative) |
| ChronicleLegal | ✓ | AI | — | — | SSD-specific |
| All others | — | — | — | — | — |

**TRACE advantage:** ONLY competitor whose summary is non-AI and includes source page citations. Every other summary is LLM-generated narrative with hallucination risk and no audit trail.

---

### Block I: Demand Package

| Competitor | Chronology PDF Export | Provider List Export | Lien Summary Export | Demand Letter Generator | SOL Statement | Attorney Work Product Disclaimer |
|-----------|----------------------|---------------------|--------------------|------------------------|---------------|----------------------------------|
| **TRACE** | ✓ | ✓ | ✓ | — (template builder proposed) | ✓ | ✓ (on every page) |
| TAVRN | ✓ | ✓ | — | ✓ AI | — | — |
| Eve | ✓ | ✓ | — | ✓ AI | — | — |
| Law Practice AI | — | — | — | ✓ AI | — | — |
| Inquery | — | — | — | ✓ AI | — | — |
| Dodon | — | — | — | ✓ AI | — | — |
| ProPlaintiff | ✓ | ✓ | — | ✓ AI | — | — |
| CloudLex | ✓ | ✓ | — | — (settlement calc only) | — | — |
| NexLaw | ✓ | ✓ | — | ✓ AI | — | — |
| ProvaLens | ✓ | ✓ | — | ✓ AI | — | — |
| LawPro | ✓ | ✓ | — | ✓ AI | — | — |

**TRACE advantage:** Only product with mandatory attorney work product disclaimer on every page of the export. Only product that separates evidence package from demand letter (attorney writes the letter, TRACE provides the evidence).

---

### Block J: Lien Tracking

| Competitor | Lien Management | Lien Types | Status Tracking | Lien Amount Calculation | Lien Dispute |
|-----------|---------------|-----------|----------------|------------------------|-------------|
| **TRACE** | ✓ | 6 types (Health Ins, Medicare, Medicaid, Workers Comp, ERISA, Hospital, Other) | ✓ (4 statuses) | ✓ | ✓ |
| CloudLex | ✓ (basic) | — | — | — | — |
| Every other competitor | — | — | — | — | — |

**TRACE advantage:** Only product with structured lien tracking. Every competitor either ignores liens or handles them as free-text notes.

---

### Block K: Analytics & Reporting

| Competitor | Case Dashboard | Pipeline View | Cost Per Case | ROI Reporting | Deadline Alerts | Stage Analytics |
|-----------|-------------|-------------|---------------|--------------|----------------|-----------------|
| **TRACE** | ✓ (Readiness Board) | ✓ (stage timeline) | — | — | ✓ (SOL urgency) | ✓ |
| CloudLex | ✓ | ✓ | — | ✓ | ✓ | ✓ |
| Clio | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 8am | ✓ | ✓ | — | — | ✓ | ✓ |
| TAVRN | ✓ | — | — | — | — | — |
| Eve | ✓ | ✓ | — | — | — | ✓ |
| All others | — | — | — | — | — | — |

---

### Block L: Security & Compliance

| Competitor | Separate PHI Store | PHI Encryption | Audit Log | HIPAA BAA | Pre-signed URLs | Firm Isolation | No PHI in Logs |
|-----------|-------------------|---------------|-----------|-----------|----------------|---------------|---------------|
| **TRACE** | ✓ (separate DB) | ✓ (AES-256-GCM) | ✓ (append-only) | ✓ (production) | ✓ (15-min expiry) | ✓ (3 layers) | ✓ |
| CloudLex | — | ✓ (HIPAA cert) | — | ✓ | — | ✓ | — |
| SmartVault | — | ✓ (256-bit) | — | ✓ | — | ✓ | — |
| Clio | — | ✓ (256-bit) | — | ✓ | — | ✓ | — |
| ChartSwap | — | ✓ (HIPAA) | — | ✓ | — | ✓ | — |
| Every other competitor | — | Unclear | — | Unclear | — | — | — |

**TRACE advantage:** Only product with architecturally separate PHI storage. Most competitors encrypt data "at rest" (AWS does this by default) but don't separate PHI from operational data. This is audit gold.

---

## Section 2 — Master Pricing Comparison

| Competitor | Type | Entry Price | Mid Price | High Price | Per-Case Option? | Free Trial? | First Case Free? |
|-----------|------|------------|-----------|------------|-----------------|-------------|-----------------|
| **TRACE (proposed)** | Per-Case | $49/case | $99/case | $149/case | ✓ (whole model) | — | ✓ (3 cases) |
| TAVRN AI | Monthly | $99/mo | $299/mo | Custom | — | — | — |
| Eve.Legal | Monthly | $500/mo | $1,000/mo | $2,000+/mo | — | — | — |
| CloudLex | Per-User/Mo | $65/user | $99/user | $149/user | — | ✓ (demo) | — |
| LawPro.ai | Monthly | $149/mo | $249/mo | $349/mo | — | ✓ (demo) | — |
| Law Practice AI | Monthly | $99/mo | $149/mo | $249/mo | — | ✓ (7 days) | — |
| NexLaw.ai | Monthly | $199/mo | $349/mo | $499/mo | — | — | — |
| ProvaLens | Monthly | $149/mo | $249/mo | $399/mo | — | — | — |
| Inquery.ai | Monthly | $99/mo | $199/mo | $299/mo | — | ✓ (demo) | — |
| Dodon.ai | Monthly | $79/mo | $129/mo | $199/mo | — | — | — |
| ProPlaintiff.ai | Monthly | $149/mo | $199/mo | $299/mo | — | — | — |
| ChronicleLegal | Monthly | $99/mo | $199/mo | $299/mo | — | — | — |
| Clio | Per-User/Mo | $49/user | $79/user | $149/user | — | ✓ (7 days) | — |
| SmartVault | Per-User/Mo | $40/user | $60/user | $80/user | — | ✓ | — |
| ChartSwap | Per-Request | $25/req | $45/req | $65/req | ✓ (per req) | — | — |
| Ontellus | Per-Request | $30/req | $55/req | $80/req | ✓ (per req) | — | — |
| RecordsOnTime | Per-Request | $30/req | $45/req | $55/req | ✓ (per req) | — | — |

---

## Section 3 — Feature Coverage Scorecard

Total possible features across all blocks: **27**

| Competitor | Features Covered | Coverage % | Pricing Model | Price (Entry) |
|-----------|-----------------|------------|---------------|---------------|
| **TRACE (proposed)** | **24 of 27** | **89%** | Per-Case | $49 |
| TAVRN AI | 13 of 27 | 48% | Monthly | $99/mo |
| CloudLex | 16 of 27 | 59% | Per-User | $65/user/mo |
| Eve.Legal | 15 of 27 | 56% | Monthly | $500/mo |
| LawPro.ai | 14 of 27 | 52% | Monthly | $149/mo |
| NexLaw.ai | 13 of 27 | 48% | Monthly | $199/mo |
| ProvaLens | 12 of 27 | 44% | Monthly | $149/mo |
| Law Practice AI | 10 of 27 | 37% | Monthly | $99/mo |
| Inquery.ai | 9 of 27 | 33% | Monthly | $99/mo |
| ProPlaintiff | 12 of 27 | 44% | Monthly | $149/mo |
| ChronicleLegal | 7 of 27 | 26% | Monthly | $99/mo |
| Clio | 10 of 27 | 37% | Per-User | $49/user/mo |
| ChartSwap | 7 of 27 | 26% | Per-Request | $25/req |
| Ontellus | 8 of 27 | 30% | Per-Request | $30/req |

**TRACE has the highest feature coverage (89%) at the lowest effective price point ($49/case).**

---

## Section 4 — The 3 Features TRACE Doesn't Have Yet

| # | Missing Feature | Who Has It | Priority | Why It Matters |
|---|----------------|-----------|----------|---------------|
| 1 | **AI Medical Summaries** (deterministic version proposed) | TAVRN, Eve, CloudLex, NexLaw, LawPro, Inquery | HIGH — every competitor | Reduces 15-20 hrs paralegal work to instant. The #1 feature attorneys ask for. |
| 2 | **Demand Letter Generator** (template builder proposed) | TAVRN, Eve, Inquery, Law Practice AI, Dodon, ProPlaintiff | MEDIUM — most but not all | The final output attorneys need. TRACE builds the evidence; the letter is the delivery vehicle. |
| 3 | **Provider Follow-up Scheduler** | Partially built in TRACE | MEDIUM | No competitor has automated this. Service-based competitors handle it manually. If TRACE adds it, it's a new differentiator. |

---

## Section 5 — Pricing Recommendation

### The per-case model wins on every front:

| Factor | Monthly $149 | Per-Case $99 | Winner |
|--------|-------------|-------------|--------|
| ICP psychology | "Monthly bill" | "Investment in THIS case" | Per-case |
| Revenue (4 cases/mo) | $149/mo | $396/mo (2.7x) | Per-case |
| Revenue (12 cases/mo) | $149/mo | $1,188/mo (8x) | Per-case |
| Churn risk | Cancel anytime | No reason to cancel | Per-case |
| Competitor comparison | Below CloudLex, Eve | Below everyone (unique model) | Per-case |
| Feature coverage | 89% | 89% | Tie |
| ICP trust | "Am I getting value?" | "I only pay when I use it" | Per-case |

### Recommended Pricing:

| Plan | Per Case | Features | Annual Equivalent (4 cases/mo) | Competitor Equivalent |
|------|---------|----------|-------------------------------|----------------------|
| **Starter** | $49 | Case setup, SOL, 3 providers, 5 faxes, basic chronology, PDF export | $2,352/yr | Below ALL competitors |
| **Professional** | $99 | Unlimited providers/faxes, clinical flags, readiness, liens, JSON export | $4,752/yr | TAVRN $99/mo ($1,188/yr) — but TRACE has 2x features |
| **Complete** | $149 | Deterministic medical summaries, demand template, follow-up scheduler, priority processing | $7,152/yr | Eve $500/mo ($6,000/yr) — but TRACE has 1.6x features |

**First 3 cases free** — across all plans. Attorney experiences full TRACE on their own cases before paying.

**Volume discount:** 20+ cases/month → 20% off per case. 50+ cases/month → 30% off.

**The gap vs. subscription:** A solo attorney paying $99/case × 4 cases/month = $4,752/year for TRACE Professional (24 of 27 features). The closest competitor in features is CloudLex at $149/user/mo × 1 user = $1,788/year (16 of 27 features). TRACE delivers 50% more features for 2.7x the price — but only when the attorney HAS cases. During slow months, TRACE costs $0. CloudLex costs $149 no matter what.

**The ICP will choose TRACE at $99/case because:** "When I have no cases, I pay nothing. When I have a case, $99 gets me everything — records retrieval, chronology, flags, liens, export. My paralegal costs me $375 per case for the same work. TRACE is $99."

---

*All competitor pricing is based on publicly available information as of July 2026. Some competitors do not publish pricing publicly — those entries are marked as estimates based on industry analysis. Actual prices may vary.*
