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

1. **Provider identification** — Extracts provider references from Benjamin's intake record using NLP. Cross-references against the NPI Registry for complete provider details. Surfaces a confirmation checklist to the attorney before any request is sent.

2. **HIPAA-authorized record requests** — Generates and transmits HIPAA-compliant record requests to all confirmed providers using encrypted cloud fax infrastructure. Uses the signed HIPAA authorization captured at retainer signing. Attorney approves the outgoing request list before transmission.

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

**Story 1 — Retainer converted**
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
- Treatment gaps of 14 days or more are flagged with date range and gap duration
- Billing discrepancies are flagged with specific description of the mismatch
- Each flag has an attorney annotation field: confirmed/explained/dismissed/follow-up required
- Chronology cannot be marked demand-ready until all Priority flags have an attorney annotation
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

### 5.2 HIPAA Authorization and Request Generation

**5.2.1 Authorization capture at retainer signing**
- TRACE onboarding configures a HIPAA authorization template in the attorney's retainer package
- Authorization template is reviewed and approved by the attorney during TRACE onboarding
- Authorization is attorney-specific (names the attorney and their firm as the authorized recipient)
- Signed authorization is stored in TRACE with the case record, linked to the client identifier
- Authorization must be signed before any record request is transmitted

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
- Duplicate detection: flags pages that appear in multiple incoming batches
- Misfiled documents: flags documents that appear to relate to a different patient or date range

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

**5.5.3 Flag management**
- All flags displayed in attorney QA interface with: flag type, description, source references, annotation field
- Attorney annotation options: Confirmed and Explained (free text) / Confirmed and Needs Follow-up / Dismissed (not relevant) / Resolved
- Flags cannot be deleted — only annotated. The audit trail shows every flag and its resolution
- Chronology cannot be marked demand-ready until all Priority flags (treatment gaps and billing discrepancies above threshold) have attorney annotations

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
  Scrollable list of all clinical events in date order. Each entry displays: date, provider, facility, event type, clinical description (verbatim from source), and flag status indicator (clean / flagged / annotated). Flagged items are visually distinguished with a color indicator — treatment gaps in amber, billing discrepancies in red, resolved flags in grey. Filter controls above the list allow filtering by provider, date range, event type, and flag status.

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

2. TRACE flags treatment gaps and billing inconsistencies as data observations derived from the records. These flags do not constitute legal analysis, clinical interpretation, or a representation of case facts. The attorney interprets and acts on all flags.

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
─────────────────────────────────────────────────────
INTAKE RECORD        NLP EXTRACTION         PROVIDER
(Benjamin JSON)  →  + NPI LOOKUP        →  CHECKLIST
                                           (Attorney Confirms)
                                                 ↓
                                         REQUEST GENERATION
                                         (PDF + HIPAA Auth)
                                                 ↓
                                    HIPAA CLOUD FAX TRANSMISSION
                                    (Encrypted, BAA-covered)
                                                 ↓
                                    SECURE INBOUND RECEIVE
                                    (Fax inbox / Upload portal)
                                                 ↓
                                    DOCUMENT PROCESSING
                                    OCR → Classification → Indexing
                                                 ↓
                                    CHRONOLOGY ENGINE
                                    NLP extraction → Date sort → Cite
                                                 ↓
                                    GAP + BILLING DETECTION
                                                 ↓
                                    ATTORNEY QA PORTAL
                                    Flag review → Annotation → Approval
                                                 ↓
                                    DEMAND-READY OUTPUT
                                    PDF + JSON export
─────────────────────────────────────────────────────
```

### 8.2 Data Flow and PHI Handling

- PHI enters TRACE only through: signed client HIPAA authorization + attorney-approved provider list
- PHI stored only in HIPAA-compliant, SOC 2 Type II certified infrastructure
- PHI never transmitted to any party other than: the originating healthcare provider (for requests), the attorney's firm (for records and chronology)
- PHI never included in any URL, notification subject line, or log entry accessible outside the secure portal
- All PHI access logged with user ID, timestamp, and action
- Case data segmented by firm — no attorney can access another firm's case data under any circumstance
- Data retention per firm: configurable per HIPAA and state bar record retention requirements (minimum 6 years)
- Data destruction at firm termination: documented process, confirmation delivered to attorney

### 8.3 Integration Points

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
| HIPAA authorization status | Signed / Pending / Expired |
| Provider list status | Draft / Attorney Confirmed / Locked |
| Retrieval status | Per-provider: Pending / Requested / Partial / Complete / Unresponsive |
| Case stage | Initialization / Retrieval / Processing / Chronology Ready / Attorney Review / Demand-Ready |
| Approval record | Attorney ID, timestamp, and confirmation text at Demand-Ready approval |

**Entity 2 — Chronology**

Ordered list of all clinical events across all providers. Each entry contains:

| Field | Description |
|-------|-------------|
| Event ID | Sequential identifier within the case |
| Timestamp | Date and time of clinical event (normalized from source) |
| Provider | Treating provider name |
| Facility | Facility name |
| Event type | Visit / Imaging / Prescription / Procedure / Discharge / Referral |
| Clinical description | Verbatim text from source record — not interpreted |
| Source document ID | Reference to the processed document in the document store |
| Source page number | Exact page within the source document |
| Flag reference | Link to Event Node if this entry has a flag — null if clean |
| Attorney annotation | Free-text annotation field — null until attorney adds one |
| Verify flag | Boolean — attorney can mark any entry for secondary review |

**Entity 3 — Event Nodes**

Atomic records for each flagged item. Each Event Node contains:

| Field | Description |
|-------|-------------|
| Node ID | Unique identifier |
| Flag type | Treatment Gap / Billing Discrepancy / Escalation Flag |
| Date range or date | For gaps: start and end date of the gap. For discrepancies: the specific date |
| Gap duration | Days between last treatment before gap and first treatment after (treatment gaps only) |
| Source document references | Document IDs and page numbers on both sides of the flag |
| System-generated description | Factual description of the discrepancy — no clinical or legal interpretation |
| CPT code extracted | For billing discrepancies: the extracted CPT code and its documentation requirement |
| Clinical note summary | For billing discrepancies: what the corresponding clinical note contains |
| Attorney annotation | Required field: Confirmed and Explained / Confirmed and Needs Follow-up / Dismissed / Resolved |
| Annotation text | Free-text explanation (required when status is Confirmed and Explained) |
| Annotation timestamp | Auto-populated when attorney saves annotation |
| Annotation attorney ID | Auto-populated from authenticated session |
| Resolution timestamp | Auto-populated when status is set to Resolved or Dismissed |

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
- Completed TRACE onboarding: HIPAA authorization template configured, retainer package updated, provider confirmation workflow reviewed

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
4. Which cloud fax vendor is selected? Fax.Plus, iFax, Documo, and Notifyre all meet baseline requirements. Selection requires: comparison of API depth for automated request generation, BAA terms review, SOC 2 report review, and pricing at expected early access volume.

5. What OCR engine is used for handwritten clinical notes — the highest-failure document type? Options include Google Document AI, Amazon Textract, and Azure Form Recognizer. Each has different accuracy profiles on medical handwriting. Requires accuracy benchmarking against a sample set of real PI medical records before selection.

6. How does TRACE handle records received in Spanish (common in California, Texas, Florida markets where Spanish-speaking clients are a significant portion of the PI caseload)? → Requires either a medical translation layer or bilingual NLP processing. Decision needed before build.

**Product:**
7. What is the minimum viable chronology output for early access — full gap detection and billing reconciliation, or just the organized chronology? → Recommendation: launch with chronology and gap detection only. Add billing reconciliation in Phase 4 after gap detection is validated. Reduces Phase 2 build scope and narrows the QA surface area for early access.

8. Should TRACE accept records from before the incident date (pre-existing condition documentation)? → These records are legally significant but require careful handling to avoid surfacing pre-existing conditions to the opposing party through the TRACE workflow. Attorney-controlled setting: opt-in per case.

9. What is the correct cap on records volume per case before TRACE requires manual intervention? → 500 pages has been used as the standard benchmark in the market. Cases above 2,000 pages (severe injury, long treatment history) may require different handling. Threshold to be confirmed during Phase 3.

---

## 13. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Provider refuses to respond to TRACE-generated requests | High | Medium | Automated follow-up at day 10 and 20. Escalation toolkit for attorney: certified mail template, legal demand letter template. |
| OCR accuracy below threshold on poor-quality scans | High | Medium | All below-threshold pages flagged for attorney manual review. Accuracy tracking per document type. |
| Attorney does not complete QA review before using chronology | Medium | High | System enforces approval gate. Chronology cannot be exported as "Demand-Ready" without attorney sign-off. |
| PHI breach through cloud fax transmission error | Low | Severe | HIPAA-compliant fax provider with BAA. Confirmation logging. Misdirected fax incident response protocol. |
| Client forgets key providers during retainer confirmation | High | Medium | Provider checklist prompt surfaces all Benjamin-extracted references. Attorney encouraged to conduct brief provider confirmation call with client at retainer signing. |
| State bar challenge to TRACE as UPL | Low | Severe | Output is factual organization of records only. Prohibited output registry enforced. Attorney responsibility addendum in writing. No clinical or legal interpretation in any output. |
| Early access firm misuses chronology without attorney review | Low | High | Approval gate enforced. Audit trail captures all access. Attorney responsibility addendum establishes professional responsibility. |
| SETTLE input quality insufficient if TRACE chronology has errors | Medium | Medium | SETTLE explicitly requires attorney-approved TRACE chronology as input. If TRACE chronology is not approved, SETTLE cannot be run. |

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
Automates the 12–18 hours of medical records work between retainer signing and demand preparation. Benjamin's intake record seeds the provider list. HIPAA-authorized requests go out automatically. Incoming records are processed into a source-cited treatment chronology. Treatment gaps and billing discrepancies are flagged for your review. You review, annotate, and approve — then the chronology is demand-ready.

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

*This document is a working draft. All requirements, timelines, and pricing are subject to change based on legal review, technical feasibility assessment, and early access learnings. No external commitments should be made based on this document without written approval from TrueVow leadership.*

