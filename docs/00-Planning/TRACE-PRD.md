# TRACE — Product Requirements Document
## Treatment Record Acquisition and Chronology Engine
**Version:** 0.1 — Internal Working Draft  
**Status:** Pre-build — Early Access Scoping  
**Owner:** TrueVow Technologies  
**Classification:** Confidential — Not for External Distribution  
**Last Updated:** July 2026

---

## 1. Executive Summary

TRACE is TrueVow's second-stage pipeline product, designed to automate the medical record retrieval, organization, and chronology build that currently consumes 12–18 hours of manual attorney or paralegal time per PI case. It sits between INTAKE (which captures the opportunity) and SETTLE (which protects its value), completing the pre-litigation intelligence pipeline: **Capture → Build → Protect.**

TRACE is not a general-purpose medical record retrieval service. It is a structured workflow layer built specifically for PI cases that have already converted to signed retainers through the TrueVow INTAKE system. That constraint is the product's defining architecture decision — it enables HIPAA authorization capture at retainer signing, provider identification from Benjamin's structured intake record, and economics aligned to the attorney's contingency revenue cycle.

Early access is limited to PIPELINE and OPERATIONS subscribers with active INTAKE. TRACE processes retainer-converted cases only. The attorney reviews all output before it is used for any legal purpose.

---

## 2. Problem Statement

### 2.1 The Bottleneck

After a PI attorney signs a retainer, the case enters a dead zone. The client is signed. The case is real. But before any demand can be prepared, medical records must be retrieved from every provider the client saw — and that process is broken.

The full manual workflow costs the attorney or their staff 12–18 hours per case spread across 4–10 weeks:

| Step | Manual Time | Who Does It |
|------|------------|-------------|
| Provider identification and authorization prep | 1–2 hrs | Attorney or staff |
| Record request submission (fax, portal, or mail per provider) | 1–2 hrs | Staff |
| Follow-up on non-respondents (every 10–14 days) | 2–4 hrs cumulative | Staff |
| Record organization and indexing on arrival | 3–5 hrs | Staff or attorney |
| Chronology build, gap detection, billing reconciliation | 8–12 hrs | Attorney or paralegal |
| **Total** | **15–25 hrs** | **Attorney + staff** |

For a solo PI attorney with no paralegal, all of this is attorney time at $288/hour in opportunity cost. The result: settlement-ready cases sit in a preparation queue for 6–12 weeks while the attorney's limited capacity is consumed by records administration rather than legal work.

56% of PI professionals cite medical record summarization as the most in-demand AI capability. Manual chronologies miss approximately 37% of potentially case-relevant medical details. Cases that are ready to demand stall before demand because the records aren't organized.

### 2.2 Why Existing Solutions Don't Serve This ICP

EvenUp, Tavrn, Supio, and ProPlaintiff all address this problem — but for the wrong buyer. They are priced and designed for firms with dedicated paralegal staff managing 50–200+ cases. Enterprise-priced, enterprise-integrated, enterprise-supported. The solo attorney managing 20–30 active cases with no paralegal is effectively unserved.

TRACE enters at per-case flat-rate pricing, automated retrieval initiation seeded from Benjamin's intake record, and a paralegal-optional attorney QA workflow. It makes the same outcome accessible to the attorney who cannot afford the enterprise alternatives.

### 2.3 The Unique Structural Advantage

No competitor can replicate TRACE's pipeline integration. Benjamin's structured intake record already contains:
- Provider references mentioned during the intake call
- Injury type and treatment status signals
- Jurisdiction and incident timing data

These fields seed TRACE's provider identification automatically. A competitor starting from scratch asks the attorney to manually enter provider information. TRACE starts with what Benjamin already captured and asks the attorney to confirm, not create. That is a meaningfully different user experience and a defensible technical moat.

---

## 3. Product Scope

### 3.1 What TRACE Does

0. **Document package signing (DocuSeal)** — Before any record request can be sent, the client must sign the retainer and HIPAA authorization. TRACE generates the complete signing package and sends it to the client via DocuSeal — a self-hosted open-source electronic signature tool deployed within TrueVow's Fly.io HIPAA boundary. The client signs on their phone in under 3 minutes. No printing. No scanning. No office visit. The attorney's signature is pre-applied via a template. The signed PDF with embedded audit trail is stored automatically in the case record. TRACE case initialization completes only when DocuSeal confirms all required signatures are complete.

1. **Provider identification** — Extracts provider references from Benjamin's intake record using NLP. Cross-references against the NPI Registry for complete provider details. Surfaces a confirmation checklist to the attorney before any request is sent.

2. **HIPAA-authorized record requests** — Generates and transmits HIPAA-compliant record requests to all confirmed providers using encrypted cloud fax infrastructure. Uses the signed HIPAA authorization captured via DocuSeal at retainer signing. Attorney approves the outgoing request list before transmission.

3. **Retrieval tracking and follow-up** — Tracks provider response status. Sends automated follow-up requests at day 10 and day 20. Flags overdue requests at day 30 for attorney attention. Surfaces incomplete responses for attorney resolution.

4. **Record organization and indexing** — Processes incoming records through OCR and document parsing. Classifies documents by type (ER records, imaging, PT notes, billing, pharmacy, specialist notes). Organizes by provider and date. Flags duplicate pages and misfiled documents.

5. **Chronology generation** — Builds a structured treatment chronology with every clinical event extracted, dated, categorized, and source-cited to the exact document and page number. Every entry is traceable.

6. **Gap detection** — Identifies date ranges with no recorded treatment across any provider in the record set. Flags gaps for attorney annotation — confirmed explained, or requiring follow-up. Does not interpret why gaps exist.

7. **Billing reconciliation** — Cross-references billing statements against clinical records. Flags treatment dates with no corresponding bill and bills with no corresponding treatment record. Does not interpret billing discrepancies — surfaces them for attorney review.

8. **Attorney QA delivery** — Delivers the completed chronology to the attorney portal with all flagged items highlighted. Attorney annotates, confirms, or dismisses each flag before the chronology is marked demand-ready.

### 3.2 What TRACE Explicitly Does Not Do

- Provide legal advice of any kind
- Interpret clinical findings or treatment outcomes
- Assess case value, damages, or settlement potential (that is SETTLE's job)
- Generate demand letters or any attorney work product
- Run conflicts checks
- Replace attorney review at any stage
- Make the chronology available for any legal purpose before attorney approval
- Share any client PHI with any party other than the requesting attorney's firm

---

## 4. User Stories

### 4.1 Primary User — Solo PI Attorney (PIPELINE or OPERATIONS subscriber)

**Story 0 — Document package signed**
*As a solo PI attorney who has decided to proceed with a case after reviewing the Benjamin intake record, I want to send the client the retainer and HIPAA authorization for electronic signature without requiring them to come to my office, print anything, or create an account, so that the case starts the same day the intake call happens.*

Acceptance criteria:
- Attorney clicks "Send for Signature" in the TRACE portal — one button, no configuration required per case
- Client receives a text message and email within 2 minutes containing a direct signing link (no app download, no account creation required)
- Client signs on any device — phone, tablet, or desktop — using finger or mouse
- Attorney signature is pre-applied automatically via the firm's configured DocuSeal template
- Signed PDF package with embedded audit trail is stored in Supabase Storage and linked to the case record
- HIPAA authorization status updates to SIGNED in the case manifest
- Attorney receives a portal notification and email: "Client has signed. Provider list ready for your review."
- TRACE case initialization completes automatically — attorney does not need to trigger it manually
- If client has not signed within 24 hours: automated reminder sent to client. Attorney notified at 48 hours
- Signed documents are retained for minimum 6 years per HIPAA and state bar requirements
*As a solo PI attorney who has just signed a retainer through the TrueVow portal, I want TRACE to automatically identify the providers Benjamin mentioned during intake and prepare a record request list for my review, so that I do not have to start the records process from scratch.*

Acceptance criteria:
- TRACE surfaces a provider identification checklist within 24 hours of retainer conversion being marked in the portal
- The checklist is pre-populated with providers extracted from the Benjamin intake record
- Each provider entry shows: name, facility, specialty, NPI number (where found), and the source reference in the intake record
- Attorney can add, remove, or correct any entry before approving
- Attorney must explicitly approve the list before any request is transmitted

**Story 2 — Record requests transmitted**
*As a solo PI attorney who has approved the provider list, I want TRACE to send HIPAA-compliant record requests to all confirmed providers automatically, so that I do not have to prepare and send individual fax requests to each provider.*

Acceptance criteria:
- TRACE generates a correctly formatted HIPAA records request for each provider using the signed authorization on file
- Requests include the client's name, date of birth, date of incident, dates of service requested, and the signed authorization
- Requests are transmitted via HIPAA-compliant encrypted cloud fax infrastructure
- Attorney receives a confirmation that requests were transmitted, with timestamps and fax confirmation numbers
- No request is transmitted without the attorney's prior approval of the provider list

**Story 3 — Follow-up tracking**
*As a solo PI attorney, I want to know which providers have not responded without having to track it myself, so that I can focus on legal work rather than records administration.*

Acceptance criteria:
- TRACE sends automated follow-up requests at day 10 and day 20 of non-response
- Attorney receives a status summary at day 15 showing which providers have responded and which have not
- At day 30, unresolved non-respondents are flagged in the portal with escalation options: attorney follow-up call, certified mail backup, or legal demand for records
- Attorney can mark any provider as resolved or pending at any time

**Story 4 — Chronology delivered**
*As a solo PI attorney who has received complete records, I want a structured treatment chronology with every clinical event dated, categorized, and source-cited, so that I can review the complete medical picture in 30 minutes rather than 10 hours.*

Acceptance criteria:
- Chronology lists every clinical event with: date, provider, facility, event type, clinical description (from the record, not interpreted), and source citation (document name, page number)
- Events are organized chronologically across all providers
- All flags from the Extended Flag Registry (Section 5.5.3) are surfaced with their priority level, source citation, and attorney annotation field:
  - PRIORITY flags: treatment gaps ≥14 days, billing discrepancies, delayed initial treatment ≥8 days, sudden treatment stop without discharge/MMI, follow-up with no record (imaging/specialist), non-compliant language, bill with no procedure report, clinician credibility language, changing incident description, pre-existing condition signal
  - ADVISORY flags: delayed initial treatment 4–7 days, new provider without referral, changing symptom complaints, routine follow-up with no record
  - INFORMATIONAL tags: functional impact entries, imaging cross-reference links
- Chronology cannot be marked demand-ready until all PRIORITY flags have attorney annotations
- Export available as structured PDF and structured JSON for case management system import

**Story 5 — QA and approval**
*As a solo PI attorney reviewing the TRACE chronology, I want to annotate flags and approve the final output, so that I am clearly in control of the work product before it is used in any demand or negotiation.*

Acceptance criteria:
- Attorney annotates each flagged item individually
- System tracks which items were reviewed by the attorney and when
- Attorney signs off on the completed chronology with a dated approval action
- Approval action is logged with attorney name, date, and timestamp in the audit trail
- Chronology status changes to "Demand-Ready — Attorney Approved" only after this action
- The disclaimer ("Generated by TRACE. Does not replace attorney judgment. Not legal advice.") appears on every exported page

### 4.2 Secondary User — Small Firm Attorney (2–3 attorneys, OPERATIONS subscriber)

Same stories as above with the addition:

**Story 6 — Multi-matter visibility**
*As an attorney at a small firm with multiple active TRACE cases, I want to see the status of all TRACE cases in one view, so that I can prioritize which cases need my attention without opening each one individually.*

Acceptance criteria:
- Portal dashboard shows a TRACE case list with: client identifier (tokenized until attorney clicks through), stage (Provider Confirmation / Requests Transmitted / Records In Progress / Chronology Ready / Attorney Review / Demand-Ready), days in current stage, and any flags requiring attention
- Attorney can sort by stage or by days in stage
- Cases with overdue provider responses are surfaced at the top of the list with a flag indicator

---

## 5. Functional Requirements

### 5.1 Provider Identification Engine

**5.1.1 NLP extraction from intake record**
- Input: Benjamin's structured intake record (JSON)
- Extract: all provider references mentioned during intake call
- Field targets: hospital name, clinic name, physician name, specialty, geographic reference
- Confidence scoring: High (explicit named provider) / Medium (generic reference with location) / Low (implied provider without name)
- Low-confidence extractions are surfaced to the attorney as "unconfirmed — please verify"

**5.1.2 NPI Registry lookup**
- System queries the CMS NPI Registry API for each extracted provider
- Match criteria: name, specialty, and geographic proximity to the incident location from the intake record
- Returns: NPI number, registered name, address, fax number, phone number
- Where multiple matches exist: surfaces top 3 for attorney selection
- Where no match found: surfaces as "Not found — attorney entry required"

**NPI match is not authorization to fax — this rule must never be violated:**

NPI lookup is candidate enrichment only. It does not authorize a fax transmission. A confirmed NPI match means the provider exists in the public CMS registry. It does not confirm the client received treatment from this specific provider, that the fax number is current and correct, or that the attorney has reviewed and approved this provider for record requests. The distinction matters because a misdirected fax to the wrong provider is a PHI transmission to an unauthorized recipient — a HIPAA incident.

The mandatory sequence is:

```
NPI lookup → candidate with confidence label
                      ↓
         Attorney reviews confirmation checklist
                      ↓
         Attorney explicitly confirms each provider
                      ↓
         Attorney approves outgoing request list (Checkpoint 2)
                      ↓
         Fax transmitted
```

No fax is ever sent on the basis of NPI lookup alone. The Checkpoint 1 gate and the Checkpoint 2 gate (`hipaa_auth_status = SIGNED`) enforce this in code. The rule is also stated in the Attorney Responsibility Addendum.

**5.1.3 Provider confirmation checklist**
- Displays pre-populated provider list to attorney in portal
- Attorney actions per provider: Confirm / Edit / Remove / Add new
- "Add new" field captures: provider name, facility, fax number, address, specialty, approximate dates of service
- Attorney must confirm the complete list before transmission is enabled
- Confirmed list is locked and timestamped after attorney approval

**5.1.4 Statute of Limitations Auto-Calculation**
*(Extracted and adapted from MalpracticeVibe SRD — SOL display concept, July 2026)*
- On case initialization, TRACE reads incident date and jurisdiction from the Benjamin intake record
- System queries a jurisdiction-specific SOL lookup table covering all 50 states and DC
- Personal injury SOL is surfaced as: calculated deadline date, days remaining from today, and urgency label
  - **Standard** — more than 180 days remaining
  - **Monitor** — 90–180 days remaining
  - **Urgent** — 30–90 days remaining
  - **Critical** — under 30 days remaining
- SOL display appears: at the top of every case view in the portal, in the provider confirmation checklist, and in the weekly intake performance report for PIPELINE and OPERATIONS subscribers
- SOL urgency label is visible but does not block any workflow step — it is informational only
- Attorney-facing disclaimer on every SOL display: *"This calculation is based on the standard personal injury statute of limitations for the indicated state and incident date. Tolling provisions, discovery rules, government entity notice requirements, and other state-specific exceptions may apply. The attorney is responsible for confirming the applicable deadline before relying on this calculation for any purpose."*
- Disclaimer is not dismissible — it appears permanently alongside every SOL display
- The lookup table must be reviewed by a licensed attorney in each target state before Phase 3 launch and updated annually or whenever a state legislature amends its SOL statute

### 5.2 HIPAA Authorization and Document Signing

**5.2.0 Document Package Signing via DocuSeal**
*(Added July 2026 — DocuSeal self-hosted e-signature integration)*

Electronic document signing is the gate that starts everything in TRACE. No signature, no case. The signing workflow uses DocuSeal — an open-source, self-hosted electronic signature tool deployed within TrueVow's Fly.io HIPAA boundary. Because DocuSeal runs inside the same HIPAA infrastructure boundary as TRACE, no separate vendor BAA is required.

**Documents in the signing package (generated per case):**

| Document | Signers | Attorney signature required? | Witness required? | Notarization? |
|----------|---------|------------------------------|-------------------|---------------|
| Retainer / Engagement Letter | Client + Attorney | Yes — pre-applied via template | No | No |
| Contingency Fee Agreement | Client + Attorney | Yes — pre-applied via template | No (most states — confirm with healthcare attorney) |
| HIPAA Authorization | Client only | No | No | No (federal baseline) |
| Lien Acknowledgment (if applicable) | Client | No | No | No |

Attorney signature is pre-configured as a template in DocuSeal during TRACE onboarding. It is applied automatically to the appropriate fields when the package is generated — the attorney does not sign each individual document per case.

**Signing workflow:**

```
Attorney reviews Benjamin intake record
        ↓
Attorney clicks "Send for Signature" in TRACE portal
        ↓
TRACE generates document package (retainer + fee agreement + HIPAA auth)
using firm-configured DocuSeal templates
        ↓
Attorney pre-signature applied automatically
        ↓
DocuSeal sends client a text message + email:
"[Firm Name] is ready to represent you.
 Please review and sign your documents here: [link]
 Takes about 3 minutes on your phone."
        ↓
Client taps link — no app, no account, no printing
        ↓
Client signs on phone/tablet/desktop
        ↓
DocuSeal generates tamper-evident signed PDF with embedded audit trail
        ↓
Signed package stored in Supabase Storage (encrypted, private)
Linked to case record by case_id
        ↓
DocuSeal webhook fires → TRACE updates:
  hipaa_auth_status = SIGNED
  case_stage = INITIALIZATION (provider extraction begins)
        ↓
Attorney receives portal notification + email:
"[Client first name] has signed. Provider list is being prepared."
```

**Signing status lifecycle:**

| Status | Meaning |
|--------|---------|
| PENDING | Package generated, not yet sent |
| SENT | Signing link delivered to client |
| PARTIALLY_SIGNED | Some signers complete, waiting on others |
| SIGNED | All required signatures collected |
| EXPIRED | Signing link expired without completion (resend option available) |
| DECLINED | Client declined to sign (attorney notified immediately) |

**Automated reminders:**
- 24 hours after sending: client receives automated reminder if not signed
- 48 hours: attorney receives portal notification that client has not signed
- Attorney can resend the package or call the client from the portal with one click

**Document retention:**
Signed PDFs are stored in Supabase Storage under the `signed-documents` private bucket. Retained for minimum 6 years from case closure per HIPAA and state bar requirements. Included in the firm data destruction process at termination.

**State-specific signing requirements:**
The healthcare attorney must review the signing package for each target state. Some states impose additional requirements on contingency fee agreements (e.g., California requires a separate notice for contingency fees). Personal representative requirements apply when the client cannot sign for themselves — the HIPAA authorization must document the representative's relationship and legal authority. TRACE does not validate state-specific requirements automatically — the attorney is responsible.

**5.2.1 Authorization capture**
- Signed HIPAA authorization from DocuSeal is stored in TRACE with the case record
- Authorization is attorney-specific (names the attorney and their firm as the authorized recipient)
- Authorization status tracked in case manifest (PENDING / SIGNED / EXPIRED)
- Authorization must reach SIGNED status before any record request is transmitted — enforced at the API level (Checkpoint 2 gate)
- If authorization expires before records are fully collected: TRACE alerts the attorney and provides a one-click resend option

**5.2.2 Request generation**
- TRACE generates a compliant records request for each confirmed provider containing:
  - Client full name and date of birth
  - Date of incident (from intake record)
  - Requested dates of service (from intake record + provider confirmation)
  - Specific record types requested (ER records, imaging, billing, PT notes, pharmacy — configurable per case)
  - Signed HIPAA authorization attachment
  - Attorney contact information and return fax number
  - TRACE-assigned case reference number (opaque — no client PII in reference number)
- Request format: PDF with cover sheet compliant with standard medical records request protocols

**5.2.3 Transmission infrastructure**
- All requests transmitted via HIPAA-compliant encrypted cloud fax provider (BAA required — see Section 8)
- TLS 1.2+ in transit, AES-256 at rest
- Delivery confirmation and timestamp logged per provider
- Failed transmissions flagged for attorney attention with retry option
- Alternative transmission paths: secure email where provider supports it, certified mail fallback option

### 5.3 Retrieval Tracking

**5.3.1 Response tracking**
- System tracks response status per provider: Pending / Partial / Complete / Unresponsive
- Incoming records received via: dedicated TRACE secure fax inbox, secure upload portal (attorney or provider-initiated), SFTP
- Records linked to the correct case via TRACE case reference number on the cover sheet

**5.3.2 Automated follow-up**
- Day 10: automated follow-up fax transmitted to non-respondent providers
- Day 20: second follow-up fax transmitted
- Day 25: attorney notification — list of non-respondent providers with days outstanding
- Day 30: escalation flag in portal — attorney selects action per provider: attorney call, certified mail, legal demand letter

**5.3.3 Partial response handling**
- System detects when received records appear incomplete relative to requested dates of service
- Flags partial responses for attorney review: "Records received for [dates] — requested records for [dates] not yet received"
- Attorney can accept partial records as complete or initiate supplemental request

### 5.4 Document Processing Pipeline

**5.4.1 Intake and classification**
- OCR processing for all incoming documents (digital PDF and scanned)
- Handwritten note handling: best-effort OCR with attorney flag for manual review where confidence is below threshold
- Document type classification: ER records / imaging reports / PT/OT notes / specialist notes / primary care / billing / pharmacy / other
- Duplicate detection: SHA256 hash comparison against all existing documents in the case — exact duplicates flagged, attorney confirms before removal
- Misfiled documents: flags documents that appear to relate to a different patient or date range
- Source provenance tracked per document: PROVIDER_FAX / ATTORNEY_UPLOAD / CLIENT_UPLOAD / SCAN / DOCUSEAL_SIGNED

**5.4.1a Document intake paths**

TRACE accepts documents through three paths in Phase 1:

**Path 1 — Provider fax (primary):** Incoming fax from healthcare provider via cloud fax inbox. Linked to case via TRACE reference number on the cover sheet. Source = PROVIDER_FAX. This is the authoritative copy when duplicates exist.

**Path 2 — Attorney manual upload:** Attorney downloads document from client text/email or receives physical copy, scans it, and uploads via the TRACE portal document upload. Source = ATTORNEY_UPLOAD.

**Path 3 — Client secure upload link (Phase 1C):** Attorney generates a one-time upload URL from the TRACE portal and sends it to the client via text or email. Client opens the link on their phone — no account, no password, no TRACE portal access. Client takes a photo or chooses a file and submits. Document lands directly in the case file. Link expires after 48 hours or when attorney revokes it. Source = CLIENT_UPLOAD.

The client upload path does not require building a client portal. It is a single expiring URL per case with a minimal upload page showing only the firm name and the attorney's label. The client never knows what software the attorney uses.

**5.4.1b Deduplication**

When the same document arrives via multiple paths (provider fax and client email scan of the same record), TRACE detects the duplicate and surfaces it for attorney review:

- SHA256 hash computed for every incoming document immediately after storage
- Hash compared against all existing document hashes for the same case
- Exact match found: incoming document flagged as DUPLICATE. Attorney sees both copies with their source labels and confirms which to keep
- No document is ever auto-deleted — attorney must confirm
- Near-duplicate detection (same content, different scan quality) is Phase 2 scope
- Provider fax copy is always the authoritative copy when duplicates exist — attorney confirmation reflects this as the default recommendation, not a hard rule

**5.4.2 Indexing**
- All processed documents indexed by: provider, facility, document type, date range, page count
- Master index delivered to attorney alongside chronology
- Source documents remain accessible for citation verification

**5.4.3 Chronology extraction**
- NLP extraction of clinical events from processed documents
- Each event extracted with: date, provider, facility, event type (visit / imaging / prescription / procedure / discharge / referral), clinical description (verbatim from the record — not interpreted), and source citation (document name, page number)
- Events deduplicated across providers where the same clinical event appears in multiple records
- Chronology assembled in date order across all providers

### 5.5 Gap and Discrepancy Detection

**5.5.1 Treatment gap detection**
- Algorithm identifies date ranges of 14 days or more with no recorded treatment across any provider
- Flags: date gap started, date gap ended, gap duration in days, last treatment before gap, first treatment after gap
- Does not interpret why the gap occurred
- Does not surface flags to the opposing party or any third party — attorney-portal only
- Threshold of 14 days is configurable by attorney during case setup (some practice areas may use different thresholds)

**5.5.2 Billing reconciliation**
- Cross-references billing statement dates and CPT codes against clinical event dates in the chronology
- Flags: billing entry with no corresponding clinical record, clinical record date with no corresponding billing entry
- CPT code matching: uses CPT-to-procedure-type mapping to identify likely clinical equivalents even when terminology differs
- Does not interpret billing discrepancies — surfaces them as data observations for attorney review

**5.5.2a Code Extraction and Standardization**
*(Extracted and adapted from MalpracticeVibe SRD audit.py implementation, July 2026 — language and output constraints rewritten to comply with TRACE Prohibited Output Registry)*
- **CPT code extraction:** Pattern matching for 5-digit procedure codes in billing records. Extracted codes mapped to procedure category descriptions (e.g., CPT 99215 → High Complexity Outpatient Management, requires 40+ minutes documented patient contact)
- **ICD-10 extraction:** Pattern matching for standard diagnostic code format (letter + 2 digits + optional decimal + alphanumeric extension). Extracted codes mapped to condition category descriptions
- **Terminology standardization:** Raw CPT and ICD-10 codes mapped to a standardized medical vocabulary (OMOP Common Data Model or equivalent) to resolve terminology variations across provider billing systems. Ensures that "99215 High Complexity Outpatient" in a billing record and "extended office visit" in a clinical note are recognized as the same procedure category before cross-referencing
- **Time and complexity discrepancy detection:** Where a billed procedure code requires documented minimum time or examination elements (per CMS documentation guidelines), and the corresponding clinical note does not contain documentation supporting that minimum, the system flags the discrepancy as a factual observation
- **Attorney-facing output format:** *"Bill dated [date] shows CPT [code] ([procedure description] — requires [minimum documentation standard]). Progress note for same date shows [extracted documentation]. Factual discrepancy — flag for attorney review."*
- **Prohibited output:** The system must never characterize a billing discrepancy as fraud, upcoding, abuse, malpractice, or intentional error. Output is limited to the factual observation of the discrepancy between the billed code's documentation requirements and the clinical note content. The attorney determines the significance and appropriate response
- **False positive target:** Under 15% — no more than 15% of flagged discrepancies should be attributable to terminology format differences rather than actual documentation gaps. OMOP standardization is the primary mechanism for reducing false positives

**5.5.3 Extended Flag Registry**
*Added July 2026 — based on paralegal and physician PI record review research. Covers all flag types a trained paralegal or reviewing physician would identify across a complete PI medical record set. Organized by detection method: Tier 1 (algorithmic — date math and string matching), Tier 2 (NLP-assisted — OpenMed entity extraction and cross-record comparison), Tier 3 (attorney judgment only — TRACE surfaces raw data, never characterizes).*

*All flags in this registry follow the same output constraints as existing gap and billing flags: factual observation only, no legal or clinical interpretation, no prohibited language. Every flag links to source document and page. Every flag requires attorney annotation before demand-ready status is granted on Priority flags.*

---

**TIER 1 FLAGS — Algorithmic detection**

These are built in Phase 1D alongside the existing gap detection and billing reconciliation jobs. No additional NLP required beyond what is already in the pipeline. Detection logic is date math, string matching, and record set completeness checks.

---

**FLAG T1-01 — Delayed Initial Treatment**

*What it detects:* The gap between the incident date (from the intake record) and the first clinical encounter in the chronology. Insurance adjusters and defense counsel treat unexplained delays between incident and first treatment as evidence the injury was not serious or was caused by a subsequent event.

*Detection logic:*
- Input: incident_date from case manifest, first chronology entry date
- Calculate: days between incident_date and first_clinical_entry_date
- Flag thresholds:
  - 0–3 days: no flag (expected ER or urgent care presentation)
  - 4–7 days: ADVISORY flag (surfaced but not Priority)
  - 8–14 days: PRIORITY flag
  - 15+ days: PRIORITY flag with escalated label
- Do not flag if the first entry is a telehealth visit, pharmacy record, or follow-up to a prior visit — these suggest earlier treatment exists

*Attorney-facing output:* "First recorded clinical encounter is [N] days after the reported incident date of [date]. Attorney review recommended — delay may require explanation in demand narrative."

*Prohibited output:* Do not characterize the delay as suspicious, evidence of fraud, or inconsistent with the claimed injury. Surface the data point only.

*Priority level:* PRIORITY if gap ≥ 8 days. ADVISORY if 4–7 days.

---

**FLAG T1-02 — Sudden Treatment Stop Without Discharge or MMI**

*What it detects:* A treatment sequence that ends abruptly — the last chronology entry has no discharge notation, maximum medical improvement (MMI) language, case closure note, or referral to a new provider. This signals either missing records from a final provider visit or a treatment pathway that was abandoned without clinical resolution.

*Detection logic:*
- Identify the last chronology entry for each provider in the record set
- Check the clinical_description of that entry for presence of: "discharged," "MMI," "maximum medical improvement," "case closed," "no further treatment," "released from care," "final visit," "completed treatment," "follow up as needed"
- If none of these terms are present in the last entry from any provider: flag
- Do not flag if a referral to a new provider is present — that provider's records should be in the set

*Attorney-facing output:* "Last recorded treatment entry from [provider] on [date] does not contain a discharge notation, MMI finding, or referral. Attorney review recommended — records may be incomplete or treatment status may be unresolved."

*Priority level:* PRIORITY

---

**FLAG T1-03 — Follow-Up Recommendation With No Corresponding Record**

*What it detects:* A clinical note that documents a follow-up instruction, referral, or diagnostic order with no corresponding entry appearing in the chronology within a reasonable timeframe. This identifies either missing records from the follow-up provider or a gap in treatment compliance that defense counsel will surface.

*Detection logic:*
- String match on clinical_description fields for follow-up language patterns:
  - "follow up in [N] days/weeks"
  - "return in [N] days/weeks"
  - "refer to [specialty]"
  - "referred to [specialty]"
  - "order [imaging type]"
  - "ordered [imaging type]"
  - "schedule [procedure]"
  - "MRI recommended," "CT ordered," "X-ray ordered"
- For each match: check whether a corresponding chronology entry exists from the indicated provider type or for the indicated procedure within 60 days
- If no corresponding entry found: flag with the source entry and the expected follow-up type

*Attorney-facing output:* "Entry dated [date] from [provider] documents [follow-up instruction: verbatim text]. No corresponding [referral type/imaging type] record found within 60 days. Attorney review recommended — records may be missing or follow-up may not have occurred."

*Priority level:* PRIORITY if imaging or specialist referral. ADVISORY if routine follow-up.

---

**FLAG T1-04 — Non-Compliant Language**

*What it detects:* Specific language in clinical notes that documents patient non-compliance with treatment recommendations. Defense counsel searches for these entries actively — they are used to argue that the client's ongoing symptoms are attributable to non-compliance rather than the incident.

*Detection logic:*
- String match on clinical_description fields for the following exact terms and close variants:
  - "non-compliant," "noncompliant"
  - "missed appointment," "no show," "no-show," "failed to appear"
  - "patient did not follow," "did not complete," "did not take"
  - "against medical advice," "AMA," "left AMA"
  - "refused treatment," "declined"
  - "not following recommendations"
- Flag every instance — do not filter by context
- Multiple instances across different providers are flagged as a group with count

*Attorney-facing output:* "Entry dated [date] from [provider] contains non-compliance language: '[verbatim text, max 60 chars]'. [N] total non-compliance notations found across the record set. Attorney review recommended — these entries may require explanation or context in the demand narrative."

*Priority level:* PRIORITY for any instance.

---

**FLAG T1-05 — Bill References Procedure With No Operative or Procedure Report**

*What it detects:* A billing record that includes a CPT code for a surgical procedure, injection, or diagnostic procedure with no corresponding operative report, procedure note, or diagnostic report in the received document set. This is a common missing records signal — facility billing records and physician procedure notes are often stored in separate silos.

*Detection logic:*
- Identify billing entries with CPT codes in surgical or procedural ranges:
  - 10000–69999 (surgery)
  - 70000–79999 (radiology/imaging procedures)
  - 90000–99099 (medicine/injections/infusions)
- For each match: check document set for document_type = IMAGING, OPERATIVE, or PROCEDURE_NOTE from the same provider within 7 days of the bill date
- If no corresponding procedural document found: flag

*Attorney-facing output:* "Bill dated [date] from [provider] shows CPT [code] ([procedure description]). No corresponding operative report, procedure note, or imaging report found in the received document set from this provider. Attorney review recommended — physician records and facility records may be stored separately and require a separate request."

*Priority level:* PRIORITY

---

**FLAG T1-06 — Clinician Credibility Language**

*What it detects:* Language in clinical notes that reflects provider skepticism about the client's reported symptoms or history. These entries do not damage the case clinically but are weaponized by defense counsel to attack the client's credibility. The attorney must know they exist before the deposition, not during it.

*Detection logic:*
- String match on clinical_description fields for:
  - "exaggerating," "exaggerates," "embellishing"
  - "inconsistent history," "inconsistent complaints," "inconsistent with"
  - "malingering," "secondary gain"
  - "subjective complaints only," "no objective findings"
  - "drug seeking," "drug-seeking"
  - "symptoms out of proportion"
  - "functional overlay"
- Flag every instance regardless of context

*Attorney-facing output:* "Entry dated [date] from [provider] contains language that may be used by defense counsel to challenge client credibility: '[verbatim text, max 80 chars]'. Attorney review recommended before demand preparation."

*Priority level:* PRIORITY for any instance.

---

**TIER 2 FLAGS — NLP-assisted detection via OpenMed**

These require OpenMed entity extraction and cross-record comparison. They run in the same Phase 1D sprint as Tier 1 flags — the NLP pipeline is already running for clinical event extraction, so these are extensions of the same pass, not a separate job.

---

**FLAG T2-01 — New Provider Without Referral Context**

*What it detects:* A new provider appearing in the chronology with no preceding referral from an existing provider and no self-referral context (e.g., ER self-presentation, attorney referral). This can indicate either a gap in the care narrative or a provider the client sought independently and did not disclose during intake.

*Detection logic:*
- Track provider introduction events: the first chronology entry from each provider
- For providers introduced after the first encounter: check the preceding 30 days of chronology for a referral entity (FLAG T1-03 detection output) naming that provider or specialty
- If no referral found and the provider is not an ER or urgent care: flag
- Exception: first provider in chronology never flagged (expected — no referral exists yet)

*OpenMed role:* Entity extraction identifies referral target specialties ("refer to orthopedic surgery") and matches them against subsequent provider specialty labels from the NPI Registry.

*Attorney-facing output:* "Provider [name/facility] appears in the chronology on [date] with no preceding referral documented in the record set. Attorney review recommended — referral records may be missing or client may have self-referred."

*Priority level:* ADVISORY

---

**FLAG T2-02 — Changing Incident Description Across Providers**

*What it detects:* Materially different descriptions of how the incident occurred appearing in clinical notes from different providers. Defense counsel uses these discrepancies to attack the client's narrative and argue the incident did not happen as described.

*Detection logic:*
- OpenMed extracts incident description entities from the first 1–2 clinical entries from each provider (ER note, initial intake note, first PT note)
- Target entity types: mechanism of injury ("rear-end collision," "fall," "struck by"), body region initially affected, position at time of incident
- Compare mechanism of injury descriptions across providers
- Flag where mechanism description is materially different across two or more providers (not just varying detail — fundamentally different mechanism)

*OpenMed role:* NER extracts mechanism of injury phrases. Cross-record comparison identifies divergence.

*Attorney-facing output:* "Incident description in records from [Provider A] on [date] states '[verbatim excerpt, max 60 chars]'. Incident description in records from [Provider B] on [date] states '[verbatim excerpt, max 60 chars]'. Factual discrepancy across providers — attorney review recommended."

*Priority level:* PRIORITY

---

**FLAG T2-03 — Changing Symptom Complaints Without Progression Logic**

*What it detects:* Symptom complaints that shift across providers or over time in ways that lack clinical progression logic. A client who reports only neck pain at the ER but reports knee pain as their primary complaint at a physical therapy intake 3 weeks later — with no clinical explanation connecting the two — is a flag.

*Detection logic:*
- OpenMed extracts body region and symptom entities from each chronology entry
- Track the primary complaint body region across providers and over time
- Flag where a new body region appears as a primary complaint with no:
  - Preceding referral or imaging finding explaining the new complaint
  - Progression logic in the notes ("neck pain radiating to shoulder" → new shoulder complaint is expected)
  - Incident description that includes the new region

*OpenMed role:* Anatomy and symptom NER across the full chronology. Body region tracking and progression logic classification.

*Attorney-facing output:* "Symptom complaint of [body region] first appears in records from [provider] on [date], [N] days after the incident. No preceding documentation of [body region] symptoms or referral explanation found in earlier records. Attorney review recommended — complaint progression may require explanation in demand narrative."

*Priority level:* ADVISORY

---

**FLAG T2-04 — Pre-Existing Condition Signal**

*What it detects:* Clinical language in records from after the incident date that references prior conditions, degenerative findings, or pre-existing complaints in the same body regions as the claimed injury. This flag is high priority — it is the most common defense strategy in PI cases.

*Detection logic:*

This flag is only active when the attorney has opted in to pre-incident records processing for the case (PRD §12 Open Question 8 — attorney-controlled per case). Without pre-incident records, TRACE surfaces only post-incident language that itself references prior conditions.

*For cases with pre-incident records opted in:*
- OpenMed NER extracts body region and condition entities from pre-incident records
- Same extraction runs on post-incident records
- Flag where the same body region appears as a complaint or finding in both pre- and post-incident records

*For all cases (pre-incident records not required):*
- String match and NER on post-incident clinical notes for language that itself references prior conditions:
  - "pre-existing," "prior history of," "history of," "chronic," "degenerative," "longstanding"
  - "previously treated," "prior injury," "old injury," "prior surgery"
  - "age-appropriate changes," "degenerative disc disease," "arthritic changes," "spondylosis"
- Flag where these terms appear in the same clinical note that describes the incident-related complaint, or in imaging reports from after the incident date

*OpenMed role:* Body region NER, condition entity extraction, temporal classification (pre- vs post-incident).

*Attorney-facing output:* "Entry dated [date] from [provider] contains language referencing a prior condition in the same body region as the claimed injury: '[verbatim text, max 80 chars]'. Attorney review recommended — pre-existing condition references may require proactive addressing in the demand narrative."

*Priority level:* PRIORITY

---

**FLAG T2-05 — Functional Impact Documentation Present** *(positive flag — not a problem signal)*

*What it detects:* This flag works differently from all others. It is not a warning — it is a positive identification of entries that directly support the damages calculation. Paralegals actively pull these entries into the chronology as a distinct category. TRACE tags them so the attorney can filter for damages-relevant entries without reading every clinical note.

*Detection logic:*
- OpenMed NER identifies the following entity types in clinical descriptions:
  - Work restriction language: "light duty," "restricted to," "no lifting," "limited hours," "modified duty," "unable to work," "off work," "work restrictions"
  - Return-to-work language: "return to work," "cleared to return," "phased return," "full duty clearance"
  - ADL limitation language: "unable to perform," "difficulty with," "limited ability to," "assistance required for," "cannot," "pain with"
  - Range of motion measurements: numeric values paired with anatomical direction terms ("flexion," "extension," "rotation," "abduction")
  - Pain scale scores: numeric values (0–10) paired with pain language
  - Future care language: "permanent," "ongoing," "lifetime," "chronic," "will require," "future surgery," "long-term"
- Tag every matching entry in the chronology with label: FUNCTIONAL_IMPACT

*Attorney-facing output:* Tagged in the chronology with a distinct visual indicator. Filter option in the QA interface: "Show Functional Impact entries only." No flag annotation required — these are positive tags, not issues requiring resolution.

*Priority level:* Not a blocking flag — informational tag only. Does not count toward Priority flag total in the demand-ready gate.

---

**FLAG T2-06 — Referral Recommendation With Imaging Already in Record Set**

*What it detects:* The complement of FLAG T1-03. Where T1-03 flags a referral with no follow-up found, T2-06 identifies cases where imaging was ordered and the imaging report is present — and surfaces the imaging result entry explicitly alongside the ordering note. This is positive case assembly work: linking the recommendation to the result in the chronology view.

*Detection logic:*
- For each FLAG T1-03 match where an imaging order was detected: run a second pass to find whether an imaging report document does exist in the set from that modality within 90 days
- If found: create a cross-reference link between the ordering entry and the imaging report entry in the chronology
- Surface both entries as linked in the QA interface — clicking either shows both in the right panel

*OpenMed role:* Modality entity extraction ("MRI of the lumbar spine," "CT of the cervical spine") to match imaging orders against imaging reports.

*Attorney-facing output:* Not a flag — a positive cross-reference link in the chronology. Both entries tagged as LINKED_RECORDS. Visible in the chronology with a link indicator between them.

*Priority level:* Not a blocking flag — informational link only.

---

**TIER 3 — Attorney Judgment Required (TRACE surfaces, never characterizes)**

These items cannot be reliably detected or classified by any algorithmic or NLP approach without producing an unacceptable false positive rate or crossing into legal interpretation. TRACE's contribution is ensuring the raw data is visible and organized so the attorney can make these judgments efficiently.

| Item | What TRACE does | What attorney does |
|------|----------------|-------------------|
| Pre-existing condition vs. incident causation | Surfaces T2-04 flags with source citations | Decides whether the prior condition was aggravated, concurrent, or unrelated |
| Whether a treatment gap is clinically explained | Surfaces T1-01 and mid-treatment gaps with source context | Decides whether to proactively address in demand or let stand |
| Whether conflicting descriptions are material | Surfaces T2-02 with verbatim excerpts side by side | Decides whether discrepancy is a documentation artifact or a credibility issue |
| Whether non-compliant notations are defensible | Surfaces T1-04 with full context | Decides whether to obtain client explanation before demand |
| Whether degenerative findings were aggravated | Surfaces T2-04 with imaging report language | Decides with expert input whether aggravation argument is supportable |
| Whether future care is documented sufficiently | Surfaces FUNCTIONAL_IMPACT entries tagged T2-05 | Decides whether future care language is specific enough to support demand |

---

**5.5.4 Flag Priority Levels and Demand-Ready Gate**

*(Renumbered from 5.5.3 — flag management, July 2026)*

Flags are assigned one of three priority levels. Only PRIORITY flags block the demand-ready gate.

| Priority Level | Definition | Examples | Blocks demand-ready? |
|---------------|-----------|---------|---------------------|
| PRIORITY | Material to case value or defense strategy. Attorney must annotate before export. | Treatment gaps, billing discrepancies, delayed initial treatment, non-compliant language, clinician credibility language, pre-existing condition signals, incident description conflicts, bill with no procedure report | Yes |
| ADVISORY | Potentially relevant but not demand-blocking. Surfaced for attorney awareness. | Delayed initial treatment 4–7 days, new provider without referral, changing symptoms without progression | No — attorney may annotate but not required |
| INFORMATIONAL | Positive tags. No annotation required. | Functional impact entries (T2-05), imaging cross-reference links (T2-06) | No |

All flags — regardless of priority — are visible in the QA interface. All flags — regardless of priority — are included in the audit trail. The demand-ready gate counts only unannotated PRIORITY flags.

**Updated color coding for QA interface left panel:**

| Flag type | Color |
|-----------|-------|
| Treatment gap (existing) | Amber |
| Billing discrepancy (existing) | Red |
| Delayed initial treatment (T1-01) | Amber |
| Sudden treatment stop (T1-02) | Amber |
| Follow-up with no record (T1-03) | Orange |
| Non-compliant language (T1-04) | Red |
| Bill with no procedure report (T1-05) | Red |
| Clinician credibility language (T1-06) | Red |
| New provider without referral (T2-01) | Yellow (advisory) |
| Changing incident description (T2-02) | Red |
| Changing symptom complaints (T2-03) | Yellow (advisory) |
| Pre-existing condition signal (T2-04) | Red |
| Functional impact tag (T2-05) | Green (positive) |
| Imaging cross-reference link (T2-06) | Blue (informational) |

**5.5.5 Flag Management**

*(Renumbered from 5.5.3, July 2026)*
- All flags displayed in attorney QA interface with: flag type, priority level, description, source references, annotation field
- Attorney annotation options: Confirmed and Explained (free text) / Confirmed and Needs Follow-up / Dismissed (not relevant) / Resolved
- Flags cannot be deleted — only annotated. The audit trail shows every flag and its resolution
- Chronology cannot be marked demand-ready until all PRIORITY flags have attorney annotations
- ADVISORY and INFORMATIONAL flags do not block demand-ready status but remain visible and annotatable

### 5.6 Attorney QA Interface

**5.6.1 Chronology review**
- Full chronology displayed in portal with source citation links
- Clicking any entry opens the source document at the cited page
- Filter options: by provider, by date range, by event type, by flag status
- Attorney can add free-text annotations to any chronology entry
- Attorney can mark any entry as "Verify before use" without blocking demand-ready status

**5.6.1a Split-Panel QA Interface Layout**
*(Extracted and adapted from MalpracticeVibe SRD main.py Streamlit implementation, July 2026 — interface pattern adopted, local deployment stack replaced with cloud portal implementation)*
- The chronology review interface uses a persistent split-panel layout for attorney QA

  **Left panel — Chronology:**
  Scrollable list of all clinical events in date order. Each entry displays: date, provider, facility, event type, clinical description (verbatim from source), and flag status indicator. Flag color coding follows Section 5.5.4: red for Priority flags (billing discrepancies, non-compliant language, credibility language, incident description conflicts, pre-existing condition signals, procedure bills with no report), amber for treatment gaps and treatment stop flags, orange for follow-up with no record, yellow for advisory flags (new provider, changing symptoms), green for functional impact tags, blue for imaging cross-reference links, grey for resolved flags. Filter controls above the list allow filtering by provider, date range, event type, flag status, and flag priority level.

  **Right panel — Source Document:**
  Displays the source document at the exact page cited for the currently selected chronology entry. Selecting any entry on the left automatically loads the corresponding page on the right. Right panel supports zoom, scroll, page navigation, and download of individual source documents.

  **Interaction model:**
  Attorney reads chronology entry on the left, verifies against source document on the right, annotates the flag field inline in the left panel, and advances to the next entry without losing position. No page navigation required between chronology and source — both are visible simultaneously.

  **Flag annotation inline:**
  Each flagged chronology entry displays the annotation field directly in the left panel beneath the entry. Attorney selects from: Confirmed and Explained (with free-text field) / Confirmed and Needs Follow-up / Dismissed / Resolved. Annotation saves on selection — no separate save action required. Annotation is logged with attorney ID and timestamp.

  **Demand-ready status bar:**
  A persistent status bar at the top of the interface shows: total chronology entries, total flags, annotated flags, and remaining unannotated Priority flags. The "Mark Demand-Ready" action button is locked (greyed, non-clickable) until all Priority flags (treatment gaps and billing discrepancies above threshold) have attorney annotations. When remaining Priority flags reach zero the button becomes active. The attorney's approval action is logged as a distinct event separate from individual flag annotations.

**5.6.2 Approval workflow**
- Attorney approval action: "I have reviewed this chronology and all flagged items. I confirm this chronology is ready for use in case preparation."
- Approval logs: attorney name, date, time, TrueVow case reference
- Post-approval: chronology status changes to "Demand-Ready — Attorney Approved [date]"
- Post-approval editing: any edit after approval resets status to "Pending Re-approval" and requires the attorney to re-approve

**5.6.3 Export**
- PDF export: formatted chronology with disclaimer on every page, source citations, flag annotations, attorney approval status
- JSON export: structured data for case management system import (Clio, MyCase, Filevine where supported)
- Master record index: separate document listing all received records with provider, date range, page count, and storage location

### 5.7 Case Readiness Board
*(Added July 2026 — ADR-001 §23 product simplification recommendation)*

The attorney-facing UX for TRACE is not an AI dashboard with raw flags. It is a **Case Readiness Board** — a single-screen view showing how ready each case is for demand preparation, organized into five columns with four status options each.

**Core insight:** The market already has AI medical chronology platforms. TRACE's wedge is the INTAKE pipeline. The product must simplify around one promise: *TRACE helps PI firms know what providers, records, bills, liens, treatment gaps, and chronology items still need review before demand preparation.*

**Readiness Board columns and status options:**

| Column | Status options | Backing data entity |
|--------|---------------|---------------------|
| **Providers** | Missing / Requested / Received / Reviewed | providers table, retrieval_status |
| **Records** | Missing / Requested / Received / Reviewed | documents table, OCR status |
| **Bills** | Missing / Requested / Received / Reviewed | medical_bill_line table (TRACE-owned) |
| **Liens** | Not Checked / Requested / Received / Reviewed | liens table (see below) |
| **Review Flags** | Unreviewed / Confirmed / Dismissed / Needs Follow-up | event_nodes table, attorney_annotation |

**What the Readiness Board does NOT change:**
The Extended Flag Registry (§5.5.3) runs in full. All flag types are detected. The Readiness Board is the UX layer that makes flags actionable — not a reduction in detection scope. The split-panel QA interface (§5.6.1a) remains the detailed review view. The Readiness Board is the summary view.

**Liens data requirement:**
The Liens column requires a `liens` table. Lien management is a non-trivial PI workflow concern — Medicare/Medicaid liens, ERISA liens, workers' compensation liens, and health insurance subrogation claims must all be tracked before settlement. Minimum viable schema:

| Field | Description |
|-------|-------------|
| Lien ID | Unique identifier |
| Case ID | Foreign key to cases table |
| Lien type | Medicare / Medicaid / ERISA / Workers Comp / Health Insurance / Other |
| Lienholder | Lienholder name |
| Claimed amount | Dollar amount if known |
| Status | Not Checked / Requested / Received / Reviewed |
| Notes | Attorney free-text notes |
| Created at | Timestamp |
| Updated at | Timestamp |

Lien detection (identifying that a lien may exist) is Tier 3 — attorney judgment only. TRACE does not automatically detect liens. The attorney marks lien status manually. The Readiness Board surfaces it as a status column to ensure it is not overlooked before demand preparation.

**Phase 1 scope:**
Readiness Board is built in Phase 1E alongside the QA interface. The Liens column is visible in Phase 1 with manual status update only. Automated lien detection is Phase 2+ scope.

---

## 6. Non-Functional Requirements

### 6.1 Performance
- Provider identification checklist delivered within 24 hours of retainer conversion
- Record requests transmitted within 4 business hours of attorney approval
- Document processing: standard records set (under 500 pages) processed within 24 hours of receipt; complex records sets (500–2,000 pages) within 48 hours
- Chronology delivery: within 48 hours of all provider records marked complete or attorney marks retrieval as sufficient
- Portal response time: under 3 seconds for all attorney-facing interactions

### 6.2 Accuracy
- OCR accuracy target: 95%+ on digital PDFs; 85%+ on clean scans; below-threshold pages flagged for manual attorney review
- Clinical event extraction: all extracted events must have a source citation. No event may appear in the chronology without a traceable source document
- Gap detection: no gap of 14+ days may be missed where records exist on both sides of the gap
- Billing reconciliation: false positive rate target below 15% (i.e., no more than 15% of flagged discrepancies should be format differences rather than actual discrepancies)
- **Extended Flag Registry — Tier 1 flag accuracy targets:**
  - T1-01 Delayed initial treatment: 100% detection where incident_date and first_clinical_entry_date are both present — pure date math, no NLP error source
  - T1-02 Sudden treatment stop: false negative target below 10% — must not miss a case where no discharge or MMI notation exists on the last entry
  - T1-03 Follow-up with no record: false positive target below 20% — acceptable trade-off given the consequence of a missed referral gap is higher than the cost of an unnecessary attorney review
  - T1-04 Non-compliant language: 100% detection for exact string matches in the prohibited terms list — must not miss any instance; false positives acceptable
  - T1-05 Bill with no procedure report: false negative target below 5% — the cost of a missed operative report is too high
  - T1-06 Clinician credibility language: 100% detection for exact string matches — must not miss any instance
- **Extended Flag Registry — Tier 2 flag accuracy targets:**
  - T2-01 New provider without referral: false positive target below 30% — advisory flag, attorney annotation not required. Acceptable rate given low cost of review
  - T2-02 Changing incident description: false positive target below 15% — priority flag, must be high confidence before surfacing
  - T2-03 Changing symptom complaints: false positive target below 25% — advisory flag, anatomy NER progression logic has inherent ambiguity
  - T2-04 Pre-existing condition signal: false negative target below 5% — must not miss pre-existing references; false positives acceptable given the stakes
  - T2-05 Functional impact tags: recall target 85%+ — must capture the majority of functional impact entries; missed tags reduce damages documentation visibility but do not create false flags
  - T2-06 Imaging cross-reference links: precision target 90%+ — cross-reference links must be accurate; false links between unrelated entries would mislead attorney review

### 6.3 Reliability
- System uptime: 99.9% for attorney-facing portal
- Fax transmission success rate: 95%+ on first attempt; failed transmissions automatically retried within 4 hours
- Data backup: all case records backed up in real time to geographically redundant storage
- Disaster recovery: RTO under 4 hours, RPO under 1 hour

---

## 7. Compliance and Legal Requirements

### 7.1 HIPAA Compliance Architecture

**Administrative safeguards:**
- Designated Privacy Officer and Security Officer (may be one person at early access stage)
- HIPAA Security Risk Assessment completed before first case is processed
- Annual risk assessment thereafter and after any material system change
- Documented workforce training program — all staff with PHI access complete annual HIPAA training
- Written HIPAA policies and procedures covering: minimum necessary access, breach notification, business associate management, workforce sanctions

**Technical safeguards:**
- Encryption in transit: TLS 1.2+ for all data transmission
- Encryption at rest: AES-256 for all stored PHI
- Access controls: unique user IDs, automatic logoff, role-based access (attorney sees only their firm's cases)
- Multi-factor authentication for all portal access
- Audit logging: every access to PHI logged with user ID, timestamp, action, and data accessed
- Audit logs retained for 6 years minimum per HIPAA requirement

**Physical safeguards:**
- All infrastructure hosted in SOC 2 Type II certified data centers
- No PHI processed on employee-owned or unmanaged devices
- Screen lock policies for all workstations with PHI access

**Breach notification:**
- Documented incident response plan
- Attorney (as covered entity) notified within 24 hours of confirmed or suspected breach
- HHS OCR notification process documented and tested annually
- Affected individuals notified per HIPAA breach notification rule timeline

### 7.2 Business Associate Agreement Requirements

Every firm using TRACE must have a signed BAA with TrueVow before any case is processed. The BAA must address:
- Permitted uses and disclosures of PHI
- Minimum necessary standard
- Required safeguards (technical, administrative, physical)
- Breach notification obligations (24 hours to covered entity)
- Subcontractor obligations (cloud fax provider, document processing infrastructure, storage)
- Data return or destruction at termination
- Right-to-audit language
- Data retention requirements (6 years for HIPAA-related documentation)
- Liability and indemnification terms

The BAA is presented and signed during TRACE onboarding, before any case data is entered. Separate from the TrueVow INTAKE service agreement.

### 7.3 HIPAA Fax Infrastructure Requirements

The cloud fax provider used for record requests must:
- Sign a BAA with TrueVow before any PHI is transmitted
- Provide TLS 1.2+ encryption in transit
- Provide AES-256 encryption at rest
- Maintain SOC 2 Type II certification
- Provide complete audit trails for all transmissions
- Support API integration for automated request generation and delivery confirmation
- Support HIPAA mode (no PHI in email notification content — notification text only)

Evaluated vendors meeting these requirements: Fax.Plus (Enterprise with BAA), iFax (Enterprise), Documo (BAA-backed), Notifyre (BAA available). Vendor selection to be finalized during infrastructure build phase with security review of current BAA terms and SOC 2 reports.

### 7.4 Attorney Responsibility Documentation

The following must be in writing and signed by the attorney before TRACE early access is activated:

1. TrueVow retrieves and processes records on behalf of the attorney's firm. The attorney is responsible for reviewing the chronology before it is used for any legal purpose.

2. TRACE flags treatment gaps, billing discrepancies, and a range of additional observations derived from the records — including delayed initial treatment, sudden treatment stop, follow-up recommendations with no corresponding record, non-compliant language, clinician credibility language, pre-existing condition signals, changing incident descriptions, changing symptom complaints, and billing codes billed without corresponding procedure reports. These flags are defined in the TRACE Extended Flag Registry (PRD Section 5.5.3). All flags are data observations only. They do not constitute legal analysis, clinical interpretation, or a representation of case facts. The attorney interprets and acts on all flags.

3. The attorney is responsible for ensuring that all relevant providers have been identified and that all material records have been received before relying on the chronology in any demand, negotiation, or legal proceeding.

4. TRACE chronology output does not constitute legal advice, medical advice, a medical opinion, or a representation of case value. It is a structured organization of records provided by the attorney's client's healthcare providers.

5. The attorney maintains all professional responsibility obligations for the completeness and accuracy of any demand, pleading, or negotiation position that relies on TRACE output.

This document is presented as an addendum to the MSA and must be signed before case activation.

### 7.5 UPL Boundaries

TRACE output must never:
- Characterize the strength of a legal claim
- Predict case outcome or settlement value (that is SETTLE)
- Recommend legal strategy
- Suggest that any treatment is or is not causally related to the incident
- Describe any finding as supporting or undermining a legal position

Every chronology entry uses verbatim clinical language from the source record or neutral factual description. The system must be tested against a prohibited output registry (equivalent to the Benjamin voice script prohibited phrase registry) before any case is processed.

### 7.6 ABA Compliance

Under ABA Formal Opinion 512:
- Attorney must independently verify all material facts against original source documents before using chronology output in any legal submission
- Attorney bears full responsibility for any document that relies on TRACE output, regardless of AI involvement in preparation
- Client disclosure: engagement letter must disclose that a third-party AI service processes medical records on behalf of the firm. Standard disclosure language to be drafted during onboarding configuration.

---

## 8. Technical Architecture Overview

### 8.1 System Components

```
TRACE PIPELINE
─────────────────────────────────────────────────────────────────
INTAKE RECORD
(Benjamin JSON)
Attorney reviews + clicks "Send for Signature"
        ↓
STAGE 0: DOCUMENT SIGNING (DocuSeal — self-hosted, Fly.io HIPAA boundary)
  TRACE calls DocuSeal API → generates retainer + fee agreement + HIPAA auth package
  Attorney signature template applied automatically
  Client receives SMS + email with signing link
  Client signs on phone (no app, no account, 3 minutes)
  DocuSeal webhook fires → HIPAA auth status = SIGNED
  Signed PDF → Supabase Storage (signed-documents bucket, encrypted)
  DocuSeal audit trail → signed_documents table
        ↓
STAGE 1: CASE INITIALIZATION (FastAPI)
  Provider extraction begins
  SOL calculated from incident date + jurisdiction
  Supabase PostgreSQL: case record created, stage = INITIALIZATION
        ↓
INTAKE RECORD        OpenMed NER            PROVIDER
(Benjamin JSON)  →  + NPI LOOKUP        →  CHECKLIST
+ OpenMed deid()                           (Attorney Confirms)
                                                 ↓
                                         REQUEST GENERATION
                                         (PDF + HIPAA Auth from signed-documents)
                                                 ↓
                                    HIPAA CLOUD FAX TRANSMISSION
                                    (Encrypted, BAA-covered, vendor TBD per decision protocol)
                                                 ↓
                                    SECURE INBOUND RECEIVE
                                    (Fax inbox / Upload portal)
                                                 ↓
                                    deepdoctection + DocTr (OCR)
                                    ↓ raw text
                                    OpenMed Nemotron deid_text()
                                    ↓ redacted text + phi_map
                                    phi_map → encrypted PHI Store
                                    ↓ redacted text only
                                    OpenMed clinical NER
                                    + Document Classification + Indexing
                                                 ↓
                                    CHRONOLOGY ENGINE
                                    Clinical event extraction → Date sort → Cite
                                    (redacted text — PHI re-introduced at portal display only)
                                                 ↓
                                    EXTENDED FLAG REGISTRY (§5.5.3)
                                    Tier 1 (algorithmic) + Tier 2 (OpenMed NLP)
                                    + Billing reconciliation (billing repo integration)
                                                 ↓
                                    ATTORNEY QA PORTAL
                                    Split-panel: Chronology ← → Source Document
                                    Flag review → Annotation → Approval
                                    (PHI re-introduced at display from encrypted PHI Store)
                                                 ↓
                                    DEMAND-READY OUTPUT
                                    PDF (disclaimer every page) + JSON export
                                    ↓ triggers
                                    SETTLE pipeline (chronology JSON, attorney-approved)
─────────────────────────────────────────────────────────────────

PHI STORE (separate encrypted Supabase instance — column-level pgcrypto AES-256)
  ← phi_map (OpenMed de-identification offset map, encrypted)
  ← client PII (name, DOB, address — tokenized in all other systems)
  → portal display only (authenticated attorney session, firm-scoped)
  → audit_log (access logged, PHI values never appear in logs)

SIGNED DOCUMENTS (Supabase Storage — signed-documents private bucket)
  ← DocuSeal signed PDF packages (retainer + HIPAA auth + fee agreement)
  ← DocuSeal audit trail JSON
  → HIPAA authorization attachment for fax record requests
  → Attorney download on demand (authenticated portal session only)
  → Data destruction at firm termination (separate from medical records destruction)
```

### 8.2 Data Flow and PHI Handling

- PHI enters TRACE only through: signed client HIPAA authorization + attorney-approved provider list
- PHI stored only in HIPAA-compliant, SOC 2 Type II certified infrastructure
- PHI never transmitted to any party other than: the originating healthcare provider (for requests), the attorney's firm (for records and chronology)
- PHI never included in any URL, notification subject line, or log entry accessible outside the secure portal
- All PHI access logged with user ID, timestamp, and action — PHI values never appear in logs, only entity types
- Case data segmented by firm — no attorney can access another firm's case data under any circumstance
- **phi_map retention:** The OpenMed de-identification phi_map (offset map linking redacted tokens to original PHI values) is PHI. It is stored encrypted in the PHI store alongside the case record. Retention period matches the case data retention period — minimum 6 years from case closure per HIPAA and state bar requirements. The phi_map is destroyed alongside all other case PHI when the case record is destroyed at firm termination or upon attorney request, following the documented data destruction process. The phi_map is never exported, never included in chronology exports, and never transmitted to SETTLE
- Data retention per firm: configurable per HIPAA and state bar record retention requirements (minimum 6 years)
- Data destruction at firm termination: documented process, confirmation delivered to attorney. Covers: case records, chronology exports, source documents in Supabase Storage, PHI store entries, phi_maps, and audit log entries referencing the firm

### 8.3 Integration Points

**DocuSeal → TRACE (document signing):**
- Deployment: DocuSeal self-hosted on Fly.io, within the same HIPAA boundary as TRACE. No separate BAA required — covered by Fly.io BAA
- Trigger: attorney clicks "Send for Signature" in TRACE portal
- TRACE calls DocuSeal API to generate signing package from firm templates and send to client
- DocuSeal sends signing link to client via SMS + email (client contact info from PHI store — passed securely, not logged)
- Webhook callback from DocuSeal to TRACE when all signatures are complete
- On webhook: TRACE updates `hipaa_auth_status = SIGNED`, advances `case_stage` to INITIALIZATION, triggers provider extraction job
- Signed PDF stored in Supabase Storage `signed-documents` private bucket, linked to case_id
- DocuSeal audit trail (signer identity, IP address, timestamp, signing method) embedded in signed PDF and also stored as a JSON record in the case manifest
- Signing status changes are logged to audit_log with actor_type = 'SYSTEM' and actor_type = 'CLIENT' as appropriate
- License: DocuSeal AGPL-3.0. TRACE uses DocuSeal unmodified via its REST API — no source modifications. This preserves TrueVow code as proprietary while using DocuSeal legally

**INTAKE → TRACE:**
- Trigger: attorney marks a lead as "Retainer Signed" in TrueVow portal
- Data passed: Benjamin intake record JSON (provider references, injury type, incident date, jurisdiction, client identifier)
- Client PII not passed until attorney has signed TRACE BAA and attorney responsibility addendum

**TRACE → SETTLE:**
- Trigger: attorney marks chronology as "Demand-Ready — Attorney Approved"
- Data passed: structured chronology JSON (clinical events, treatment timeline, gap summary, billing summary)
- SETTLE uses chronology as input for settlement-range context generation
- No PHI passed to SETTLE without attorney approval of the TRACE chronology

**TRACE → Case Management Systems (CMS):**
- Export format: structured JSON mapped to Clio, MyCase, and Filevine field schemas where supported
- Integration method: attorney-initiated export (no automatic sync without attorney action)
- API webhook support available at OPERATIONS tier
- All CMS integrations subject to attorney configuration and approval

### 8.4 Case Data Schema
*(Extracted and adapted from MalpracticeVibe SRD Google OKF storage specification, July 2026 — flat file local storage model replaced with cloud database schema; field structure and cross-reference concept adopted)*

Every TRACE case is structured around three entity types stored in TrueVow's HIPAA-compliant cloud database with firm-level segmentation. No case data is stored locally on attorney devices.

**Entity 1 — Case Manifest**

Master record for each active TRACE case. Contains:

| Field | Description |
|-------|-------------|
| Case ID | Opaque TrueVow-assigned identifier — no client PII in ID |
| Client token | Tokenized client reference linked to PII stored separately in encrypted store |
| Incident date | From Benjamin intake record |
| Jurisdiction | State of practice from intake record |
| SOL deadline | Calculated from incident date + jurisdiction SOL table |
| SOL urgency label | Standard / Monitor / Urgent / Critical |
| HIPAA authorization status | PENDING / SENT / SIGNED / EXPIRED |
| DocuSeal submission ID | Opaque reference to the DocuSeal signing session — used for status polling and webhook correlation. Never contains client PII |
| Signing completed at | Timestamp when all required signatures were collected |
| Provider list status | Draft / Attorney Confirmed / Locked |
| Retrieval status | Per-provider: Pending / Requested / Partial / Complete / Unresponsive |
| Case stage | Pending Signature / Initialization / Retrieval / Processing / Chronology Ready / Attorney Review / Demand-Ready |
| Approval record | Attorney ID, timestamp, and confirmation text at Demand-Ready approval |

**Entity 0 — Signed Documents** (new entity added with DocuSeal integration)

One record per signed document package per case. Contains:

| Field | Description |
|-------|-------------|
| Signing ID | Unique identifier |
| Case ID | Foreign key to cases table |
| DocuSeal submission ID | Reference to DocuSeal signing session |
| Document type | RETAINER_PACKAGE / HIPAA_AUTHORIZATION / SUPPLEMENTAL |
| Signing status | PENDING / SENT / PARTIALLY_SIGNED / SIGNED / EXPIRED / DECLINED |
| Client signed at | Timestamp of client signature |
| Attorney template applied at | Timestamp when attorney signature template was applied |
| Signed PDF storage key | Supabase Storage key for the completed signed PDF (signed-documents bucket) |
| DocuSeal audit trail | JSONB — embedded audit trail from DocuSeal: signer identity, IP address, signing timestamp, method |
| Reminder sent at | Timestamp of automated 24-hour reminder |
| Expires at | Signing link expiry — configurable, default 7 days |
| Created at | Timestamp |

**Entity 2 — Chronology**

Ordered list of all clinical events across all providers. Each entry contains:

| Field | Description |
|-------|-------------|
| Event ID | Sequential identifier within the case |
| Timestamp | Date and time of clinical event (normalized from source) |
| Provider | Treating provider name (de-identified token — real name from PHI store at display) |
| Facility | Facility name (de-identified token) |
| Event type | Visit / Imaging / Prescription / Procedure / Discharge / Referral |
| Clinical description | Verbatim text from source record — not interpreted. De-identified — PHI tokens shown at display |
| Source document ID | Reference to the processed document in the document store |
| Source page number | Exact page within the source document |
| Flag reference | Link to Event Node if this entry has a flag — null if clean |
| Review status | UNREVIEWED / CONFIRMED / EDITED / DISMISSED / NEEDS_MORE_RECORDS — default UNREVIEWED. Export clearly marks unreviewed entries |
| Attorney annotation | Free-text annotation field — null until attorney adds one |
| Verify flag | Boolean — attorney can mark any entry for secondary review |

**Document entity** (stored in Supabase Storage with metadata in documents table):

| Field | Description |
|-------|-------------|
| Document ID | Unique identifier |
| Case ID | Foreign key to cases table |
| Provider ID | Foreign key to providers table — null for client-uploaded documents not yet linked to a provider |
| Storage key | Supabase Storage object key (case_id/document_id — no PII) |
| Source | PROVIDER_FAX / ATTORNEY_UPLOAD / CLIENT_UPLOAD / SCAN / DOCUSEAL_SIGNED / UNKNOWN — tracks provenance for deduplication and audit trail |
| SHA256 hash | Computed after storage. Used for exact duplicate detection within the case. Never null after processing |
| Document type | ER / IMAGING / PT / BILLING / PHARMACY / SPECIALIST / OTHER |
| Page count | Total pages |
| Received at | Timestamp of receipt |
| OCR status | PENDING / PROCESSING / COMPLETE / FAILED |
| OCR confidence | Mean confidence score across all pages |
| Quality flags | Array of zero or more transparency indicators: LOW_OCR_CONFIDENCE / HANDWRITTEN_NOTE_DETECTED / POSSIBLE_DUPLICATE / PAGE_ORDER_UNCERTAIN / LANGUAGE_NOT_ENGLISH / MISSING_PAGE_NUMBER / POOR_SCAN_QUALITY / NEEDS_MANUAL_REVIEW. These are not error states — they indicate where TRACE is uncertain and direct attorney manual review to pages that need it |
| Is duplicate | Boolean — set by dedup job when SHA256 hash matches existing document in the same case. Never auto-removed — requires attorney confirmation |
| Is misfiled | Boolean — flagged if document appears to relate to a different patient or date range |

**Entity 3 — Event Nodes**

Atomic records for each flagged item. Each Event Node contains:

| Field | Description |
|-------|-------------|
| Node ID | Unique identifier |
| Flag type | See Extended Flag Registry §5.5.3 — 14 flag types across PRIORITY/ADVISORY/INFORMATIONAL |
| Flag priority | PRIORITY / ADVISORY / INFORMATIONAL |
| Date range or date | For gaps: start and end date. For discrepancies: specific date |
| Gap duration | Days between last treatment before gap and first treatment after (treatment gaps only) |
| Source document references | Document IDs and page numbers on both sides of the flag |
| System-generated description | Factual description of the discrepancy — no clinical or legal interpretation |
| CPT code extracted | For billing discrepancies: extracted CPT code and documentation requirement |
| Clinical note summary | For billing discrepancies: what the corresponding clinical note contains |
| Attorney annotation | Required on PRIORITY flags: Confirmed and Explained / Confirmed and Needs Follow-up / Dismissed / Resolved |
| Annotation text | Free-text explanation (required when status is Confirmed and Explained) |
| Annotation timestamp | Auto-populated when attorney saves annotation |
| Annotation attorney ID | Auto-populated from authenticated session |
| Resolution timestamp | Auto-populated when status is set to Resolved or Dismissed |
| Provenance | JSONB — traceability metadata for every flag: rule_name, rule_version, detection_method, matched_string (Tier 1), model_name + model_version + confidence (Tier 2). Displayed to attorney on hover in QA interface. Required for legal defensibility if attorney is deposed about a flag. Never null — every flag must carry provenance at creation time |

**Cross-references:**
Chronology entries link to Event Nodes by Node ID. Clicking a flagged chronology entry in the QA interface opens the corresponding Event Node with full source citations. Event Nodes link back to chronology entries. All cross-references are maintained as structured database foreign keys — not as markdown file links or relative paths.

**Schema integrity rules:**
- No chronology entry may exist without a valid source document ID and page number
- No Event Node may exist without at least two source document references (one on each side of the discrepancy or gap)
- No annotation field may be set to null on a Priority flag when the case is submitted for Demand-Ready approval
- All schema writes are logged with actor ID, timestamp, and operation type in the audit log

---

## 9. Early Access Program

### 9.1 Eligibility

- Active PIPELINE or OPERATIONS subscriber with at least 60 days of INTAKE usage
- At least 3 retainer-converted cases in the INTAKE portal (demonstrates the pipeline is producing signed cases)
- Signed BAA addendum covering TRACE processing
- Signed attorney responsibility addendum
- Completed TRACE onboarding:
  - DocuSeal configured: retainer template uploaded, contingency fee template uploaded, HIPAA authorization template uploaded, attorney signature pre-configured
  - Client SMS/email notification text reviewed and approved by attorney
  - Retainer package reviewed by the attorney's state bar counsel (state-specific requirements confirmed)
  - Provider confirmation workflow reviewed
  - Test signing session completed successfully (attorney sends a test package to themselves, signs, confirms DocuSeal webhook fires and TRACE case advances)

### 9.2 Early Access Pricing

| Component | Amount | Trigger |
|-----------|--------|---------|
| Platform fee | $299/month | Monthly, regardless of case volume |
| Per-settled-case fee | $199/case | At settlement — not at retainer signing |

The per-settled-case fee aligns TRACE revenue with attorney revenue. The attorney never pays the full fee until the case generates proceeds. The $299/month maintains TrueVow's infrastructure commitment to the case pipeline.

Early access pricing is locked for the duration of early access participation. Public pricing at general availability will be set based on early access economics and may differ.

### 9.3 Early Access Cohort Size

Maximum 20 firms in early access Phase 1. This limit is operational — it ensures TrueVow can provide genuine human support for edge cases during the stress-test period without overwhelming the QA and support capacity.

Phase 2 expansion to 50 firms after:
- Phase 1 cohort has processed at least 100 cases to chronology delivery
- All four human checkpoint steps have been documented with real timing data
- Attorney QA average time per case confirmed at target (under 45 minutes)
- False positive rate on billing reconciliation flags confirmed below 15%

### 9.4 Early Access Support

Each early access firm is assigned a TrueVow TRACE support contact. That contact:
- Reviews the provider confirmation checklist with the attorney on the first 3 cases
- Is available for escalation on any provider non-response beyond day 30
- Reviews OCR quality flags on the first 5 cases to calibrate attorney expectations
- Collects structured feedback after every 10 cases processed

This level of support is not scalable at general availability pricing. It is the investment required to build a product that works correctly before it is broadly deployed.

### 9.5 Early Access Graduation Criteria

A firm graduates from early access to standard PIPELINE/OPERATIONS pricing when:
- 10 cases have been processed end-to-end through TRACE
- The attorney has confirmed the chronology QA workflow is understood and sustainable
- No material compliance incidents have occurred
- The firm has provided at least one structured case study that TrueVow may use (anonymized) in product documentation

---

## 10. Metrics and Success Criteria

### 10.1 Phase 1 Success Metrics (first 100 cases)

| Metric | Target |
|--------|--------|
| Provider identification completeness | 80%+ of relevant providers captured from intake record + confirmation |
| Record request transmission success rate | 95%+ first-attempt delivery |
| Average provider response time | Under 20 days for 80% of providers |
| OCR accuracy on digital PDFs | 95%+ |
| Attorney QA time per case | Under 45 minutes |
| False positive rate on billing reconciliation flags | Under 15% |
| Treatment gap detection accuracy | 100% of gaps ≥14 days flagged where records exist on both sides |
| Attorney satisfaction (post-case survey) | 4.0+ out of 5.0 |

### 10.2 Economic Validation Metrics

| Metric | Target |
|--------|--------|
| Time saved per case vs. manual baseline (18 hrs) | 14+ hours saved |
| Attorney-reported value of time saved (at $288/hr) | $4,000+ per case |
| Per-settled-case fee as % of attorney's recovered time value | Under 5% |
| Value-to-price ratio at $199/case fee | 20:1+ |

### 10.3 Pipeline Metrics (INTAKE → TRACE → SETTLE conversion)

| Metric | Target |
|--------|--------|
| % of INTAKE retainer conversions that activate TRACE | 70%+ within 6 months of early access launch |
| % of TRACE cases that subsequently run a SETTLE report | 40%+ |
| Increase in PIPELINE/OPERATIONS subscriber LTV with TRACE active | 35%+ |

---

## 11. Development Phases and Milestones

### Phase 0 — Legal and Compliance Infrastructure (Months 1–2)
- [ ] Healthcare attorney engaged to draft TRACE BAA template
- [ ] Attorney responsibility addendum drafted and reviewed
- [ ] HIPAA authorization template for retainer package drafted and reviewed
- [ ] Cloud fax vendor selected, SOC 2 report reviewed, BAA executed
- [ ] Privacy Officer and Security Officer designated
- [ ] HIPAA Security Risk Assessment completed
- [ ] SOC 2 Type II audit initiated (Type I as interim milestone)
- [ ] Workforce HIPAA training program documented and completed by all relevant staff

### Phase 1 — Core Infrastructure Build (Months 2–4)
- [ ] NPI Registry API integration built and tested
- [ ] Provider extraction NLP built on Benjamin intake record JSON schema
- [ ] Provider confirmation checklist UI built in attorney portal
- [ ] HIPAA authorization template integration into retainer workflow
- [ ] Cloud fax transmission pipeline built (request generation + transmission + confirmation logging)
- [ ] Secure inbound fax receive infrastructure built and tested
- [ ] Document upload portal for attorney-initiated record submission built
- [ ] OCR processing pipeline built and accuracy-tested against 50 sample records sets
- [ ] Document classification model trained and tested
- [ ] Case data storage built with PHI segmentation by firm

### Phase 2 — Chronology and Detection Build (Months 4–6)
- [ ] Chronology extraction NLP built and tested against 30 sample records sets
- [ ] Source citation linking built (every entry traceable to document + page)
- [ ] Gap detection algorithm built and tested against records sets with known gaps
- [ ] Billing reconciliation algorithm built and tested against mixed billing/clinical records
- [ ] Flag management system built in attorney QA interface
- [ ] Attorney annotation workflow built
- [ ] Approval action and audit logging built
- [ ] PDF export built with disclaimer on every page
- [ ] JSON export built with CMS field mapping

### Phase 3 — Early Access Launch (Months 6–8)
- [ ] First 5 early access firms onboarded and BAAs signed
- [ ] First 20 cases processed with TrueVow support contact present for QA review
- [ ] Timing data collected on all four human checkpoint steps
- [ ] OCR edge case library built from first cohort failures
- [ ] Attorney feedback structured and prioritized
- [ ] Phase 1 success metrics evaluated against targets

### Phase 4 — Iteration and Phase 2 Expansion (Months 8–12)
- [ ] Edge cases from Phase 3 addressed
- [ ] Phase 1 cohort expanded to 20 firms, 100+ cases
- [ ] SETTLE integration tested (TRACE chronology → SETTLE input)
- [ ] Phase 1 success metrics confirmed
- [ ] Economic validation metrics confirmed
- [ ] Case studies collected from early access graduates
- [ ] Public pricing page and product page prepared

### Phase 5 — General Availability (Month 13–18)
- [ ] trace.html product page live
- [ ] TRACE added to pricing page as PIPELINE + OPERATIONS add-on
- [ ] Homepage pipeline section updated: INTAKE → TRACE → SETTLE
- [ ] LEVERAGE product page retired or repositioned
- [ ] Public pricing: $299/month + $199/settled case OR adjusted based on Phase 1–4 economics

---

## 12. Open Questions Requiring Resolution Before Build

**Legal:**
1. Does the HIPAA authorization template need to be jurisdiction-specific (California, Texas, Florida each have additional state-level records access requirements beyond federal HIPAA)? → Requires healthcare attorney review by state.

2. Does the attorney responsibility addendum need to be reviewed by each state bar where early access firms practice? → Requires legal analysis of professional responsibility rules in target states.

3. What is the correct characterization of TrueVow's role under HIPAA — Business Associate of the attorney firm, or Business Associate of the covered entity (healthcare provider)? → The attorney is not a covered entity; they are an authorized representative of the patient. This affects how the BAA chain is structured. Requires healthcare attorney guidance.

**Technical:**
4. Which cloud fax vendor is selected? Two primary candidates: **Fax.Plus Enterprise** and **Documo**. Published pricing is the starting point only — actual enterprise costs include compliance riders, volume overage rates, and support tiers not reflected in published prices. The Technical Implementation Spec (Part 2.1) defines the vendor decision protocol: obtain real BAA quotes from both vendors at target volume (200–500 faxes/month early access, 2,000–5,000/month GA), apply the switch rule (switch to Documo if Fax.Plus total annual cost exceeds 2x Documo at same volume), document the comparison, and lock the vendor before Phase 1C endpoints are built. The switch has zero architecture impact — both APIs are wrapped identically through the `FaxService` abstraction. Default to Documo if the comparison is not completed before the Phase 1B/1C boundary (all-plan BAA eliminates plan-gating compliance risk).

5. ~~What OCR engine is used for handwritten clinical notes?~~ **RESOLVED — deepdoctection + DocTr selected (July 2026).** Open caveat: handwriting accuracy spike required before Phase 1D. Benchmark deepdoctection + DocTr against minimum 20 pages of de-identified handwritten clinical notes from urgent care and chiropractor records. If mean accuracy falls below 80%, evaluate Google Document AI as a fallback backend within the deepdoctection framework (single config line change, no job code changes required).

6. ~~How does TRACE handle records received in Spanish?~~ **RESOLVED — OpenMed handles Spanish natively (July 2026).** OpenMed supports 12 languages including Spanish with automatic language detection. Same `deid_text()` and `analyze_text()` calls work on Spanish-language records. No separate translation layer required.

**Product:**
7. What is the minimum viable chronology for early access — full Extended Flag Registry or subset? → Recommendation: Phase 1D launches with chronology + all Tier 1 algorithmic flags (T1-01 through T1-06) + treatment gap detection. Add Tier 2 NLP flags (T2-01 through T2-06) in Phase 2 after Tier 1 is validated against early access data. Add billing reconciliation after billing repo prerequisites (Q11) are confirmed. Confirm phasing with product owner before Phase 1D begins.

8. Should TRACE accept records from before the incident date (pre-existing condition documentation)? → Attorney-controlled opt-in per case. FLAG T2-04 (Pre-Existing Condition Signal) operates in two modes: post-incident reference detection (all cases) and full pre/post comparison (opted-in cases only). Confirm opt-in UI placement in Phase 1E build.

9. What is the correct cap on records volume per case before TRACE requires manual intervention? → 500 pages standard, 2,000+ pages flagged for attorney attention. Confirm based on early access data during Phase 3.

**Architecture — added following Technical Implementation Spec revisions, July 2026:**

10. ~~Which cloud provider do the existing TrueVow repos use?~~ **RESOLVED — Fly.io + Supabase confirmed (July 2026).** See Q13 for Supabase HIPAA configuration requirements.

11. What are the billing repo integration prerequisites before the billing reconciliation job (Spec Section 5.6) can be built? → Four items must be confirmed with the billing repo team: (a) what case identifier maps between TRACE and the billing repo; (b) what fields the billing repo's case-level API returns — minimum: date of service, provider identifier, CPT code, ICD-10 code, billed amount; (c) whether the billing repo is within TrueVow's HIPAA compliance boundary; (d) what authentication the billing repo API uses. Until all four are confirmed, billing reconciliation uses the temporary fax-document fallback marked TODO in code.

12. Is a HIPAA BAA confirmed with the selected LLM provider before billing reconciliation processes any case data? → Spec defaults to Azure OpenAI GPT-4o-mini under Microsoft Healthcare BAA. DeepSeek prohibited until BAA is published and Privacy Officer approves in writing. Privacy Officer must sign off before Phase 1D begins.

13. **Supabase HIPAA configuration — 11 items required before production go-live. Not required during development build — synthetic data only during development.** Based on Supabase shared responsibility model documentation as of July 9, 2026: (a) Team Plan minimum — HIPAA add-on not available on Pro or Free plans; (b) HIPAA add-on enabled via Supabase dashboard; (c) BAA signed with Supabase; (d) TRACE project(s) marked as HIPAA projects in project settings; (e) MFA enforced on all Supabase accounts in the TrueVow organization; (f) Point in Time Recovery enabled (requires compute add-on); (g) SSL Enforcement enabled; (h) Network Restrictions enabled; (i) Postgres connection logging explicitly enabled — Supabase sets log_connections to OFF by default for new projects from July 9, 2026; HIPAA projects must override this explicitly; (j) Supabase AI editor data sharing disabled; (k) PHI must not be processed through Supabase Edge Functions — all TRACE jobs processing PHI run on Fly.io application servers only. Full checklist in Spec Part 9.2. Engineering lead confirms all 11 items complete before first real PHI case is processed — not before Phase 1A development begins.

14. Should TEFCA Individual Access Services be evaluated as a Phase 3 retrieval pathway? → On June 26, 2026, HHS ONC confirmed TEFCA has exchanged one billion health records and is being actively strengthened. TEFCA's Individual Access Services purpose enables patients or their authorized representatives (including attorneys) to retrieve records through the TEFCA network. In 2026, hybrid TEFCA-enabled and traditional fax workflows are the operational reality — TEFCA does not replace fax for non-participating providers but materially accelerates retrieval for hospital systems with modern EHR adoption. Recommendation: evaluate a QHIN connection as a Phase 3 enhancement potentially replacing the Metriport HIE integration given TEFCA's larger 2026 network footprint. Requires legal analysis of whether attorney retrieval under Individual Access Services requires specific patient consent language beyond the existing HIPAA authorization template.

---

## 13. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Provider refuses to respond to TRACE-generated requests | High | Medium | Automated follow-up at day 10 and 20. Escalation toolkit for attorney: certified mail template, legal demand letter template. |
| OCR accuracy below threshold on poor-quality scans | High | Medium | All below-threshold pages flagged for attorney manual review. Accuracy tracking per document type. deepdoctection + DocTr handwriting spike required before Phase 1D. |
| Attorney does not complete QA review before using chronology | Medium | High | System enforces approval gate. Chronology cannot be exported as "Demand-Ready" without attorney sign-off. |
| PHI breach through cloud fax transmission error | Low | Severe | HIPAA-compliant fax provider with BAA. Confirmation logging. Misdirected fax incident response protocol. |
| Client forgets key providers during retainer confirmation | High | Medium | Provider checklist prompt surfaces all Benjamin-extracted references. Attorney encouraged to conduct brief provider confirmation call with client at retainer signing. |
| State bar challenge to TRACE as UPL | Low | Severe | Output is factual organization of records only. Prohibited output registry enforced. Attorney responsibility addendum in writing. No clinical or legal interpretation in any output. |
| Early access firm misuses chronology without attorney review | Low | High | Approval gate enforced. Audit trail captures all access. Attorney responsibility addendum establishes professional responsibility. |
| SETTLE input quality insufficient if TRACE chronology has errors | Medium | Medium | SETTLE explicitly requires attorney-approved TRACE chronology as input. If TRACE chronology is not approved, SETTLE cannot be run. |
| Extended Flag Registry Tier 2 NLP flags produce high false positive rate causing attorney alert fatigue | Medium | High | Tier 2 flags launch in Phase 2, not Phase 1D, giving early access data to calibrate accuracy before Tier 2 is activated. Per-flag-type accuracy tracking from Phase 3 onwards. ADVISORY flags do not block demand-ready gate — reduces friction cost of false positives. If any Tier 2 flag type exceeds 30% false positive rate in early access data, that flag type is demoted to INFORMATIONAL or disabled pending retraining. |
| phi_map loss or corruption renders chronology unreadable at portal display | Low | High | phi_map stored encrypted in PHI store alongside case record. Same backup and PITR policy as all PHI. phi_map integrity check runs at case open — if phi_map is missing or corrupt, portal surfaces alert and falls back to showing redacted tokens with an explanation, rather than silently displaying corrupted data. |

---

## 14. Appendices

### Appendix A — Prohibited Output Registry (TRACE-specific)

TRACE output must never contain the following language or equivalent formulations:

- Any characterization of injury severity as strong, weak, clear, significant, or minimal
- Any prediction of case outcome, settlement range, or recovery amount
- Any statement that a treatment is or is not causally related to the incident
- Any recommendation regarding legal strategy or demand amount
- Any statement characterizing the credibility of the client or any provider
- Any statement that a treatment gap supports or undermines the client's claim
- Any statement that a billing discrepancy indicates fraud or error
- Any characterization of a provider's notes as supporting or inconsistent with the client's account
- Any language that could be read as legal advice, medical advice, or case evaluation

### Appendix B — Human Checkpoint Summary

| Checkpoint | Who | When | What |
|-----------|-----|------|------|
| 1 — Provider list confirmation | Attorney | After TRACE generates checklist from intake record | Add, remove, correct providers before any request is sent |
| 2 — Outgoing request approval | Attorney | Before TRACE transmits any fax | Review and approve the complete provider list and request content |
| 3 — Chronology QA review | Attorney | After TRACE delivers completed chronology | Review all entries, annotate all flags, verify source citations |
| 4 — Demand-ready approval | Attorney | After QA review is complete | Explicit approval action — logged with name, date, timestamp |

### Appendix C — Early Access Communication Template

*For distribution to PIPELINE and OPERATIONS subscribers via portal notification:*

---

**TRACE Early Access — Now Available**

TrueVow is opening early access to TRACE — our medical record retrieval and chronology service — for PIPELINE and OPERATIONS subscribers with active INTAKE and converted retainers.

**What TRACE does:**
Automates the 12–18 hours of medical records work between retainer signing and demand preparation. Benjamin's intake record seeds the provider list. HIPAA-authorized requests go out automatically. Incoming records are processed into a source-cited treatment chronology. The TRACE flag system identifies treatment gaps, billing discrepancies, delayed initial treatment, sudden treatment stops, non-compliant language, clinician credibility notes, pre-existing condition signals, and more — all surfaced as factual observations for your review. You review, annotate, and approve — then the chronology is demand-ready.

**What TRACE does not do:**
Provide legal advice. Replace attorney review. Decide anything. You remain fully in control at every stage.

**Early access pricing:**
$299/month platform fee + $199 per settled case. You only pay the per-case fee when the case settles.

**Requirements:**
Active PIPELINE or OPERATIONS subscription. At least 3 retainer-converted cases in your portal. Signed BAA addendum and attorney responsibility addendum. Completed TRACE onboarding.

**To apply:**
[Apply for TRACE Early Access →]

Early access is limited to 20 firms. We review applications in the order received.

---

*TRACE processes retainer-converted cases only. All chronology output requires attorney review and approval before use in any legal matter. TrueVow is not a law firm and does not provide legal advice. TRACE output does not constitute legal advice, medical advice, or a case evaluation.*

---

**Document Control**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | July 2026 | TrueVow Product | Initial working draft |
| 0.2 | July 2026 | TrueVow Product | Added four SRD extractions from MalpracticeVibe review: SOL auto-calculation (§5.1.4), case data schema (§8.4), CPT/ICD-10 extraction with OMOP standardization (§5.5.2a), split-panel QA interface specification (§5.6.1a) |
| 0.3 | July 2026 | TrueVow Product | Stack updates: OCR changed to deepdoctection + DocTr (self-hosted), clinical NLP changed to OpenMed (self-hosted), PHI de-identification upgraded to OpenMed Nemotron two-level architecture, architecture diagram updated, phi_map retention policy added |
| 0.4 | July 2026 | TrueVow Product | Extended Flag Registry added (§5.5.3): 6 Tier 1 algorithmic flags (T1-01 through T1-06), 6 Tier 2 NLP-assisted flags (T2-02 through T2-06), Tier 3 judgment table, flag priority system (§5.5.4), color coding table, flag management (§5.5.5). User Story 4 acceptance criteria updated. Attorney Responsibility Addendum item 2 updated. |
| 0.5 | July 2026 | TrueVow Product | §12 expanded to 14 open questions: Q4 updated with Fax.Plus/Documo decision protocol, Q5 and Q6 marked resolved, Q10 marked resolved, Q13 added (Supabase HIPAA 11-item configuration), Q14 added (TEFCA evaluation). Risk table expanded to 10 risks. BAA timing clarified as production-only. |

*This document is a working draft. All requirements, timelines, and pricing are subject to change based on legal review, technical feasibility assessment, and early access learnings. No external commitments should be made based on this document without written approval from TrueVow leadership.*

