# TRACE — Phase 0 Deliverable Package
## Legal and Compliance Infrastructure
**Version:** 1.0  
**Status:** In Progress — Awaiting Healthcare Attorney Engagement  
**Classification:** Confidential — Internal Use Only  
**Governing Document:** TRACE PRD v0.1  
**Last Updated:** July 2026

---

## Purpose of This Document

Phase 0 is the prerequisite phase for TRACE. No engineering begins until every item in this document is complete and reviewed. This document defines:

1. Every deliverable required before the first line of TRACE code is written
2. Who owns each deliverable
3. What "complete" means for each item
4. The review and sign-off process
5. The three foundational legal documents in draft form for attorney review

Phase 0 has one governing principle: **legal and compliance infrastructure precedes technical build.** The cost of rebuilding a HIPAA-compliant data architecture after counsel identifies structural problems is 5–10x the cost of getting it right before a line is written.

---

## Section 1 — Phase 0 Deliverables Overview

| # | Deliverable | Owner | Dependency | Status |
|---|------------|-------|------------|--------|
| 1 | Healthcare attorney engaged | TrueVow leadership | None — first action | ☐ |
| 2 | HIPAA Security Risk Assessment | Healthcare attorney + Privacy Officer | Attorney engaged | ☐ |
| 3 | BAA template drafted and reviewed | Healthcare attorney | Risk Assessment | ☐ |
| 4 | Attorney Responsibility Addendum drafted | Healthcare attorney | BAA template | ☐ |
| 5 | HIPAA Authorization template drafted | Healthcare attorney | Attorney engaged | ☐ |
| 6 | Privacy Officer and Security Officer designated | TrueVow leadership | None | ☐ |
| 7 | Workforce HIPAA training completed | Privacy Officer | Officer designated | ☐ |
| 8 | Cloud fax vendor selected and BAA executed | TrueVow leadership + attorney | Risk Assessment | ☐ |
| 9 | SOC 2 Type II audit initiated | TrueVow engineering | Attorney engaged | ☐ |
| 10 | State-level records access requirements mapped | Healthcare attorney | Attorney engaged | ☐ |
| 11 | Phase 0 sign-off meeting | All stakeholders | All above complete | ☐ |

**Phase 0 is complete only when all 11 items are checked and the Phase 0 sign-off meeting has been held.**

---

## Section 2 — Deliverable 1: Healthcare Attorney Engagement

### 2.1 What Is Needed

A healthcare attorney with specific experience in:
- HIPAA Business Associate Agreements for legal tech companies
- Medical record retrieval workflows and HIPAA authorization requirements
- State-level medical records access statutes (California, Texas, Florida, New York, Illinois minimum — the five states with the highest PI attorney concentration)
- ABA professional responsibility rules as they intersect with third-party legal tech services

### 2.2 What the Attorney Receives at Engagement

On engagement, the healthcare attorney receives:
- TRACE PRD v0.1 (full document)
- This Phase 0 Deliverable document
- TrueVow's existing MSA and service agreement templates
- The three draft documents in Section 5 of this Phase 0 package for review and revision

### 2.3 Attorney's Scope of Work

The attorney's Phase 0 scope covers:

**Document drafting and review:**
- Review and revise the BAA template (Section 5.1 below)
- Review and revise the Attorney Responsibility Addendum (Section 5.2 below)
- Review and revise the HIPAA Authorization Template (Section 5.3 below)
- Review the cloud fax vendor BAA terms for the selected vendor
- Draft state-specific addenda where required (California CMIA, Texas Health & Safety Code Chapter 181, Florida HB 1537)

**Legal analysis:**
- Confirm TrueVow's classification under HIPAA: Business Associate of the PI attorney firm (not the healthcare provider)
- Confirm the BAA chain: TrueVow signs BAA with PI attorney firm → TrueVow executes downstream BAAs with cloud fax vendor and document processing infrastructure
- Confirm that the attorney responsibility addendum correctly allocates professional responsibility without creating an unauthorized practice of law exposure for TrueVow
- Review the prohibited output registry (PRD Appendix A) and confirm it is sufficient to prevent UPL characterization of TRACE output

**Risk Assessment support:**
- Review the completed HIPAA Security Risk Assessment and confirm it addresses all required safeguard categories under 45 CFR §164.302–318

### 2.4 Completion Criteria

Deliverable 1 is complete when: the healthcare attorney has signed an engagement letter, received all documents listed in 2.2, and confirmed the scope of work described in 2.3.

---

## Section 3 — Deliverable 2: HIPAA Security Risk Assessment

### 3.1 What It Is

The HIPAA Security Risk Assessment is an internal audit required under 45 CFR §164.308(a)(1) before any electronic PHI (ePHI) is created, received, maintained, or transmitted. It is not optional and it is not a one-time document — it must be updated whenever material changes to the system occur and reviewed annually.

For TRACE, the Risk Assessment answers: for every system, workflow, and person that will touch PHI, what are the risks and what safeguards are in place?

### 3.2 Scope of the TRACE Risk Assessment

The assessment covers the following threat categories per HHS guidance:

**Confidentiality threats:**
- Unauthorized access to PHI in transit (between TrueVow and cloud fax provider)
- Unauthorized access to PHI at rest (in document storage)
- Unauthorized access by TrueVow staff to attorney case data
- Unauthorized access by one attorney firm to another firm's case data
- PHI transmitted to wrong provider fax number
- PHI exposed in email notification content

**Integrity threats:**
- OCR extraction error producing incorrect clinical data in chronology
- Chronology entry incorrectly attributed to wrong source document
- Provider records corrupted during transmission or storage
- Unauthorized modification of approved chronology after attorney sign-off

**Availability threats:**
- Cloud fax service outage during active retrieval period
- Document storage outage blocking attorney access to records
- Portal unavailability preventing attorney QA review within critical window

### 3.3 Required Safeguards to Be Confirmed

The Risk Assessment must confirm that each of the following is implemented or planned before early access opens:

**Technical safeguards (45 CFR §164.312):**
- [ ] Unique user IDs for all portal access (no shared accounts)
- [ ] Automatic logoff after inactivity (configurable — 15 minutes default)
- [ ] Encryption in transit: TLS 1.2+ for all data movement
- [ ] Encryption at rest: AES-256 for all stored PHI
- [ ] Audit controls: every PHI access logged with user, timestamp, action, and data accessed
- [ ] PHI integrity controls: checksums on stored documents to detect unauthorized modification
- [ ] Transmission security: HIPAA-compliant encrypted fax for all record requests and receipts
- [ ] Multi-factor authentication for all attorney portal access

**Administrative safeguards (45 CFR §164.308):**
- [ ] Security Risk Analysis completed (this document)
- [ ] Workforce training policy documented and training completed
- [ ] Access management policy: minimum necessary access for all staff
- [ ] Incident response plan documented and tested
- [ ] Business Associate Agreement executed with each downstream vendor
- [ ] Contingency plan: backup, disaster recovery, and emergency mode procedures

**Physical safeguards (45 CFR §164.310):**
- [ ] All infrastructure hosted in SOC 2 Type II certified facilities
- [ ] No PHI processed on unmanaged or personal devices
- [ ] Workstation policy: screen lock, secure disposal of any printed PHI
- [ ] Media disposal policy: secure destruction of any storage media containing PHI

### 3.4 Risk Assessment Output

The completed Risk Assessment document must contain:
- Inventory of all systems that touch PHI
- Risk level rating per threat (Low / Medium / High)
- Current safeguard in place for each threat
- Residual risk after safeguard
- Remediation plan for any High residual risk items
- Sign-off by Privacy Officer and Security Officer
- Healthcare attorney review confirmation

### 3.5 Completion Criteria

Deliverable 2 is complete when: the Risk Assessment document is finalized, all High residual risk items have remediation plans confirmed, and the healthcare attorney has reviewed and confirmed it addresses the requirements of 45 CFR §164.302–318.

---

## Section 4 — Deliverables 6 and 7: Privacy Officer, Security Officer, and Workforce Training

### 4.1 Officer Designation

HIPAA requires covered entities and business associates to designate a Privacy Officer (45 CFR §164.530(a)) and a Security Officer (45 CFR §164.308(a)(2)). For TrueVow at early access stage, one person may hold both roles.

**Privacy Officer responsibilities:**
- Develops and implements HIPAA privacy policies and procedures
- Handles PHI-related complaints and breach notifications
- Ensures compliance with minimum necessary standards
- Reviews and updates privacy policies annually and after material system changes
- Point of contact for attorney firms on PHI handling questions

**Security Officer responsibilities:**
- Owns the Security Risk Assessment and its annual review
- Manages technical safeguard implementation and monitoring
- Leads incident response for security events involving PHI
- Reviews and approves access control changes
- Manages BAA compliance for downstream vendors

### 4.2 Workforce Training Requirements

Every TrueVow employee or contractor with access to TRACE case data must complete documented HIPAA training before being granted access. The training program must cover:

- What PHI is and how to identify it
- Minimum necessary access principle
- Secure handling of PHI in daily workflows
- Incident recognition and reporting procedure
- Consequences of HIPAA violations (civil and criminal penalties)
- TrueVow-specific policies: no PHI in email subject lines, no PHI in Slack, no PHI on personal devices, screen lock policy

Training must be:
- Completed before access to any TRACE PHI is granted
- Documented with completion records retained for 6 years
- Repeated annually
- Updated and re-completed when material policy changes occur

### 4.3 Completion Criteria

Deliverable 6 is complete when: Privacy Officer and Security Officer are designated in writing with documented role descriptions.

Deliverable 7 is complete when: all staff with TRACE data access have completed training and completion records are documented and retained.

---

## Section 5 — Three Foundational Legal Documents

These are working drafts for healthcare attorney review and revision. They are not final and must not be used without attorney sign-off.

---

### 5.1 Draft BAA Template — TrueVow ↔ PI Attorney Firm

---

**BUSINESS ASSOCIATE AGREEMENT**

This Business Associate Agreement ("Agreement") is entered into between **[Law Firm Name]**, a [state] law firm ("Covered Entity" or "Law Firm") and **TrueVow Global Tech FZE LLC**, a UAE limited liability company ("Business Associate" or "TrueVow"), effective as of the date of last signature below.

**RECITALS**

Law Firm is a law firm representing personal injury clients and, in connection with its representation, obtains and processes Protected Health Information ("PHI") of its clients pursuant to client authorization. TrueVow provides the TRACE service, which assists Law Firm in retrieving, processing, and organizing medical records pertaining to Law Firm's represented clients. In providing TRACE, TrueVow creates, receives, maintains, and transmits PHI on behalf of Law Firm, thereby constituting a Business Associate under the Health Insurance Portability and Accountability Act of 1996 and its implementing regulations ("HIPAA").

The parties enter this Agreement to satisfy the requirements of 45 CFR §164.504(e).

---

**ARTICLE 1 — DEFINITIONS**

1.1 **Breach** has the meaning set forth in 45 CFR §164.402.

1.2 **Business Associate** means TrueVow in its capacity as a service provider creating, receiving, maintaining, or transmitting PHI on behalf of Law Firm.

1.3 **Covered Entity** means Law Firm acting as an authorized representative of personal injury clients in connection with the retrieval of client medical records.

1.4 **Designated Record Set** has the meaning set forth in 45 CFR §164.501.

1.5 **Electronic Protected Health Information (ePHI)** means PHI that is transmitted by or maintained in electronic media.

1.6 **Protected Health Information (PHI)** has the meaning set forth in 45 CFR §160.103, limited to information that TrueVow creates, receives, maintains, or transmits on behalf of Law Firm.

1.7 **Required by Law** has the meaning set forth in 45 CFR §164.103.

1.8 **Secretary** means the Secretary of the U.S. Department of Health and Human Services.

1.9 **Security Incident** has the meaning set forth in 45 CFR §164.304.

1.10 **Subcontractor** means any entity to whom TrueVow delegates a function, activity, or service that involves the creation, receipt, maintenance, or transmission of PHI.

---

**ARTICLE 2 — PERMITTED USES AND DISCLOSURES**

2.1 **Permitted Uses.** TrueVow may use PHI only to the extent necessary to perform the TRACE service for Law Firm, including: medical record request generation and transmission, document receipt and storage, document processing and chronology generation, and delivery of chronology output to Law Firm through the TrueVow portal.

2.2 **Permitted Disclosures.** TrueVow may disclose PHI only: (a) to healthcare providers for the purpose of requesting medical records on behalf of Law Firm's clients pursuant to a signed client HIPAA authorization; (b) to Law Firm through the secure portal; (c) as Required by Law; (d) for TrueVow's proper management and administration, provided such disclosure is Required by Law or TrueVow obtains reasonable assurances from the recipient.

2.3 **Minimum Necessary.** TrueVow shall make reasonable efforts to use, disclose, and request only the minimum amount of PHI necessary to accomplish the permitted purpose.

2.4 **Prohibited Uses.** TrueVow shall not: (a) use or disclose PHI in any manner not permitted by this Agreement; (b) use PHI for marketing purposes; (c) sell PHI; (d) use PHI to train, improve, or develop any AI model without explicit written consent from Law Firm; (e) combine Law Firm's client PHI with PHI from other Law Firm clients in any manner that would enable identification of any individual.

---

**ARTICLE 3 — SAFEGUARDS**

3.1 **Administrative Safeguards.** TrueVow shall implement administrative safeguards as required by 45 CFR §164.308, including: designation of a Security Officer and Privacy Officer, completion of a Security Risk Analysis, workforce training, access management policies, and an incident response plan.

3.2 **Physical Safeguards.** TrueVow shall implement physical safeguards as required by 45 CFR §164.310, including hosting all ePHI in SOC 2 Type II certified data center facilities and maintaining workstation and media control policies.

3.3 **Technical Safeguards.** TrueVow shall implement technical safeguards as required by 45 CFR §164.312, including: AES-256 encryption at rest, TLS 1.2+ encryption in transit, unique user IDs, automatic logoff, audit controls, and multi-factor authentication for all portal access.

3.4 **Subcontractor Safeguards.** TrueVow shall ensure that any Subcontractor that creates, receives, maintains, or transmits PHI on behalf of TrueVow agrees to the same restrictions and conditions that apply to TrueVow under this Agreement by executing a written Business Associate Agreement with each such Subcontractor prior to disclosing any PHI.

---

**ARTICLE 4 — BREACH NOTIFICATION**

4.1 **Discovery.** TrueVow shall notify Law Firm of any Breach of Unsecured PHI without unreasonable delay and in no case later than **24 hours** after TrueVow discovers the Breach.

4.2 **Content of Notification.** Notification shall include, to the extent known: (a) the nature of the PHI involved; (b) the unauthorized person who used or received the PHI; (c) whether PHI was actually acquired or viewed; (d) the extent to which the risk has been mitigated; (e) a description of the Breach; (f) the date of the Breach and date of discovery; (g) steps Law Firm should take to protect itself and its clients; (h) what TrueVow is doing to investigate, mitigate, and prevent recurrence; (i) TrueVow's contact person.

4.3 **Security Incidents.** TrueVow shall report to Law Firm any Security Incident of which it becomes aware, including attempted unauthorized access, use, disclosure, modification, or destruction of PHI, within 5 business days of discovery.

---

**ARTICLE 5 — INDIVIDUAL RIGHTS**

5.1 TrueVow shall provide Law Firm access to PHI maintained in a Designated Record Set within 15 days of request to enable Law Firm to fulfill individual access rights under 45 CFR §164.524.

5.2 TrueVow shall make amendments to PHI in a Designated Record Set as directed by Law Firm within 30 days to enable Law Firm to fulfill amendment rights under 45 CFR §164.526.

5.3 TrueVow shall provide an accounting of disclosures of PHI upon Law Firm's request within 30 days to enable Law Firm to fulfill accounting rights under 45 CFR §164.528.

---

**ARTICLE 6 — AUDIT AND INSPECTION**

6.1 TrueVow shall make its internal practices, books, and records relating to the use and disclosure of PHI available to the Secretary for purposes of determining Law Firm's compliance with HIPAA.

6.2 TrueVow shall make its internal practices, books, and records relating to the use and disclosure of PHI available to Law Firm upon reasonable notice for audit purposes.

---

**ARTICLE 7 — DATA RETENTION AND DESTRUCTION**

7.1 **Retention.** TrueVow shall retain PHI in accordance with Law Firm's configured retention policy, subject to a minimum retention period of 6 years from the date of creation or last effective date, whichever is later, as required for HIPAA-related documentation.

7.2 **Destruction.** Upon termination of the TRACE service agreement, TrueVow shall, at Law Firm's election: (a) return all PHI to Law Firm in a mutually agreed format; or (b) destroy all PHI in TrueVow's possession using a NIST 800-88-compliant method, and provide written certification of destruction within 30 days of termination.

7.3 **Survival.** If return or destruction is not feasible, TrueVow shall extend the protections of this Agreement to such PHI and limit further use or disclosure to those purposes that make return or destruction infeasible.

---

**ARTICLE 8 — TERM AND TERMINATION**

8.1 **Term.** This Agreement shall be effective upon the date of last signature and shall remain in effect for the duration of the TRACE service agreement, unless terminated earlier under this Article.

8.2 **Termination for Cause.** Law Firm may terminate this Agreement immediately upon written notice if TrueVow materially breaches a provision of this Agreement and fails to cure the breach within 30 days of written notice, or if cure is not possible.

8.3 **Effect of Termination.** Upon termination, the obligations under Article 7 apply. All other obligations of this Agreement that by their nature should survive termination shall survive.

---

**ARTICLE 9 — GENERAL PROVISIONS**

9.1 **Amendment.** The parties agree to amend this Agreement to the extent necessary to comply with changes in applicable law, including HIPAA and its implementing regulations.

9.2 **No Third-Party Beneficiaries.** This Agreement is for the sole benefit of the parties and their successors and assigns. Nothing herein shall create any rights in any third party.

9.3 **Interpretation.** The parties agree that this Agreement shall be interpreted in a manner that allows Law Firm to comply with HIPAA. In the event of a conflict between this Agreement and the TRACE service agreement, the provisions of this Agreement shall govern with respect to PHI.

9.4 **Governing Law.** This Agreement shall be governed by and construed in accordance with the laws of the United Arab Emirates, except to the extent superseded by HIPAA and applicable U.S. federal law.

---

**SIGNATURES**

| Law Firm | TrueVow Global Tech FZE LLC |
|----------|----------------------------|
| Signature: _________________ | Signature: _________________ |
| Name: _________________ | Name: _________________ |
| Title: _________________ | Title: _________________ |
| Date: _________________ | Date: _________________ |

---

*[HEALTHCARE ATTORNEY NOTE: This draft requires jurisdiction-specific review for California (CMIA), Texas (Health & Safety Code Ch. 181), Florida (HB 1537), New York (SHIELD Act), and any other state where early access firms are located. The governing law clause requires specific legal analysis given TrueVow's UAE entity structure and U.S. PHI processing. The definition of "Covered Entity" is non-standard and requires confirmation that PI attorney firms are correctly characterized under this framework.]*

---

### 5.2 Draft Attorney Responsibility Addendum

---

**TRACE ATTORNEY RESPONSIBILITY ADDENDUM**

This Addendum is entered into between **[Law Firm Name]** ("Attorney Firm") and **TrueVow Global Tech FZE LLC** ("TrueVow") as a supplement to the TRACE service agreement and Business Associate Agreement. It is effective upon the date of last signature.

**BACKGROUND**

TrueVow's TRACE service automates the retrieval, organization, and chronology generation of medical records for personal injury cases in which the Attorney Firm represents the client. The parties enter this Addendum to clearly define the Attorney Firm's professional responsibility obligations in connection with TRACE output and to confirm that TRACE is a workflow tool, not a legal service provider.

---

**1. ATTORNEY REVIEW OBLIGATION**

1.1 The Attorney Firm acknowledges and agrees that TRACE chronology output is a structured organization of medical records retrieved on behalf of the Attorney Firm's client. It is not legal work product, legal advice, medical advice, a medical opinion, or a case evaluation.

1.2 The Attorney Firm is solely responsible for reviewing all TRACE chronology output before it is used in any demand letter, negotiation, legal pleading, mediation, or other legal matter.

1.3 The Attorney Firm is solely responsible for verifying that all material facts in any legal submission that relies on TRACE output are accurate and supported by the underlying source records, which remain available for attorney review in the TrueVow portal.

1.4 The Attorney Firm's approval action within the TrueVow portal — marking a chronology as "Demand-Ready — Attorney Approved" — constitutes the Attorney Firm's confirmation that it has reviewed the chronology and accepts responsibility for its use.

**2. PROVIDER IDENTIFICATION OBLIGATION**

2.1 The Attorney Firm acknowledges that TRACE identifies providers from the intake record and retainer confirmation process, and that this identification may not be complete.

2.2 The Attorney Firm is responsible for ensuring that all providers who treated the client for injuries related to the matter have been identified and added to the TRACE provider confirmation list before record requests are transmitted.

2.3 Any provider not included in the confirmed provider list will not receive a record request from TRACE. The Attorney Firm bears responsibility for the completeness of the provider list.

**3. INTERPRETATION OF FLAGS**

3.1 TRACE identifies treatment gaps and billing discrepancies as factual observations derived from the retrieved records. These flags are data observations only. They do not constitute legal analysis, clinical interpretation, a representation of case facts, or a suggestion regarding case strategy.

3.2 The Attorney Firm is responsible for interpreting and acting on all flags, including determining whether a treatment gap requires client follow-up, whether a billing discrepancy is material, and how any flag should be addressed in the demand or negotiation.

**4. NO LEGAL ADVICE**

4.1 TrueVow is not a law firm. TRACE does not provide legal advice. No communication from TrueVow or its staff regarding TRACE output constitutes legal advice to the Attorney Firm or its clients.

4.2 The Attorney Firm shall not represent to any client, opposing party, court, mediator, or other person that TRACE output constitutes an independent legal or medical evaluation of any kind.

**5. PROFESSIONAL RESPONSIBILITY**

5.1 The Attorney Firm maintains all professional responsibility obligations for the completeness and accuracy of any demand, pleading, mediation position, or other legal submission that relies on TRACE output.

5.2 The Attorney Firm acknowledges that under ABA Formal Opinion 512, it is responsible for independently verifying all material facts against original source documents before using AI-assisted output in any legal submission, and for disclosing AI use to clients where required by applicable rules of professional conduct.

5.3 The Attorney Firm is responsible for compliance with all applicable rules of professional conduct in all jurisdictions where it practices, including rules governing the use of third-party services that handle client information.

**6. CLIENT DISCLOSURE**

6.1 The Attorney Firm shall include disclosure of TRACE in its client engagement letter or obtain separate client consent confirming that a third-party AI service processes the client's medical records on behalf of the Attorney Firm.

6.2 A suggested disclosure clause for the engagement letter:

*"In connection with your representation, [Law Firm Name] may use a third-party medical record retrieval and processing service (TrueVow TRACE) to assist with obtaining and organizing your medical records. This service operates under a signed Business Associate Agreement and handles your health information in compliance with HIPAA. Your attorney reviews all output before it is used in your case."*

---

**SIGNATURES**

| Law Firm | TrueVow Global Tech FZE LLC |
|----------|----------------------------|
| Signature: _________________ | Signature: _________________ |
| Name: _________________ | Name: _________________ |
| Bar Number: _________________ | Title: _________________ |
| Date: _________________ | Date: _________________ |

---

*[HEALTHCARE ATTORNEY NOTE: Section 5.2 references ABA Formal Opinion 512. This section requires review against the specific rules of professional conduct in each state where early access firms are located, as state bar rules vary. California, for example, has specific AI disclosure requirements under California Rules of Professional Conduct that may require more specific client disclosure language than the suggested clause in Section 6.2. This addendum should be reviewed by a legal ethics attorney in addition to a HIPAA attorney.]*

---

### 5.3 Draft HIPAA Authorization Template for Retainer Package

---

**AUTHORIZATION FOR RELEASE OF MEDICAL RECORDS**
*(Pursuant to 45 CFR §164.508 — HIPAA)*

**CLIENT INFORMATION**

Name: _________________________________  
Date of Birth: _________________________________  
Address: _________________________________  
Phone: _________________________________

---

**AUTHORIZATION**

I, the undersigned, hereby authorize the healthcare provider(s) identified below to release my medical records to:

**Authorized Recipient:**  
[Law Firm Name]  
[Law Firm Address]  
Fax: [TrueVow TRACE Secure Fax Number]  
Reference: [TRACE Case Reference — to be assigned]

I understand that [Law Firm Name] uses TrueVow TRACE, a HIPAA-compliant third-party service, to receive and process my medical records on the Law Firm's behalf. TrueVow TRACE operates under a Business Associate Agreement with [Law Firm Name] and handles my health information in compliance with HIPAA. My records will be used solely for the purpose of my personal injury representation and will not be shared with any other party without my consent.

---

**RECORDS REQUESTED**

☐ All medical records related to treatment for injuries sustained on or after: **[Incident Date]**  
☐ All medical records from: **[Start Date]** to **[End Date]**  
☐ Emergency room records  
☐ Imaging and radiology reports  
☐ Physical therapy / occupational therapy records  
☐ Physician and specialist notes  
☐ Billing and itemized statements  
☐ Pharmacy records  
☐ Other: _________________________________

---

**PURPOSE**

This authorization is given for the purpose of: Personal injury legal representation and case preparation.

---

**EXPIRATION**

This authorization expires: **18 months from the date of signature**, or upon conclusion of my legal matter, whichever is earlier.

---

**PATIENT RIGHTS**

I understand that:

1. I have the right to revoke this authorization at any time by providing written notice to [Law Firm Name]. Revocation will not affect actions taken before the revocation is received.

2. The healthcare provider may not condition my treatment, payment, enrollment, or eligibility on whether I sign this authorization.

3. Information disclosed pursuant to this authorization may be re-disclosed by the recipient and may no longer be protected by HIPAA, to the extent permitted by applicable law.

4. I have the right to receive a copy of this signed authorization.

5. I am not required to sign this authorization as a condition of receiving treatment.

---

**HEALTHCARE PROVIDER(S) AUTHORIZED TO RELEASE RECORDS**

*(Complete one section per provider — additional pages may be attached)*

Provider 1:  
Name: _________________________________  
Facility: _________________________________  
Address: _________________________________  
Fax: _________________________________  
Dates of Service: _________________________________

Provider 2:  
Name: _________________________________  
Facility: _________________________________  
Address: _________________________________  
Fax: _________________________________  
Dates of Service: _________________________________

*(Additional providers: see attached)*

---

**SIGNATURE**

Client Signature: _________________________________  
Date: _________________________________

If signing as personal representative:  
Name: _________________________________  
Relationship: _________________________________  
Authority: _________________________________

---

*[HEALTHCARE ATTORNEY NOTE: This template requires state-specific review. California requires additional language under the Confidentiality of Medical Information Act (CMIA). Texas requires specific language under Health & Safety Code Chapter 181. Florida has specific requirements for mental health records (Chapter 394) and substance abuse records (Chapter 397) that require separate authorizations. The authorization should be reviewed for compliance in every state where early access firms practice before it is incorporated into any retainer package.]*

---

## Section 6 — Deliverable 8: Cloud Fax Vendor Selection

### 6.1 Vendor Evaluation Criteria

The following criteria must all be satisfied before a vendor is selected. All criteria are non-negotiable.

| Criterion | Required Standard | Fax.Plus | iFax | Documo | Notifyre |
|-----------|------------------|---------|------|--------|---------|
| BAA available | Yes, at selected tier | ✓ Enterprise | ✓ Enterprise | ✓ | ✓ |
| SOC 2 Type II | Current report available | Confirm | Confirm | Confirm | Confirm |
| TLS 1.2+ in transit | Required | ✓ | ✓ | ✓ | ✓ |
| AES-256 at rest | Required | ✓ | ✓ | ✓ | ✓ |
| Audit trails | Full transmission logs | ✓ | ✓ | ✓ | ✓ |
| API integration | REST API + webhooks | ✓ | ✓ | ✓ | ✓ |
| HIPAA mode | No PHI in notifications | ✓ | Confirm | Confirm | Confirm |
| MFA support | Required | ✓ | ✓ | Confirm | Confirm |
| Delivery confirmation | Per-fax confirmation | ✓ | ✓ | ✓ | ✓ |
| Failed fax retry | Automatic retry | ✓ | ✓ | Confirm | Confirm |

### 6.2 Vendor Selection Process

1. Request current SOC 2 Type II audit report from each candidate vendor (not a summary badge — the full auditor report with testing period and findings)
2. Request BAA terms from each candidate vendor for review by healthcare attorney
3. Request API documentation and confirm webhook support for: fax sent, fax delivered, fax failed, inbound fax received
4. Healthcare attorney reviews BAA terms for all candidates
5. Engineering reviews API documentation for integration feasibility
6. Selection made based on: BAA terms quality, API depth, delivery reliability data, and pricing at expected early access volume (estimated 200–500 faxes per month across all early access firms)
7. Execute BAA with selected vendor before any PHI is transmitted

### 6.3 Completion Criteria

Deliverable 8 is complete when: vendor is selected, current SOC 2 Type II report has been reviewed and confirmed, BAA is executed with the selected vendor, and API integration feasibility is confirmed by engineering.

---

## Section 7 — Deliverable 9: SOC 2 Type II Audit Initiation

### 7.1 Why SOC 2 Type II

SOC 2 Type II certification is required for TRACE because:
- Every attorney firm evaluating TRACE will ask for it
- It is the standard compliance credential for legal tech companies handling PHI
- The cloud fax vendor evaluation criteria require it
- It is the primary mechanism for demonstrating that TrueVow's security controls are not just documented but actually operating effectively over time

Type II (not Type I) is required because Type I only confirms controls exist at a point in time. Type II confirms they operated effectively over a period (typically 6–12 months). Attorney buyers — especially those at PIPELINE and OPERATIONS tier — will ask for a Type II report, not a Type I.

### 7.2 Timeline Implications

A Type II report covers a minimum observation period of 6 months. This means the audit must be initiated no later than 6 months before the first early access firm is onboarded, if a Type II report is to be available at early access launch.

**Practical implication:** If early access targets Month 6–8 of the development timeline, the SOC 2 audit must be initiated in Phase 0 — not Phase 3.

### 7.3 Interim Approach

While the Type II observation period is running, TrueVow can:
- Complete a SOC 2 Type I (point-in-time controls confirmation) as an interim credential
- Include the Type II initiation date and expected completion date in the TRACE Early Access terms
- Be transparent with early access attorneys that Type II is in progress and provide the Type I report as interim evidence

### 7.4 Completion Criteria

Deliverable 9 is complete when: a qualified SOC 2 auditor has been engaged, the audit scope has been defined (must include TRACE data systems), and the observation period has formally begun.

---

## Section 8 — Deliverable 10: State-Level Records Access Requirements

### 8.1 Federal Baseline

Federal HIPAA (45 CFR §164.524) gives patients the right to access their own records and to authorize release to third parties. It sets the national floor. States may impose additional requirements.

### 8.2 Priority States for Early Access

The five states with the highest PI attorney concentration — and therefore the most likely early access firm locations — each have additional requirements:

**California — Confidentiality of Medical Information Act (CMIA)**
- Health & Safety Code §56.10 et seq.
- CMIA provides stronger protections than HIPAA in several areas
- Specific authorization language required for release to attorneys
- Mental health, substance abuse, HIV/AIDS records require separate authorizations
- Action required: California-specific HIPAA authorization addendum

**Texas — Health & Safety Code Chapter 181**
- Texas Medical Privacy Act
- Requires specific state notice language in authorization forms
- Electronic health records: specific provisions for digital release
- Action required: Texas-specific authorization language confirmed by attorney

**Florida — Various statutes**
- Chapter 395 (hospital records), Chapter 456 (health practitioner records)
- Mental health: Chapter 394 (Baker Act records require separate authorization)
- Substance abuse: Chapter 397 (Marchman Act records require separate authorization)
- Action required: Florida-specific authorization forms for mental health and substance abuse records

**New York — SHIELD Act + Public Health Law §18**
- PHI of New York residents has specific access and notification requirements
- Action required: New York-specific provisions confirmed by attorney

**Illinois — Medical Patient Rights Act**
- 410 ILCS 50
- Specific authorization requirements for release to attorneys
- Action required: Illinois-specific authorization language confirmed by attorney

### 8.3 Completion Criteria

Deliverable 10 is complete when: the healthcare attorney has reviewed the authorization template against the requirements of all five priority states and produced state-specific addenda or language modifications for each state where HIPAA authorization template language is insufficient.

---

## Section 9 — Phase 0 Sign-Off Meeting

### 9.1 Purpose

The Phase 0 Sign-Off Meeting is the gate between Phase 0 and Phase 1 engineering build. No engineering work begins until this meeting confirms all 11 deliverables are complete.

### 9.2 Attendees

- TrueVow leadership
- Healthcare attorney
- Privacy Officer / Security Officer
- Engineering lead
- Product owner

### 9.3 Agenda

1. Confirmation that all 11 Phase 0 deliverables are complete with documentation
2. Healthcare attorney confirms: BAA template, attorney responsibility addendum, and HIPAA authorization template are ready for early access use
3. Healthcare attorney confirms: HIPAA Security Risk Assessment is complete and all High residual risk items have remediation plans
4. Cloud fax vendor confirmed: BAA executed, SOC 2 report reviewed
5. SOC 2 audit confirmed: auditor engaged, observation period begun
6. State-level requirements confirmed: state-specific addenda or language modifications ready for all five priority states
7. Engineering lead confirms: Phase 1 technical scoping document is ready and technical build can begin
8. Product owner confirms: early access cohort target (5 firms for Phase 1) and support workflow are defined
9. Formal sign-off: all attendees confirm Phase 0 is complete and Phase 1 may begin

### 9.4 Sign-Off Record

| Attendee | Role | Signature | Date |
|---------|------|-----------|------|
| | TrueVow CEO | | |
| | Healthcare Attorney | | |
| | Privacy / Security Officer | | |
| | Engineering Lead | | |
| | Product Owner | | |

---

## Section 10 — Phase 0 Timeline

| Week | Activities |
|------|-----------|
| Week 1 | Engage healthcare attorney. Provide PRD and this Phase 0 document. Designate Privacy Officer and Security Officer. Initiate SOC 2 auditor selection. |
| Week 2 | Attorney begins BAA review. Begin HIPAA Security Risk Assessment. Request SOC 2 reports and BAA terms from cloud fax vendor candidates. |
| Week 3 | Attorney produces first draft revisions to BAA, attorney responsibility addendum, and HIPAA authorization template. Begin workforce HIPAA training. SOC 2 auditor shortlist. |
| Week 4 | Internal review of attorney draft documents. Cloud fax vendor candidate BAA terms reviewed by attorney. |
| Week 5 | Attorney finalizes all three documents. HIPAA Security Risk Assessment completed and reviewed by attorney. SOC 2 auditor engaged, scope defined. |
| Week 6 | Cloud fax vendor selected. BAA executed with selected vendor. Workforce training completed and documented. State-specific authorization addenda finalized. |
| Week 7 | All Phase 0 deliverables confirmed complete. Phase 0 sign-off meeting held. |
| Week 8 | Phase 1 engineering build begins. |

---

## Section 11 — What Happens After Phase 0

Phase 0 completion unlocks the parallel tracks that run through Phase 1 and Phase 2:

**Engineering Track (Phase 1 — Months 2–4):**
- NPI Registry API integration
- Provider extraction NLP on intake record JSON
- Provider confirmation checklist UI in portal
- HIPAA authorization integration into retainer workflow
- Cloud fax transmission pipeline (request generation, transmission, confirmation logging)
- Secure inbound fax receive infrastructure
- OCR processing pipeline (spike results determine engine selection)
- Document classification model
- Case data storage with PHI segmentation

**Engineering Track (Phase 2 — Months 4–6):**
- Chronology extraction NLP
- Source citation linking
- Gap detection algorithm
- Flag management system and attorney QA interface
- Approval action and audit logging
- PDF and JSON export

**Product Track (running throughout):**
- Early access firm identification and qualification
- Support contact workflow design
- Feedback collection instrument design
- Case study collection framework

**Compliance Track (running throughout):**
- SOC 2 observation period ongoing
- Annual HIPAA training schedule established
- Risk Assessment review triggers defined and documented

The output of Phase 0 is not just legal documents. It is the operating foundation that every downstream decision rests on. A TRACE product built without Phase 0 complete is a TRACE product that cannot legally operate.

---

*Document Control*

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | July 2026 | Initial draft for healthcare attorney review |

*This document contains draft legal instruments for attorney review. No document in Section 5 is final or suitable for use without review and approval by a qualified healthcare attorney. All drafts are for discussion purposes only.*

