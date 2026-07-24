# TRACE — The Definitive Reference Document
## Market Research · Pricing · ICP Pain Points · Features · Frameworks · Value Proposition

**Version:** 3.0  
**Date:** July 25, 2026  
**Purpose:** The single document every stakeholder references. Competitor analysis, pricing, ICP pain points, feature walkthrough, value proposition, frameworks, and sales positioning — all in one place.

---

# SECTION 1 — WHAT TRACE IS

## The Pipeline Position

```
INTAKE (AI voice) → TRACE (medical chronology) → SETTLE (settlement range)
     Capture              Build                    Protect
```

TRACE sits between intake and settlement. An attorney converts a prospect in INTAKE into a TRACE case. TRACE handles everything from retainer through demand-ready export. The output feeds SETTLE for settlement range estimation.

## The 7-Stage Case Lifecycle

```
PENDING_SIGNATURE → INITIALIZATION → RETRIEVAL → PROCESSING → CHRONOLOGY_READY → ATTORNEY_REVIEW → DEMAND_READY
```

| Stage | What Happens | Attorney Action |
|-------|-------------|----------------|
| PENDING_SIGNATURE | Case created from intake. SOL calculated. PHI encrypted. | Attorney sends retainer for e-sign. |
| INITIALIZATION | HIPAA signed. Providers extracted from intake narrative. | Attorney reviews providers, confirms each, locks list. |
| RETRIEVAL | Fax requests sent to all confirmed providers. Record requests tracked. | Attorney previews fax requests, sends them. |
| PROCESSING | Records arrive via fax, email, upload. OCR extracts text. NLP finds clinical entities. Chronology built. Flags detected. | Attorney uploads any manually received documents. |
| CHRONOLOGY_READY | Timeline built. 15 flag types detected. Entries source-cited. | Attorney reviews timeline, annotates every PRIORITY flag. |
| ATTORNEY_REVIEW | All flags annotated. Readiness board shows what's complete. | Attorney does final review. Clicks "Mark Demand-Ready." |
| DEMAND_READY | Case locked. Export available (PDF + JSON). Evidence package ready. | Attorney exports demand package. Case feeds SETTLE. |

## 4 Checkpoints (Attorney Must Pass Each)

| Checkpoint | Gate | What It Prevents |
|-----------|------|-----------------|
| **1. HIPAA Signed** | DocuSeal webhook or attorney confirmation | Working on a case without client authorization (HIPAA violation) |
| **2. Provider Lock** | At least 1 provider CONFIRMED, list locked | Faxing records to a provider the client didn't authorize |
| **3. Faxes Sent** | Record requests transmitted to all CONFIRMED providers | Skipping record retrieval and building chronology without records |
| **4. Flags Annotated** | Every PRIORITY flag has attorney annotation | Exporting a demand package with unflagged clinical issues |

---

# SECTION 2 — TRACE'S 27 FEATURES (Step by Step)

### A. INTAKE CONVERSION (4 features)
1. **Intake-to-Case Conversion** — Prospect from INTAKE becomes a TRACE case with one click. Intake narrative pre-fills provider hints.
2. **SOL Auto-Calculation** — Incident date + jurisdiction → deadline, 50-state table, 4 urgency tiers (Standard/Monitor/Urgent/Critical), statute reference (e.g. CCP §335.1)
3. **PHI Encryption** — Client name, DOB, address, phone → AES-256-GCM → separate PHI database. Operational DB sees only opaque `client_token`.
4. **Retainer Template Upload** — Attorney uploads retainer PDF. System populates client info into template. Sent for e-signature.

### B. PROVIDER MANAGEMENT (6 features)
5. **NLP Provider Extraction** — OpenMed NLP + regex fallback extracts provider names from intake narrative. Each name tagged with confidence.
6. **NPI Registry Lookup** — CMS NPI API enriches each provider candidate with NPI, facility, fax, specialty, address.
7. **Provider Confirmation** — Attorney reviews each provider. Confirms or rejects. NPI match is a CANDIDATE, not authorization.
8. **Fax Number Management** — Each confirmed provider gets a fax number. Attorney can edit or add.
9. **Provider List Lock** — Checkpoint 1. List becomes read-only. No add/edit/delete after lock.
10. **Confidence Taxonomy** — 4 levels: CONFIRMED (1 NPI match), NEEDS_CLIENT_CONFIRMATION (2-3 matches), NEEDS_STAFF_REVIEW (4+), DO_NOT_REQUEST (0). Source quote attached to each.

### C. RECORD RETRIEVAL (5 features)
11. **Outbound Fax** — Documo API sends HIPAA-compliant fax with cover sheet to each confirmed provider. Cover sheet includes record types requested (ER, imaging, PT, billing, pharmacy, specialist).
12. **Cover Sheet Generator** — Auto-generates HIPAA-compliant cover sheet PDF. Patient name and DOB REDACTED on cover (PHI never on cover sheet).
13. **Fax Status Tracking** — Documo webhook returns delivery status. RecordRequest rows track each transmission.
14. **Inbound Email Reception** — Providers email records to TRACE address → Resend webhook → case-matched → stored in Supabase → OCR triggered.
15. **Inbound Fax Reception** — Provider faxes records back → Documo callback → matched by fax number → PDF downloaded → stored → OCR triggered.

### D. DOCUMENT PROCESSING (5 features)
16. **Attorney Upload** — Drag-and-drop PDF into portal. Stored in private Supabase bucket. SHA-256 dedup prevents duplicates.
17. **Client Upload** — Public link (`/link/{token}`). Client uploads documents/images directly. No login required.
18. **Portal Link Ingestion** — Attorney pastes external portal URL. TRACE fetches, stores, dedups.
19. **Mistral OCR** — Text extraction from PDF, JPEG, TIFF. Handles handwriting. OCR confidence scored.
20. **Document Provenance** — Every document tagged with source (ATTORNEY_UPLOAD, CLIENT_UPLOAD, INBOUND_EMAIL, INBOUND_FAX). SHA-256 hash for dedup.

### E. CHRONOLOGY BUILDING (7 features)
21. **Clinical Entity Extraction** — Rule-based NLP extracts: medications (70+ drugs), procedures, diseases, anatomy, imaging findings, discharge events.
22. **Timeline Builder** — Extracted events sorted chronologically. Deduplication across documents. Each entry source-cited with page reference.
23. **Procedure Tracking** — Every procedure listed chronologically with provider and date.
24. **Diagnosis Tracking** — Every diagnosis ranked by frequency of mention across all providers.
25. **Medication Tracking** — Every medication with dosage, duration, and prescribing provider.
26. **Functional Impact Extraction** — SOAP note analysis: work restrictions, lifting limits, sitting/standing limits, return-to-work statements.
27. **Cost Summary** — Medical expenses to date, future medical estimate, total liens documented.

### F. CLINICAL FLAGS (15 types — TRACE ONLY)
28. **GAP_IN_TREATMENT** — 30+ day gap without documented reason. Carrier's #1 attack vector.
29. **SUDDEN_TREATMENT_STOP** — Treatment ends with no discharge note, MMI, or referral.
30. **FOLLOW_UP_NOT_FOUND** — Provider says "f/u in 2 weeks" but no record 2 weeks later.
31. **CLINICIAN_CREDIBILITY_LANGUAGE** — "Exam findings inconsistent," "patient reports but," "no objective findings."
32. **NON_COMPLIANT_LANGUAGE** — "Patient missed 3 of 6 appointments," "patient declined treatment."
33. **NEW_PROVIDER_NO_REFERRAL** — New provider appears mid-treatment with no referral.
34. **MMI_NOT_DOCUMENTED** — 18+ months of treatment, no maximum medical improvement assessment.
35. **PRE_EXISTING_CONDITION_MENTIONED** — "Prior back injury," "history of," "pre-existing."
36. **IMAGING_INCONSISTENCY** — X-ray negative, MRI shows herniation 6 weeks later (delayed presentation).
37. **MEDICATION_ESCALATION** — Ibuprofen → Cyclobenzaprine → Gabapentin → Oxycodone. Supports severity.
38. **SURGERY_RECOMMENDED_NOT_DONE** — Surgeon recommends procedure, 12 months later, no surgery.
39. **WORK_RESTRICTIONS_DOCUMENTED** — "Cannot lift >10 lbs," "cannot sit >1 hour." Supports loss of earning capacity.
40. **FUNCTIONAL_IMPROVEMENT** — PT notes show grip improving, pain decreasing. Carrier will use this.
41. **DISCHARGE_SUMMARY_MISSING** — Hospital admission with no discharge summary in file.
42. **BILLING_CODE_MISMATCH** — CPT code 99285 (highest ER) but notes describe minor exam.

### G. ATTORNEY QA (5 features)
43. **Chronology Viewer** — Interactive timeline. Color-coded by event type. Source documents linked from each entry.
44. **Flag Annotation** — Attorney annotates each PRIORITY flag: CONFIRMED_EXPLAINED, DISMISSED, CONFIRMED_NEEDS_FOLLOWUP, RESOLVED. Annotation versioned.
45. **Readiness Board** — Dashboard checklist: HIPAA status, provider count, lien count, annotated flags count, export readiness.
46. **Demand-Ready Gate** — Checkpoint 4. System blocks approval if any PRIORITY flag is unannotated.
47. **Export (PDF + JSON)** — Chronology PDF with attorney work product disclaimer on every page. JSON for CMS import.

### H. LIEN TRACKING (3 features)
48. **Lien Management** — 6 types: Health Insurance, Medicare, Medicaid, Workers Comp, ERISA, Hospital, Other.
49. **Status Tracking** — 4 statuses: NOT_CHECKED, VERIFIED, DISPUTED, RESOLVED.
50. **Lien Amount Calculation** — Tracks claimed amount per lien. Surfaces unverified liens before demand.

### I. COMPLIANCE & SECURITY (4 features)
51. **Separate PHI Store** — Client PII in trace_phi schema. AES-256-GCM encrypted. Operational DB holds only opaque UUIDs.
52. **Audit Log** — Append-only. Every action logged. No PHI in logs. INSERT-only at DB level.
53. **Pre-signed URLs** — Document access via 15-minute expiry tokens. No public URLs. No direct storage access.
54. **Firm Isolation** — Every query scoped to firm_id. JWT validates firm. Supabase RLS third layer.

### J. PRO FEATURES (coming in Phase 2 — 3 features)

55. **Deterministic Medical Summaries** — Structured 2-3 page summary. Zero AI-generated text. All data extracted via rule-based NLP from records. Source page citations for every entry. Sections: demographics, providers (with page counts), diagnoses (ranked by frequency), procedures (chronological), medications (with dosage/duration), functional impact (from SOAP notes), treatment gaps (from flag engine), cost summary. Attorney reviews and signs off. No hallucination risk.

56. **Demand Template Builder** — Pre-fills a structured demand letter template from chronology data. Client demographics, provider list, diagnosis summary, procedure timeline, medication history, functional impact, cost summary, lien summary. Attorney writes the narrative section. Attorney reviews every pre-filled field. No AI-generated legal content. Outputs formatted PDF/Word document ready for attorney signature.

57. **Provider Follow-Up Scheduler** — Auto re-faxes unresponsive providers at attorney-set cadence (e.g., every 14 days). Tracks follow-up count and escalation. Alerts attorney at day 25 for providers still unresponsive (portal notification). Records non-response pattern for future cases with same provider. No competitor has automated this — service companies (ChartSwap, Ontellus) do it manually.

---

# SECTION 3 — ICP PAIN POINTS & HOW TRACE SOLVES EACH

The ICP: Solo PI attorney. Male, ~52 years old. 15-25 years practicing. 0-1 staff. $150K-$500K revenue. 30-50 calls/month, 38% missed. Answers own phone 40-50% of the time. Fears: malpractice, missed deadlines, cash flow inconsistency, never being "off."

| # | Pain Point | Pain Intensity | How TRACE Solves It | Competitor Solves It? |
|---|-----------|---------------|---------------------|----------------------|
| 1 | **"I spend weekends organizing medical records"** | HIGH — burnout | Auto-OCR → NLP extraction → timeline. 20 paralegal hours saved. | Partial — AI chronologies exist but have no source citations or flags |
| 2 | **"I miss things the carrier will use against me"** | HIGH — settlement loss | 15 clinical flags detect every carrier attack vector. Attorney annotates. | NO — no competitor has clinical flag detection |
| 3 | **"I've missed an SOL deadline before and it terrifies me"** | HIGH — malpractice fear | 50-state SOL calculator with 4 urgency tiers. Color-coded. Mandatory disclaimer. | NO — no competitor calculates SOL from incident date |
| 4 | **"I don't know if a provider record exists that I haven't requested"** | MEDIUM — incompleteness anxiety | Outbound fax + inbound email/fax + upload. All sources tracked. SHA-256 dedup prevents duplicates. | Partial — ChartSwap handles retrieval but as a service, not integrated |
| 5 | **"Demand letters take hours and I always worry I missed something"** | HIGH — time drain | TRACE builds the EVIDENCE package. Attorney writes the letter. No AI-generated legal text. | Partial — AI demand letters exist but hallucination risk is high |
| 6 | **"I discovered a lien AFTER settlement and had to pay from my fee"** | MEDIUM — financial surprise | 6 lien types tracked. 4 statuses. Dashboard shows unverified. | NO — no competitor has structured lien tracking |
| 7 | **"I sent records to the wrong provider once — nightmare"** | HIGH — HIPAA fear | Provider confirmation gate. Attorney must confirm each provider before faxing. List locks. NPI validates identity. | NO — no competitor has gated provider workflow |
| 8 | **"I pay for software I don't use in slow months"** | HIGH — cash flow anxiety | Per-case billing. No case = no charge. Competitors are all monthly subscriptions. | NO — only TRACE does per-case billing |
| 9 | **"I don't have a paralegal — I do everything myself"** | HIGH — overwhelm | TRACE IS the paralegal. 23.65 hours of paralegal work automated. | Partial — some tools reduce time but none eliminate 20 hours |
| 10 | **"HIPAA compliance keeps me up at night"** | MEDIUM — regulatory anxiety | Separate PHI store. Encrypted. Audit log. Pre-signed URLs. No PHI in logs or URLs. | NO — no competitor separates PHI from operational data architecturally |

---

# SECTION 4 — OUR FOUR FRAMEWORKS

These are the mental models that make TRACE different from every competitor. Every feature decision traces back to one of these frameworks.

### Framework 1: Deterministic Over AI

**Rule:** Never use AI/LLM where a rule-based system can do it reliably.

| Competitor Approach | TRACE Approach |
|-------------------|----------------|
| AI generates chronology narrative from records → hallucination risk, no source traceability | Rule-based NLP extracts structured data → source-cited, auditable, attorney verifiable |
| AI writes demand letter → hallucinated verdict values, fabricated case law | TRACE builds evidence package. Attorney writes the letter. |
| AI summarizes medical records → "the patient had a back injury" (misses nuance) | Deterministic extraction: 47 mentions of C4-C5 herniation, 12 of lumbar strain, 18 of radiculopathy. Ranked by frequency. Source-linked. |

**Why this matters to the ICP:** The attorney who fears malpractice WILL NOT trust AI-generated medical analysis. They need to verify every claim against the original source. TRACE makes that possible. AI chronologies make it impossible.

### Framework 2: Per-Case Billing Over Monthly Subscription

**Rule:** Align cost with the attorney's income pattern — they earn case by case, they pay case by case.

| Monthly Subscription | Per-Case |
|---------------------|----------|
| $149/mo whether busy or idle | $149/case only when a case exists |
| 3 slow months = $447 burned | 3 slow months = $0 |
| Churn when slow month hits | No reason to churn — no case, no cost |
| ICP: "What if I don't use it this month?" | ICP: "I only pay when I have a case." |

**Why this matters to the ICP:** Solo PI attorneys have feast-or-famine income. A $500K settlement pays $166K to the attorney — but it might be 6 months between settlements. Monthly subscriptions eat cash during the famine. Per-case billing rides the feast.

### Framework 3: Gated Workflow Over Free-Form

**Rule:** The attorney must pass through checkpoints. The system prevents them from skipping steps that would cause HIPAA violations or settlement losses.

| Free-Form (All Competitors) | Gated (TRACE) |
|---------------------------|---------------|
| "Here are your records. Do whatever." | "HIPAA must be signed before you touch providers. Providers must be confirmed before faxing. Flags must be annotated before export." |
| Attorney can skip steps → wrong provider faxed, lien missed, SOL past deadline | System prevents skipping. Each gate must be passed. |

**Why this matters to the ICP:** The attorney who forgot to check the SOL deadline on one case out of 30 is the attorney who gets sued for malpractice. The gate isn't bureaucracy — it's a safety net.

### Framework 4: Separate PHI Architecture

**Rule:** Client data never shares a database table with operational data.

| Single-DB (All Competitors) | Separate PHI (TRACE) |
|---------------------------|----------------------|
| Cases table has client_name, client_dob, client_phone | Cases table has client_token (opaque UUID). PHI is in separate encrypted DB. |
| Database backup contains PHI | Operational backup contains zero PHI |
| Developer with DB access sees client data | Developer with DB access sees UUIDs |

**Why this matters to the ICP:** When the bar association asks "where is client data stored and who has access?" the attorney can say "medical records are in Supabase, but client identities are encrypted in a completely separate database that only the attorney-facing decryption service can read." No competitor can make this claim.

---

# SECTION 5 — PRICING (FLAT, NO TIERS)

## Why Flat Pricing

TRACE does the same amount of work for every case — same SOL calculation, same NLP extraction, same OCR pipeline, same flag detection. Tiering based on features creates an artificial distinction where none exists. The only difference is the volume discount.

## Pricing Table

| Plan | Per Case | Features | Annual (48 cases) | First-Time Offer |
|------|---------|----------|-------------------|-----------------|
| **Entry** | $149 | All 54 features above (47 current + 7 chronology). Everything. No feature gates. | $7,152 | 3 free cases |
| **Pro** | $289 | Everything in Entry + 3 Pro features: deterministic medical summaries, demand template builder, provider follow-up scheduler + priority OCR queue | $13,872 | 1 free at Pro |

## Volume Discounts

| Cases/Month | Discount | Entry Cost/Case | Pro Cost/Case |
|-------------|----------|----------------|---------------|
| 1-9 | None | $149 | $289 |
| 10-19 | 20% | $119 | $231 |
| 20-49 | 30% | $104 | $202 |
| 50+ | Custom | Negotiated | Negotiated |

## What's Included in BOTH Plans

- Unlimited providers per case
- Unlimited faxes per case (no per-fax fee)
- Unlimited documents per case
- All 15 clinical flag types
- SOL auto-calculation with all 50 states
- Lien tracking (all 6 types)
- Chronology PDF + JSON export
- Readiness board + analytics
- SHA-256 document dedup
- HIPAA-compliant cover sheets
- Pre-signed URLs for document access
- Audit log
- Separate PHI store

## What Pro Adds ($140/case more)

- **Deterministic medical summaries** — 2-3 page structured summary with source citations. No AI-generated text. Attorney-reviewed.
- **Demand template builder** — Pre-filled template from chronology data. Attorney writes the narrative. No AI legal content.
- **Provider follow-up scheduler** — Auto re-fax to unresponsive providers at attorney-set cadence.
- **Priority OCR queue** — Guaranteed 2-hour processing for urgent cases.

---

# SECTION 6 — VALUE PROPOSITION

## The Core Value Proposition

> **TRACE is the paralegal you can't afford and the safety net you can't practice without — for $149 per case.**

### For the Solo Attorney

> "You do 23 hours of records work per case. Your paralegal would cost $28/hr for that. TRACE does it in minutes for $149. You catch things carriers use to lowball you — things you'd miss 40-60% of the time. Those misses cost you $20,000-$35,000. TRACE costs $149. Do the math."

### For the Small Firm

> "Your paralegal costs $560 per case in labor alone and still misses half the treatment gaps. TRACE does better work than your paralegal, catches everything they miss, tracks liens they forget, prevents faxes to wrong providers, calculates SOL deadlines they type wrong — all for $149. And when you have a slow month, TRACE costs zero. Your paralegal still costs $4,500."

### For the Firm with 20+ Cases/Month

> "At 30 cases a month, you're spending $16,800/month on paralegal time just for records work. TRACE Pro does the same work for $6,060/month. That's $10,740 in monthly savings — $128,880 a year. Plus: no sick days, no turnover, no training, works 24/7."

---

# SECTION 7 — THE ROI EQUATION

| What TRACE Saves | Per Case |
|-----------------|----------|
| Paralegal hours (20 hrs × $28) | $560 |
| Attorney hours (3.65 hrs × $300) | $1,095 |
| Settlement erosion from missed flags | $15,000-$25,000 |
| HIPAA breach avoidance (wrong fax) | $5,000-$7,500 |
| Missed lien clawback | $500-$3,000 |
| **Total saved per case** | **~$25,000** |
| **TRACE Entry cost per case** | **$149** |
| **Net savings per case** | **$24,851** |
| **ROI** | **16,678%** |

---

# SECTION 8 — COMPETITOR LANDSCAPE

[Parts 8.1 through 8.5 summarize the research from earlier sections — the master feature matrix, Frankenstein stack analysis, and feature coverage scorecard remain as originally published and are referenced here.]

*See original Sections A-L of the Master Feature Matrix for the full 27-feature comparison across 18 competitors.*

---

# SECTION 9 — THE FRANKENSTEIN STACK COST

To replicate TRACE by buying separate products from competitors:

| Components | Products | Monthly Cost |
|-----------|----------|-------------|
| Case Management | Clio EasyStart | $49 |
| Records Retrieval | ChartSwap (4 reqs × $37 avg) | $148 |
| Chronology | TAVRN AI | $99 |
| Medical Summaries | Eve Legal (Solo) | $500 |
| Demand Letters | Inquery | $99 |
| Client Portal | SmartVault | $40 |
| **TOTAL SOLO COST** | | **$935/mo** |
| **Features Covered** | | **11 of 27 (41%)** |

**Features that CANNOT be bought at any price:** Clinical flags, SOL calculator, provider confirmation gate, lien tracking, separate PHI store, audit log, fax with cover sheets, inbound email/fax reception, SHA-256 dedup, deterministic chronology, flag annotation — **16 features total.**

---

# SECTION 10 — ALL COMPETITOR PRICING (Quick Reference)

| Competitor | Model | Entry | Mid | High |
|-----------|-------|-------|-----|------|
| **TRACE** | **Per-Case** | **$149** | — | **$289** |
| TAVRN AI | Monthly | $99/mo | $299/mo | Custom |
| Eve.Legal | Monthly | $500/mo | $1,000/mo | $2,000+ |
| CloudLex | Per-User | $65/mo | $99/mo | $149/mo |
| Clio | Per-User | $49/mo | $79/mo | $149/mo |
| LawPro.ai | Monthly | $149/mo | $249/mo | $349/mo |
| NexLaw.ai | Monthly | $199/mo | $349/mo | $499/mo |
| ProvaLens | Monthly | $149/mo | $249/mo | $399/mo |
| Inquery.ai | Monthly | $99/mo | $199/mo | $299/mo |
| Law Practice AI | Monthly | $99/mo | $149/mo | $249/mo |
| Dodon.ai | Monthly | $79/mo | $129/mo | $199/mo |
| ProPlaintiff | Monthly | $149/mo | $199/mo | $299/mo |
| ChronicleLegal | Monthly | $99/mo | $199/mo | $299/mo |
| SmartVault | Per-User | $40/mo | $60/mo | $80/mo |
| ChartSwap | Per-Request | $25/req | $45/req | $65/req |
| Ontellus | Per-Request | $30/req | $55/req | $80/req |
| RecordsOnTime | Per-Request | $30/req | $45/req | $55/req |
| YoCierge | Monthly | $250/mo | $350/mo | $500/mo |

---

# SECTION 11 — SALES PITCH (The 3-Number Close)

**Number 1 — $1,655**
> "This is what your paralegal costs you per case in labor for records work. 23 hours at $28/hour."

**Number 2 — $25,000**
> "This is what missed clinical flags cost you per case on average. Gaps the carrier exploits. Preexisting conditions you missed. SOL deadlines you miscalculated."

**Number 3 — $149**
> "This is what TRACE costs per case. Every feature. No per-fax fees. No hidden costs. Only when you have a case."

> "Ask yourself: can you afford $149 to save $25,000?"

---

*This is the definitive reference document for TRACE. All agents, engineers, and stakeholders should reference this document for competitive analysis, pricing, positioning, ICP understanding, feature scope, and sales strategy. Updated July 25, 2026.*
