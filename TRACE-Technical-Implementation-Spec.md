# TRACE — Technical Implementation Specification
## Instructions for AI Coding Agent
**Version:** 1.0  
**Status:** Ready for Phase 1 Build  
**Prerequisite:** TRACE PRD v0.1 (read before this document)  
**Last Updated:** July 2026  
**Classification:** Confidential — Engineering Use Only

---

## How to Use This Document

You are a coding agent building TRACE — TrueVow's medical record retrieval and chronology engine for solo and small personal injury law firms.

Read this document from top to bottom before writing a single line of code. Every architectural decision in this document is final for Phase 1. Do not substitute alternative libraries, frameworks, or approaches without flagging the change and receiving explicit approval. The reasons for each decision are stated — they are not preferences, they are constraints driven by HIPAA compliance, attorney professional responsibility rules, and the TrueVow product architecture.

When you encounter a section marked **[DECISION LOCKED]**, do not deviate. When you encounter a section marked **[IMPLEMENTATION CHOICE]**, you have discretion within the stated boundaries.

---

## Part 1 — What You Are Building

### 1.1 The Product in One Paragraph

TRACE is a cloud-hosted, attorney-facing web application that automates the medical record retrieval and chronology build for personal injury cases that have already converted to signed retainers through TrueVow's INTAKE system. It sits inside the existing TrueVow attorney portal — not as a standalone application. The attorney who is already using INTAKE to review Benjamin's structured intake records will see a new "TRACE" section appear in their portal when a lead is marked as retainer-converted. Everything TRACE does flows from that trigger.

### 1.2 The User and Their Constraints

**Primary user:** Solo PI attorney. 1 person. No paralegal. No IT support. No tolerance for technical complexity. They are in court three days a week. They review TRACE on a laptop or tablet between hearings. Every interface decision must assume this user has 30 minutes to review a case, not 3 hours.

**What this means for you:** No multi-step onboarding flows. No settings screens with more than 5 options. No technical error messages visible to the attorney. Every action in the portal must be completable in under 3 clicks from the point of decision. If something fails, the attorney sees a plain-English message and a support contact — not a stack trace.

### 1.3 The Four Things TRACE Does — In Order

Do not build these out of order. Each step depends on the previous one being stable.

```
Step 1: Case Initialization
When attorney marks a lead as "Retainer Signed" in portal,
TRACE creates a case record, calculates the SOL deadline,
and triggers provider identification from the intake record.

Step 2: Provider Confirmation + Record Request
Attorney reviews and confirms provider list.
TRACE generates HIPAA-compliant fax requests.
Attorney approves outgoing request list.
TRACE transmits requests via cloud fax API.

Step 3: Record Receipt + Processing
Incoming records arrive via secure fax inbox.
TRACE runs OCR, classifies documents, indexes by provider and date.
Records are organized into the case data schema.

Step 4: Chronology + QA Delivery
TRACE builds the treatment chronology with source citations.
Runs gap detection and billing reconciliation.
Delivers chronology to attorney QA interface.
Attorney annotates flags and approves demand-ready status.
```

### 1.4 What TRACE Does NOT Do — Enforced at Code Level

These are hard constraints. They are not guidelines. The system must make them technically impossible, not just policy-prohibited.

- **Never generate text that characterizes a legal claim** — the words "malpractice", "upcoding", "fraud", "strong case", "weak case", "liability", "causation" must not appear in any system-generated output shown to the attorney or exportable from the system. Build a prohibited string filter that runs on all LLM outputs before they are written to the database or displayed in the UI.

- **Never allow a case to advance past Step 2 without attorney approval of the provider list** — the fax transmission endpoint must check for a confirmed provider list timestamp before accepting a transmission request. If the timestamp is absent, return a 403 with the message "Provider list not yet confirmed by attorney."

- **Never allow a chronology to be marked demand-ready with unannotated Priority flags** — the demand-ready approval endpoint must check that all Event Nodes with flag_type of TREATMENT_GAP or BILLING_DISCREPANCY have a non-null attorney_annotation field. If any are null, return a 400 with the count of unannotated flags.

- **Never display PHI in any URL, notification subject line, email subject, or log entry** — client names, dates of birth, and case details must reference only the opaque case ID and tokenized client reference in all system layers except the encrypted PHI store and the authenticated portal session.

- **Never store any case data locally on the attorney's device** — no localStorage, no IndexedDB, no service worker cache of PHI. The portal is a server-rendered or API-driven interface only.

---

## Part 2 — Technology Stack

### 2.1 Stack Decisions [DECISION LOCKED]

Every technology choice below is final for Phase 1. The reasons are stated. Do not substitute.

**Backend: Python 3.11+ with FastAPI**

Reason: FastAPI's async request handling is necessary for the document processing pipeline where multiple records can be processed simultaneously. Python is the language of the medical NLP ecosystem (spaCy, QuickUMLS, OMOP mappings). The TrueVow team can maintain Python. Do not substitute Node.js, Go, or any other language.

**Database: PostgreSQL 15+**

Reason: TRACE's case data schema has relational integrity requirements — chronology entries must link to source documents, event nodes must link to chronology entries, and all links must be enforced at the database level, not the application level. PostgreSQL's foreign key constraints and audit extension (pgaudit) provide the HIPAA audit logging requirement without custom implementation. Do not substitute MongoDB, DynamoDB, or any document store — the schema integrity rules in PRD Section 8.4 require relational enforcement.

**PHI Store: Separate encrypted PostgreSQL instance with column-level encryption**

Reason: Client PII (name, DOB, address) is stored in a separate database instance from case operational data. The case operational database references only the opaque case ID and tokenized client reference. If the operational database is compromised, client PII is not exposed. Column-level encryption using pgcrypto with AES-256. Encryption keys managed via AWS KMS or equivalent — never stored in application code or environment variables accessible to the application process.

**File Storage: HIPAA-Compliant Encrypted Object Storage [IMPLEMENTATION CHOICE — match your existing cloud]**

Reason: Incoming medical records (PDFs, faxes, scanned documents) are stored as encrypted binary objects in object storage. They are never stored in the database. The database holds only the storage object key, document metadata, and page-level index. All object access uses pre-signed/time-limited URLs with 15-minute expiry — the portal never serves document bytes directly from application memory.

Use whichever of the following matches your existing repo infrastructure:

| Your cloud | Service | Encryption | Time-limited URL mechanism | BAA coverage |
|-----------|---------|-----------|--------------------------|-------------|
| AWS | S3 with SSE-KMS | Customer-managed KMS key | Pre-signed URL (15 min) | AWS BAA |
| Google Cloud | Cloud Storage with CMEK | Customer-managed key in Cloud KMS | Signed URL (15 min) | Google BAA |
| Azure | Blob Storage with CMK | Customer-managed key in Azure Key Vault | SAS token (15 min) | Microsoft BAA |

The application code references a storage abstraction layer — not the cloud SDK directly. Build a `StorageService` interface with `upload(key, bytes)`, `download(key)`, and `presign(key, expiry_seconds)` methods. Swap the implementation by environment variable. This means switching clouds later requires only a new implementation of the interface, not changes to any endpoint or job.

```python
# storage_service.py — abstraction layer
class StorageService:
    def upload(self, key: str, data: bytes, content_type: str) -> str: ...
    def presign(self, key: str, expiry_seconds: int = 900) -> str: ...
    def delete(self, key: str) -> None: ...

# Implementations injected via dependency injection based on STORAGE_PROVIDER env var
# STORAGE_PROVIDER=s3 → S3StorageService
# STORAGE_PROVIDER=gcs → GCSStorageService  
# STORAGE_PROVIDER=azure → AzureBlobStorageService
```

**Non-negotiable regardless of cloud:**
- All objects encrypted at rest with customer-managed keys
- All objects private — no public access policy
- Pre-signed/SAS URLs expire at 15 minutes maximum
- The cloud provider must have a signed BAA covering this storage service
- Bucket/container must be in a region covered by your BAA

**OCR: AWS Textract [cross-cloud capable — does not require AWS hosting]**

Reason: Textract provides the best accuracy on mixed document types (digital PDFs and scanned documents) and handles handwritten clinical notes better than open-source alternatives at the accuracy levels required (85%+ on clean scans per PRD Section 6.2). Textract is a standalone API service — your application can call it from Google Cloud, Azure, or any other infrastructure via HTTPS. You do not need to be hosted on AWS to use Textract.

HIPAA compliance for cross-cloud Textract use: you must have an AWS BAA in place. AWS's standard BAA includes Textract as a HIPAA-eligible service and requires an AWS Business Support plan minimum. PHI sent to Textract and received back is encrypted in transit (TLS 1.2+) and covered by the BAA. Cross-cloud API calls are permissible under HIPAA — same-cloud routing is not a requirement.

**If you already have an AWS BAA for another service (e.g., you use any AWS service elsewhere):** keep Textract. No additional work required.

**If you have no AWS relationship at all and want to avoid adding one:**

| Alternative | BAA | Accuracy on medical handwriting | Notes |
|-------------|-----|--------------------------------|-------|
| Google Document AI | Google BAA (Cloud Healthcare API) | Good — comparable to Textract on digital PDFs, slightly below on handwriting | Requires enabling Cloud Healthcare API specifically for BAA coverage |
| Azure AI Document Intelligence | Microsoft BAA | Good on digital PDFs, weaker on handwriting | Acceptable if already on Azure |
| Tesseract (self-hosted) | None needed (self-hosted) | Poor on handwriting — does not meet the 85% accuracy target | Not recommended |

**Default decision:** Use AWS Textract regardless of hosting platform. It is the most accurate option for medical records, the BAA is straightforward to execute, and the cross-cloud API call adds negligible latency. Only substitute if AWS is explicitly prohibited by your organization's cloud policy.

**Cloud Fax: Fax.Plus Enterprise**

Reason: Selected during Phase 0 vendor evaluation. BAA is executed. SOC 2 Type II report reviewed. API supports webhook callbacks for delivery confirmation. HIPAA mode enabled (no PHI in email notifications). Do not substitute another fax vendor without legal review of BAA terms.

**NLP for Clinical Event Extraction: spaCy with en_core_sci_md model**

Reason: spaCy's medical NLP model (en_core_sci_md from scispaCy) is trained on biomedical text and provides the entity recognition accuracy needed for clinical event extraction from medical records. It runs as a service within TrueVow's infrastructure — no PHI is sent to external NLP APIs. Do not use OpenAI, Anthropic, or any external LLM API for PHI processing. All AI/ML processing of medical records must happen inside TrueVow's HIPAA-compliant infrastructure boundary.

**LLM for Billing Reconciliation: Azure OpenAI Service (GPT-4o-mini) [DECISION LOCKED — see DeepSeek note below]**

Reason: The billing reconciliation comparison task — matching CPT code documentation requirements against clinical note content — benefits from language model reasoning but must never send PHI to any provider without a signed Business Associate Agreement. Azure OpenAI Service is BAA-covered under Microsoft's standard Healthcare BAA, lower cost than Claude claude-sonnet-4-6 direct, and suitable for the structured comparison task TRACE requires.

**Why not DeepSeek V4 Pro:** DeepSeek does not currently publish a HIPAA BAA for its API service. Its infrastructure is primarily China-based, which creates a data residency risk — Chinese law can compel data disclosure in ways that conflict with HIPAA patient rights. Until DeepSeek publishes a HIPAA BAA and your legal counsel approves the data residency question in writing, DeepSeek cannot be used for any task that involves PHI or PHI-derived data. This is not a preference — it is a HIPAA compliance requirement. If DeepSeek subsequently publishes a BAA and your legal counsel approves, update this decision with written sign-off from the Privacy Officer.

**BAA-covered LLM options by cost (lowest to highest):**

| Option | Provider BAA | Cost tier | Notes |
|--------|-------------|-----------|-------|
| Azure OpenAI GPT-4o-mini | Microsoft Healthcare BAA | Lowest | Default selection |
| AWS Bedrock Claude claude-sonnet-4-6 | AWS BAA (if already in place for Textract) | Low | Good option if AWS BAA exists |
| Google Vertex AI Gemini Flash | Google Cloud Healthcare BAA | Low | Good option if on GCP |
| Anthropic API Claude claude-sonnet-4-6 direct | Anthropic BAA (separate process) | Medium | Original spec choice |
| Self-hosted Llama 3.1 70B | None needed | Zero per-token cost | More infrastructure overhead |

**PHI handling for all LLM options — non-negotiable regardless of provider:**
- Strip all direct identifiers before the API call: no patient names, DOBs, or addresses in the prompt
- The LLM sees: CPT codes, ICD-10 codes, OMOP concept IDs, anonymized clinical note excerpts (max 200 chars), and the CPT documentation requirement standard
- The LLM does not see: client name, client DOB, provider name (replaced with "Provider A"), or any field that could identify the patient
- All LLM output passes through the prohibited string filter before being written to the database
- Prompt template is fixed and reviewed by the Privacy Officer before deployment — not dynamically constructed from user input

**Frontend: React 18 with TypeScript**

Reason: The split-panel QA interface (PRD Section 5.6.1a) requires real-time state synchronization between the chronology list and the document viewer panel. React's component model handles this cleanly. TypeScript reduces runtime errors in a PHI-handling application where data model errors have compliance implications. Do not substitute Vue, Svelte, or vanilla JavaScript.

**PDF Viewer for Document Panel: PDF.js (Mozilla)**

Reason: PDF.js renders PDFs directly in the browser without sending documents to an external service. It supports page-level navigation, zoom, and annotation. It runs entirely client-side from a CDN — the actual document bytes are fetched from time-limited pre-signed/SAS URLs directly to the browser from your object storage provider. No document content passes through the application server. This is the correct HIPAA data flow for document display regardless of which cloud object storage you use.

**Authentication: Auth0 with MFA enforcement**

Reason: HIPAA technical safeguard requirement — unique user IDs and MFA for all portal access. Auth0 provides MFA enforcement, session management, and audit logging. All portal routes require a valid Auth0 session token. Do not implement custom authentication.

**Infrastructure: Match your existing repo hosting [IMPLEMENTATION CHOICE]**

Requirement: SOC 2 Type II certified data centres, geographic redundancy across two regions (satisfies PRD Section 6.3 RTO under 4 hours, RPO under 1 hour), and all services covered under your organisation's existing cloud BAA. Use whichever cloud your existing repos are already hosted on to avoid introducing a new cloud provider and a new BAA.

If your existing repos span multiple clouds, host TRACE on the same cloud as your billing and financial management repo — the billing reconciliation integration (see below) requires low-latency service calls between TRACE and the billing repo, which is easier within the same cloud.

**Audit Logging: pgaudit extension on PostgreSQL + cloud-native log aggregation [IMPLEMENTATION CHOICE — match your cloud]**

Reason: Every PHI access must be logged with user ID, timestamp, action, and data accessed (PRD Section 7.1 technical safeguards). pgaudit captures all database-level reads and writes. Application-level API request logging goes to your existing log aggregation service:

| Cloud | Log aggregation service |
|-------|------------------------|
| AWS | CloudWatch Logs |
| Google Cloud | Cloud Logging |
| Azure | Azure Monitor / Log Analytics |
| Self-hosted | Elasticsearch + Kibana or Grafana Loki |

Non-negotiable regardless of service: logs retained for 6 years minimum (HIPAA requirement), logs are immutable (no application process has write or delete access to the log store), and logs do not contain PHI (client names, DOBs, or addresses must not appear in log entries — reference case_id and firm_id only).

### 2.2 What Not to Use [DECISION LOCKED]

These are explicitly prohibited for TRACE Phase 1:

- **No local LLM (Ollama, LMStudio, local Llama3, DeepSeek self-hosted)** — PHI cannot be processed on unmanaged local hardware
- **No DeepSeek API (any version)** — no HIPAA BAA available, China-based infrastructure creates data residency risk incompatible with HIPAA. Do not use until a BAA is published and approved by the Privacy Officer in writing
- **No LLM API from any provider without a signed HIPAA BAA** — this rule supersedes any cost or performance argument. BAA first, then evaluate
- **No Docker deployment to attorney machines** — TRACE is cloud-hosted SaaS only
- **No Streamlit** — not appropriate for a production HIPAA-compliant multi-tenant SaaS application
- **No Docspell** — replaced by cloud-native OCR (Textract or equivalent)
- **No Orthanc / DICOM handling** — not in Phase 1 scope (added in Phase 4)
- **No OHIF Viewer** — not in Phase 1 scope
- **No flat file storage of case data** — all case data in PostgreSQL
- **No Metriport HIE integration** — Phase 3 enhancement, not Phase 1 dependency
- **No localStorage or IndexedDB in the browser** — PHI must not persist on client devices
- **No regex-only billing code extraction** — use billing repo integration (Section 5.6) as primary; regex pattern matching only as temporary fallback explicitly marked as such in code
- **No rebuilding billing extraction inside TRACE** — the existing billing repo owns CPT/ICD-10 data. Integrate with it, do not duplicate it

---

## Part 3 — Database Schema

### 3.1 Core Tables

Build these tables in this exact order. Foreign key constraints must be enforced at the database level.

```sql
-- PHI Store (separate encrypted database instance)
CREATE TABLE clients (
    client_token        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    encrypted_name      BYTEA NOT NULL,        -- pgcrypto AES-256
    encrypted_dob       BYTEA NOT NULL,        -- pgcrypto AES-256
    encrypted_address   BYTEA NOT NULL,        -- pgcrypto AES-256
    encrypted_phone     BYTEA NOT NULL,        -- pgcrypto AES-256
    firm_id             UUID NOT NULL,         -- which attorney firm owns this record
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Operational Database (main TRACE database — no direct PII)
CREATE TABLE cases (
    case_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_token        UUID NOT NULL,         -- reference to PHI store only
    firm_id             UUID NOT NULL,
    intake_record_id    UUID NOT NULL,         -- Benjamin intake record reference
    incident_date       DATE NOT NULL,
    jurisdiction_state  CHAR(2) NOT NULL,
    sol_deadline        DATE,                  -- calculated, null until initialized
    sol_urgency         VARCHAR(10),           -- Standard/Monitor/Urgent/Critical
    hipaa_auth_status   VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    provider_list_status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    case_stage          VARCHAR(30) NOT NULL DEFAULT 'INITIALIZATION',
    approval_attorney_id UUID,
    approval_timestamp  TIMESTAMPTZ,
    approval_text       TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_hipaa_status CHECK (hipaa_auth_status IN ('PENDING','SIGNED','EXPIRED')),
    CONSTRAINT valid_provider_status CHECK (provider_list_status IN ('DRAFT','CONFIRMED','LOCKED')),
    CONSTRAINT valid_stage CHECK (case_stage IN (
        'INITIALIZATION','RETRIEVAL','PROCESSING',
        'CHRONOLOGY_READY','ATTORNEY_REVIEW','DEMAND_READY'
    ))
);

CREATE TABLE providers (
    provider_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id             UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    npi_number          VARCHAR(10),
    provider_name       VARCHAR(255) NOT NULL,
    facility_name       VARCHAR(255),
    fax_number          VARCHAR(20),
    address             TEXT,
    specialty           VARCHAR(100),
    dates_of_service    DATERANGE,
    confirmation_status VARCHAR(20) NOT NULL DEFAULT 'UNCONFIRMED',
    confirmed_at        TIMESTAMPTZ,
    confirmed_by        UUID,                  -- attorney user ID
    retrieval_status    VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    last_request_sent   TIMESTAMPTZ,
    follow_up_count     INTEGER DEFAULT 0,
    CONSTRAINT valid_confirmation CHECK (confirmation_status IN ('UNCONFIRMED','CONFIRMED','REMOVED')),
    CONSTRAINT valid_retrieval CHECK (retrieval_status IN ('PENDING','REQUESTED','PARTIAL','COMPLETE','UNRESPONSIVE'))
);

CREATE TABLE documents (
    document_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id             UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    provider_id         UUID REFERENCES providers(provider_id),
    s3_bucket           VARCHAR(255) NOT NULL,
    s3_key              VARCHAR(1024) NOT NULL,
    document_type       VARCHAR(50),           -- ER/IMAGING/PT/BILLING/PHARMACY/OTHER
    page_count          INTEGER,
    received_at         TIMESTAMPTZ DEFAULT NOW(),
    ocr_status          VARCHAR(20) DEFAULT 'PENDING',
    ocr_confidence      DECIMAL(5,2),
    is_duplicate        BOOLEAN DEFAULT FALSE,
    is_misfiled         BOOLEAN DEFAULT FALSE
);

CREATE TABLE chronology_entries (
    entry_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id             UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    event_date          TIMESTAMPTZ NOT NULL,
    provider_id         UUID REFERENCES providers(provider_id),
    facility_name       VARCHAR(255),
    event_type          VARCHAR(30) NOT NULL,  -- VISIT/IMAGING/PRESCRIPTION/PROCEDURE/DISCHARGE/REFERRAL
    clinical_description TEXT NOT NULL,        -- verbatim from source record
    source_document_id  UUID NOT NULL REFERENCES documents(document_id),
    source_page_number  INTEGER NOT NULL,
    flag_node_id        UUID,                  -- populated if this entry has a flag
    attorney_annotation TEXT,
    verify_flag         BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_event_type CHECK (event_type IN (
        'VISIT','IMAGING','PRESCRIPTION','PROCEDURE','DISCHARGE','REFERRAL'
    ))
);

CREATE TABLE event_nodes (
    node_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id             UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    flag_type           VARCHAR(30) NOT NULL,
    flag_date_start     DATE,
    flag_date_end       DATE,
    gap_duration_days   INTEGER,
    system_description  TEXT NOT NULL,         -- factual only — passes prohibited string filter
    cpt_code            VARCHAR(10),
    cpt_description     TEXT,
    cpt_documentation_requirement TEXT,
    clinical_note_summary TEXT,
    source_doc_id_before UUID REFERENCES documents(document_id),
    source_page_before  INTEGER,
    source_doc_id_after UUID REFERENCES documents(document_id),
    source_page_after   INTEGER,
    attorney_annotation VARCHAR(50),           -- enum see below
    annotation_text     TEXT,
    annotation_at       TIMESTAMPTZ,
    annotation_by       UUID,
    resolved_at         TIMESTAMPTZ,
    CONSTRAINT valid_flag_type CHECK (flag_type IN ('TREATMENT_GAP','BILLING_DISCREPANCY','ESCALATION_FLAG')),
    CONSTRAINT valid_annotation CHECK (attorney_annotation IN (
        'CONFIRMED_EXPLAINED','CONFIRMED_NEEDS_FOLLOWUP','DISMISSED','RESOLVED', NULL
    ))
);

-- Add foreign key from chronology to event nodes after both tables exist
ALTER TABLE chronology_entries 
    ADD CONSTRAINT fk_flag_node 
    FOREIGN KEY (flag_node_id) REFERENCES event_nodes(node_id);

CREATE TABLE audit_log (
    log_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id            UUID NOT NULL,
    actor_type          VARCHAR(20) NOT NULL,  -- ATTORNEY/SYSTEM/SUPPORT
    action              VARCHAR(100) NOT NULL,
    resource_type       VARCHAR(50) NOT NULL,
    resource_id         UUID,
    case_id             UUID,
    firm_id             UUID,
    ip_address          INET,
    user_agent          TEXT,
    timestamp           TIMESTAMPTZ DEFAULT NOW(),
    details             JSONB
);
-- Audit log is append-only: no UPDATE or DELETE permissions for any application role
```

### 3.2 Database Roles and Permissions

Create three database roles. Grant minimum necessary permissions to each.

```sql
-- Application role: read/write to operational tables only
CREATE ROLE trace_app_role;
GRANT SELECT, INSERT, UPDATE ON cases, providers, documents, 
      chronology_entries, event_nodes TO trace_app_role;
GRANT INSERT ON audit_log TO trace_app_role;  -- INSERT only, no SELECT/UPDATE/DELETE

-- PHI access role: separate from app role, requires explicit elevation
CREATE ROLE trace_phi_role;
GRANT SELECT, INSERT, UPDATE ON clients TO trace_phi_role;
-- Application only elevates to trace_phi_role for PHI reads required by specific
-- attorney-authenticated actions. Never open by default.

-- Read-only role: for reporting and support
CREATE ROLE trace_readonly_role;
GRANT SELECT ON cases, providers, documents, chronology_entries, event_nodes TO trace_readonly_role;
-- No access to audit_log or clients from this role
```

---

## Part 4 — API Specification

### 4.1 Base URL Structure

```
/api/v1/trace/
```

All endpoints require:
- Valid Auth0 JWT in Authorization header
- Firm ID validated against authenticated user's firm membership
- Every request logged to audit_log before response is returned

### 4.2 Case Initialization

```
POST /api/v1/trace/cases
```

**Trigger:** Attorney marks a lead as "Retainer Signed" in the INTAKE portal. This endpoint is called automatically by the INTAKE system — not directly by the attorney.

**Input:**
```json
{
    "intake_record_id": "uuid",
    "firm_id": "uuid",
    "attorney_id": "uuid",
    "client_data": {
        "name": "string",
        "dob": "YYYY-MM-DD",
        "address": "string",
        "phone": "string"
    },
    "incident_date": "YYYY-MM-DD",
    "jurisdiction_state": "CA"
}
```

**What the endpoint does:**
1. Encrypts client_data fields and writes to PHI store, returns client_token
2. Creates case record in operational database with client_token (not raw client data)
3. Calculates SOL deadline from incident_date + jurisdiction_state using SOL lookup table
4. Assigns SOL urgency label
5. Triggers provider extraction job (async — does not block response)
6. Writes to audit_log
7. Returns case_id and SOL information

**Output:**
```json
{
    "case_id": "uuid",
    "sol_deadline": "YYYY-MM-DD",
    "sol_urgency": "Standard|Monitor|Urgent|Critical",
    "sol_disclaimer": "This calculation is based on the standard personal injury statute of limitations for the indicated state and incident date. Tolling provisions, discovery rules, government entity notice requirements, and other state-specific exceptions may apply. The attorney is responsible for confirming the applicable deadline before relying on this calculation for any purpose.",
    "stage": "INITIALIZATION"
}
```

**Validation rules:**
- incident_date must not be in the future
- jurisdiction_state must be a valid 2-letter US state code
- firm_id must match the authenticated user's firm
- Duplicate detection: if an intake_record_id already has a case, return 409 with existing case_id

### 4.3 Provider Confirmation

```
GET  /api/v1/trace/cases/{case_id}/providers       -- list providers for review
PUT  /api/v1/trace/cases/{case_id}/providers/{id}  -- update a provider entry
POST /api/v1/trace/cases/{case_id}/providers       -- add a new provider
DELETE /api/v1/trace/cases/{case_id}/providers/{id} -- remove a provider (sets status REMOVED)
POST /api/v1/trace/cases/{case_id}/providers/confirm  -- lock the list and trigger Step 2
```

**The confirm endpoint is the attorney's Checkpoint 1.** It:
1. Validates that at least one provider has confirmation_status = CONFIRMED
2. Sets all CONFIRMED providers to LOCKED
3. Updates case.provider_list_status to CONFIRMED
4. Timestamps the confirmation with attorney_id
5. Writes to audit_log with full provider list snapshot
6. Does NOT yet transmit any fax — that is a separate attorney action

**Validation rules:**
- Cannot confirm if zero providers are in CONFIRMED status
- Cannot confirm if case is not in INITIALIZATION or RETRIEVAL stage
- Once confirmed, individual providers cannot be edited (only removed via a documented override action)

### 4.4 Record Request Transmission

```
GET  /api/v1/trace/cases/{case_id}/requests        -- preview all pending requests
POST /api/v1/trace/cases/{case_id}/requests/send   -- Checkpoint 2: attorney approves and sends
```

**The send endpoint is the attorney's Checkpoint 2.** It:
1. Checks that provider_list_status = CONFIRMED (returns 403 if not)
2. Generates HIPAA-compliant fax cover sheets for all CONFIRMED providers
3. Presents the attorney with a preview list before sending (GET endpoint above)
4. On POST, submits all faxes to Fax.Plus API
5. Records fax transmission ID, timestamp, and confirmation for each provider
6. Updates provider retrieval_status to REQUESTED
7. Writes to audit_log with complete fax manifest

**Fax request payload to Fax.Plus:**
- To: provider fax number
- Cover sheet: generated PDF containing client token reference (not client name), provider name, record types requested, HIPAA authorization reference number, and return fax number
- Attachment: signed HIPAA authorization PDF (retrieved from secure storage by authorization reference)
- HIPAA mode: enabled (no PHI in Fax.Plus notification emails)

### 4.5 Record Receipt

```
POST /api/v1/trace/webhooks/fax-received  -- Fax.Plus webhook, internal endpoint
POST /api/v1/trace/cases/{case_id}/documents/upload  -- attorney-initiated manual upload
```

**Fax webhook handler:**
1. Validates webhook signature from Fax.Plus
2. Downloads received fax PDF from Fax.Plus
3. Stores in S3 with SSE-KMS encryption
4. Creates document record in database
5. Triggers OCR processing job (async)
6. Writes to audit_log

**Manual upload handler:**
- Accepts PDF only (reject other formats with 415)
- Max file size 100MB per document, 2GB per case total
- Same processing pipeline as fax receipt

### 4.6 Chronology and QA Interface

```
GET  /api/v1/trace/cases/{case_id}/chronology          -- full chronology with flags
GET  /api/v1/trace/cases/{case_id}/chronology/{entry_id} -- single entry with source link
GET  /api/v1/trace/cases/{case_id}/documents/{doc_id}/page/{page} -- pre-signed S3 URL for PDF.js
PATCH /api/v1/trace/cases/{case_id}/event-nodes/{node_id} -- Checkpoint 3: annotate a flag
POST /api/v1/trace/cases/{case_id}/approve             -- Checkpoint 4: demand-ready approval
```

**Chronology GET response shape:**
```json
{
    "case_id": "uuid",
    "sol_deadline": "YYYY-MM-DD",
    "sol_urgency": "string",
    "total_entries": 47,
    "total_flags": 6,
    "annotated_flags": 4,
    "unannotated_priority_flags": 2,
    "demand_ready_blocked": true,
    "entries": [
        {
            "entry_id": "uuid",
            "event_date": "2026-01-15T09:12:00Z",
            "provider": "string",
            "facility": "string",
            "event_type": "VISIT",
            "clinical_description": "verbatim text from record",
            "source_document_id": "uuid",
            "source_page_number": 12,
            "flag_node_id": "uuid or null",
            "flag_type": "TREATMENT_GAP or null",
            "flag_annotated": true,
            "attorney_annotation": "string or null",
            "verify_flag": false
        }
    ]
}
```

**Document page endpoint:**
- Returns a pre-signed S3 URL valid for 15 minutes
- PDF.js in the browser fetches the document directly from S3 using this URL
- Application server never buffers document bytes in memory
- URL expiry prevents stale access to PHI

**Flag annotation PATCH:**
```json
{
    "attorney_annotation": "CONFIRMED_EXPLAINED",
    "annotation_text": "Gap explained by patient travel — see attached note"
}
```
- Validates attorney_annotation is one of the four permitted values
- Writes annotation_at and annotation_by automatically from authenticated session
- Cannot un-annotate a flag (can only change the annotation type + text)
- Writes to audit_log

**Demand-ready approval POST:**
1. Checks that unannotated_priority_flags = 0 (returns 400 with count if not)
2. Records approval_attorney_id, approval_timestamp, and standard approval text
3. Updates case_stage to DEMAND_READY
4. Writes to audit_log with full flag annotation summary
5. Any subsequent edit to the chronology resets case_stage to ATTORNEY_REVIEW

### 4.7 Export

```
GET /api/v1/trace/cases/{case_id}/export/pdf   -- formatted chronology PDF
GET /api/v1/trace/cases/{case_id}/export/json  -- structured JSON for CMS import
```

Both exports are only available when case_stage = DEMAND_READY. Returns 403 with message "Chronology must be attorney-approved before export" if stage is not DEMAND_READY.

Every page of the PDF export includes the disclaimer:
*"Generated by TrueVow TRACE. This chronology is a structured organization of medical records retrieved for attorney review. It does not constitute legal advice, medical advice, or a case evaluation. Attorney review and approval is required before use in any legal matter. TrueVow is not a law firm. © TrueVow Technologies."*

---

## Part 5 — Background Processing Jobs

### 5.1 Provider Extraction Job

**Trigger:** Fires asynchronously after case initialization.

**Steps:**
1. Load Benjamin intake record JSON for the case
2. Run spaCy NER (en_core_sci_md) on the intake transcript text
3. Extract named entities of type: ORG (organizations/facilities), PERSON (physician names), GPE (locations)
4. Filter for entities likely to be healthcare providers based on context window
5. For each extracted provider:
   a. Query CMS NPI Registry API: `https://npiregistry.cms.hhs.gov/api/?version=2.1&name={provider_name}&state={jurisdiction}`
   b. If single confident match: create provider record with UNCONFIRMED status, pre-fill all fields from NPI response
   c. If multiple matches: create provider record with UNCONFIRMED status, flag as "Multiple matches — attorney selection required"
   d. If no match: create provider record with UNCONFIRMED status, flag as "Not found in NPI Registry — attorney entry required"
6. Update case_stage to RETRIEVAL
7. Notify attorney via portal notification and SMS/email alert: "Provider list ready for your review — {n} providers identified"

**Confidence scoring:**
- HIGH: explicit facility name or physician full name + specialty match in NPI Registry
- MEDIUM: partial name match or location-only reference
- LOW: implied provider ("the hospital", "my doctor") with no identifying information
- LOW-confidence providers are shown with a warning label in the provider confirmation checklist

### 5.2 OCR Processing Job

**Trigger:** Fires asynchronously when a document record is created (fax received or manual upload).

**Steps:**
1. Retrieve document from S3 using document.s3_key
2. Submit to AWS Textract: `DetectDocumentText` for single-page, `StartDocumentTextDetection` for multi-page async
3. Receive Textract response (polling or SNS callback)
4. Evaluate per-page confidence scores
   - Pages with mean confidence below 80%: flag as LOW_CONFIDENCE, mark for attorney manual review
   - Pages with mean confidence 80–95%: flag as MEDIUM_CONFIDENCE, include in processing but note in index
   - Pages with mean confidence above 95%: flag as HIGH_CONFIDENCE, proceed to extraction
5. Store raw Textract output in S3 alongside original document
6. Update document.ocr_status and document.ocr_confidence
7. If document.ocr_status = COMPLETE: trigger clinical event extraction job

### 5.3 Clinical Event Extraction Job

**Trigger:** Fires after OCR is complete for a document.

**Steps:**
1. Load raw OCR text from S3
2. Run spaCy pipeline:
   - Named entity recognition: dates, provider names, procedures, diagnoses, medications
   - Sentence segmentation for context window construction
3. For each candidate clinical event (date + clinical action detected):
   a. Extract: event_date (normalized to ISO 8601), provider, facility, event_type (classified), clinical_description (verbatim sentence from source)
   b. Record source_document_id and source_page_number
   c. Apply deduplication: if same event_date + provider + event_type already exists in chronology for this case from a different document, flag as potential duplicate for attorney review
4. Write to chronology_entries table
5. When all documents for a case are processed: trigger gap detection and billing reconciliation jobs

### 5.4 SOL Calculation

**Triggered synchronously** during case initialization. Not a background job.

```python
SOL_TABLE = {
    "AL": 2, "AK": 2, "AZ": 2, "AR": 3, "CA": 2, "CO": 3,
    "CT": 2, "DE": 2, "FL": 4, "GA": 2, "HI": 2, "ID": 2,
    "IL": 2, "IN": 2, "IA": 2, "KS": 2, "KY": 1, "LA": 1,
    "ME": 6, "MD": 3, "MA": 3, "MI": 3, "MN": 2, "MS": 3,
    "MO": 5, "MT": 3, "NE": 4, "NV": 2, "NH": 3, "NJ": 2,
    "NM": 3, "NY": 3, "NC": 3, "ND": 6, "OH": 2, "OK": 2,
    "OR": 2, "PA": 2, "RI": 3, "SC": 3, "SD": 3, "TN": 1,
    "TX": 2, "UT": 4, "VT": 3, "VA": 2, "WA": 3, "WV": 2,
    "WI": 3, "WY": 4, "DC": 3
}

def calculate_sol(incident_date: date, state: str) -> dict:
    years = SOL_TABLE.get(state.upper())
    if not years:
        return {"error": "State not found in SOL table"}
    
    sol_deadline = incident_date.replace(year=incident_date.year + years)
    days_remaining = (sol_deadline - date.today()).days
    
    if days_remaining > 180:
        urgency = "Standard"
    elif days_remaining > 90:
        urgency = "Monitor"
    elif days_remaining > 30:
        urgency = "Urgent"
    else:
        urgency = "Critical"
    
    return {
        "sol_deadline": sol_deadline.isoformat(),
        "days_remaining": days_remaining,
        "urgency": urgency,
        "disclaimer": "This calculation is based on the standard personal injury statute of limitations for the indicated state and incident date. Tolling provisions, discovery rules, government entity notice requirements, and other state-specific exceptions may apply. The attorney is responsible for confirming the applicable deadline before relying on this calculation for any purpose."
    }
```

**Important:** This table represents standard discovery-rule PI statutes only. It does not account for: government entity notice requirements (varies by state, often 6 months), tolling for minors, tolling for disability, tolling for discovery of injury (latent injury cases), or cases against government entities. The disclaimer is mandatory on every display of SOL output.

**Maintenance requirement:** This table must be reviewed by a licensed attorney in each target state before Phase 3 launch and updated whenever a state legislature amends its statute. Track the table version in the database and display the version date alongside the SOL output.

### 5.5 Gap Detection Job

**Steps:**
1. Load all chronology_entries for the case, ordered by event_date
2. Group entries by date (a day with any entry is a treatment day)
3. Find date ranges with no treatment days, duration ≥ 14 days (configurable per case)
4. For each gap:
   a. Identify: gap_date_start, gap_date_end, gap_duration_days
   b. Find: last chronology entry before the gap (source_doc_id_before, source_page_before)
   c. Find: first chronology entry after the gap (source_doc_id_after, source_page_after)
   d. Write Event Node with flag_type = TREATMENT_GAP
   e. system_description: "No treatment records found from [date] to [date] — {n} days. Last recorded treatment: [event_type] at [facility] on [date]. Next recorded treatment: [event_type] at [facility] on [date]."
   f. No interpretation of why the gap occurred

### 5.6 Billing Reconciliation Job

**Architecture decision: integrate with the existing billing repo rather than rebuilding billing extraction inside TRACE.**

Your existing financial management and billing repo already handles billing records, invoices, and CPT/ICD-10 data. TRACE does not re-implement billing data extraction — it calls the billing repo's service API to retrieve structured billing records for the case, then cross-references them against the clinical chronology TRACE has built. This eliminates duplication, keeps billing logic in the system that owns it, and makes the integration the reconciliation point rather than the extraction point.

**Prerequisites before this job can be built:**

The billing repo must expose an API endpoint that returns structured billing records for a given case. Confirm the following with the billing repo team before starting this job:

1. What is the case identifier in the billing repo? (Is it the TRACE case_id, the intake_record_id, or a separate billing case reference? The mapping must be established.)
2. What fields does the billing record include? Minimum required: date of service, provider identifier, CPT code, ICD-10 code, billed amount.
3. Is the billing repo within your HIPAA compliance boundary? (It handles billing PHI — it should be. Confirm before making service calls that include client tokens.)
4. What authentication does the billing repo API use? (Should use the same Auth0 JWT or a service-to-service token.)

**Integration steps:**

```python
async def run_billing_reconciliation(case_id: UUID, client_token: UUID):
    
    # Step 1: Retrieve structured billing records from billing repo
    billing_records = await billing_service.get_billing_records_for_case(
        case_reference=case_id,
        client_token=client_token
    )
    # Returns list of: {date_of_service, provider_id, cpt_code, icd10_code, billed_amount}
    # If billing repo uses a different case identifier, the mapping is handled 
    # inside billing_service.get_billing_records_for_case()
    
    # Step 2: Load clinical chronology for the case
    chronology_entries = await db.get_chronology_entries(case_id=case_id)
    # Groups entries by date and provider for comparison
    
    # Step 3: For each billing record with a CPT code
    for bill in billing_records:
        if not bill.cpt_code:
            continue
        
        # Step 4: Look up CPT documentation requirements from internal reference table
        cpt_requirements = CPT_DOCUMENTATION_TABLE.get(bill.cpt_code)
        if not cpt_requirements:
            continue  # Unknown CPT code — skip, do not flag
        
        # Step 5: Find matching chronology entry (same date, same provider)
        matching_entries = [
            e for e in chronology_entries
            if e.event_date.date() == bill.date_of_service
            and e.provider_id == bill.provider_id
        ]
        
        # Step 6: Compare
        if not matching_entries:
            # Bill exists with no corresponding clinical record on same date
            description = (
                f"Bill dated {bill.date_of_service} from provider "
                f"shows CPT {bill.cpt_code} ({cpt_requirements['description']}). "
                f"No clinical record found for same date and provider. "
                f"Factual discrepancy surfaced for attorney review."
            )
        else:
            # Check if clinical note content supports CPT requirements
            note_text = matching_entries[0].clinical_description.lower()
            if cpt_requirements.get('min_time_minutes'):
                # Check for time documentation in note
                if not has_time_documentation(note_text, cpt_requirements['min_time_minutes']):
                    description = (
                        f"Bill dated {bill.date_of_service} shows CPT {bill.cpt_code} "
                        f"({cpt_requirements['description']} — requires "
                        f"{cpt_requirements['min_time_minutes']} minutes documented). "
                        f"Clinical note excerpt: '{matching_entries[0].clinical_description[:100]}'. "
                        f"Factual discrepancy surfaced for attorney review."
                    )
                else:
                    continue  # No discrepancy detected
            else:
                continue  # CPT does not have time documentation requirement — skip
        
        # Step 7: Filter and write Event Node
        filtered_description = filter_prohibited(description)  # raises ValueError if prohibited term
        await db.create_event_node(
            case_id=case_id,
            flag_type='BILLING_DISCREPANCY',
            flag_date=bill.date_of_service,
            system_description=filtered_description,
            cpt_code=bill.cpt_code,
            cpt_description=cpt_requirements['description'],
            cpt_documentation_requirement=cpt_requirements.get('documentation_standard'),
            clinical_note_summary=matching_entries[0].clinical_description[:100] if matching_entries else None,
            source_doc_id_before=matching_entries[0].source_document_id if matching_entries else None,
            source_page_before=matching_entries[0].source_page_number if matching_entries else None
        )
```

**If the billing repo is not yet ready to expose a case-level API:** build a temporary fallback that extracts CPT and ICD-10 codes from billing documents that arrive via fax (document_type = BILLING) using spaCy pattern matching. This fallback is used only until the billing repo integration is complete. Flag it clearly in code with a TODO and the billing repo ticket reference.

**LLM use in billing reconciliation:**

The structured comparison above handles most cases without an LLM. Use the LLM (Azure OpenAI GPT-4o-mini) only for cases where the CPT documentation requirement cannot be evaluated by simple time-documentation pattern matching — specifically, for evaluation and management codes (99202–99215) where the medical decision-making complexity level is the relevant criterion rather than documented time.

LLM prompt for complexity evaluation (PHI-stripped):

```python
BILLING_AUDIT_PROMPT = """
You are evaluating whether a medical billing code is supported by clinical documentation.
Do not use the words: malpractice, fraud, upcoding, negligence, liability, or causation.
Only describe what the documentation contains versus what the code requires.

CPT Code: {cpt_code}
CPT Description: {cpt_description}
Medical Decision Making Requirement for this code: {mdm_requirement}

Clinical note excerpt (anonymised):
{clinical_note_excerpt}

Does the clinical note contain documentation consistent with the medical decision making 
requirement for this CPT code? Answer only:
- SUPPORTED: note contains elements consistent with the requirement
- NOT_SUPPORTED: note does not contain elements consistent with the requirement  
- INSUFFICIENT_INFORMATION: note excerpt is too brief to evaluate

Then in one factual sentence, describe what the note contains versus what the code requires.
Do not speculate about intent. Do not use evaluative language about the provider.
"""
```

Output from this prompt passes through `filter_prohibited()` before writing to the database.

**Prohibited string filter:**
```python
PROHIBITED_STRINGS = [
    "malpractice", "upcoding", "fraud", "abuse", "intentional",
    "strong case", "weak case", "liability", "causation",
    "negligence", "below standard", "standard of care",
    "will settle", "settlement value", "case value",
    "predict", "guarantee", "likely outcome"
]

def filter_prohibited(text: str) -> str:
    """
    Run before writing any system-generated text to the database.
    Raises ValueError if prohibited string detected.
    Engineering note: do not silently replace — raise and log.
    If this filter fires during testing, the prompt or extraction
    logic is wrong and must be fixed before deployment.
    """
    text_lower = text.lower()
    for term in PROHIBITED_STRINGS:
        if term in text_lower:
            raise ValueError(
                f"Prohibited string '{term}' detected in system output. "
                f"Output blocked. Review extraction logic."
            )
    return text
```

---

## Part 6 — Frontend Implementation

### 6.1 Portal Integration Points

TRACE does not have a standalone URL. It is embedded in the existing TrueVow attorney portal as a new section that appears when cases exist. The navigation structure:

```
Portal nav:
├── Dashboard (existing INTAKE dashboard)
├── Intake Records (existing INTAKE records list)
├── TRACE Cases (new — visible only to PIPELINE and OPERATIONS subscribers)
│   ├── Case List
│   └── Case Detail → [Provider Review] → [Record Status] → [Chronology QA]
└── Settings
```

### 6.2 Case Detail View — State Machine

The case detail view renders differently based on case_stage. Build it as a state machine — not a single component with conditional rendering of everything.

```
INITIALIZATION → show: SOL info, "Provider list being prepared" loading state
RETRIEVAL      → show: SOL info, Provider confirmation checklist, Confirm button
                 (Checkpoint 1 lives here)
               → after confirm: show record request preview, Send Requests button
                 (Checkpoint 2 lives here)
PROCESSING     → show: SOL info, Provider retrieval status per provider, processing indicator
CHRONOLOGY_READY → show: SOL info, "Chronology ready for your review" alert, Review button
ATTORNEY_REVIEW  → show: Split-panel QA interface (Checkpoint 3 lives here)
                   Demand-Ready button locked until priority flags = 0
                 → Checkpoint 4: Demand-Ready approval action
DEMAND_READY     → show: Approval confirmation, export buttons (PDF + JSON)
```

### 6.3 Split-Panel QA Interface

```
┌────────────────────────────────────────────────────────────────┐
│ SOL: [deadline] — [urgency] — [disclaimer link]                │
│ Flags: 6 total | 4 annotated | 2 priority unannotated          │
│ [Mark Demand-Ready ▶] ← LOCKED (greyed) until 0 unannotated   │
├────────────────────────┬───────────────────────────────────────┤
│ CHRONOLOGY             │ SOURCE DOCUMENT                       │
│                        │                                       │
│ Filter: [Provider ▾]   │ [Document name] Page 12 of 47        │
│         [Type ▾]       │ [Zoom -] [100%] [Zoom +]             │
│         [Flags only ▾] │                                       │
│                        │ ┌─────────────────────────────────┐  │
│ 2026-01-15 09:12       │ │                                 │  │
│ ER Visit — Cedars      │ │  [PDF.js renders document here] │  │
│ "Acute back injury      │ │                                 │  │
│  following MVA"        │ │                                 │  │
│ [View source ▶]        │ │                                 │  │
│                        │ └─────────────────────────────────┘  │
│ ⚠ 2026-01-15 — 03-01  │                                       │
│ TREATMENT GAP: 45 days │                                       │
│ Annotation required:   │                                       │
│ ○ Confirmed+Explained  │                                       │
│ ○ Needs Follow-up      │                                       │
│ ○ Dismissed            │                                       │
│ ○ Resolved             │                                       │
│ [text field if         │                                       │
│  Confirmed+Explained]  │                                       │
│ [Save Annotation]      │                                       │
├────────────────────────┴───────────────────────────────────────┤
```

**Clicking "View source ▶" on a chronology entry:**
1. Front end calls `GET /api/v1/trace/cases/{case_id}/documents/{doc_id}/page/{page}`
2. Receives pre-signed S3 URL (15-min expiry)
3. PDF.js loads the document from S3 directly
4. Panel scrolls to the correct page automatically
5. No application server bytes involved in document display

### 6.4 SOL Display Component

Render on every case view, every stage. Cannot be dismissed or hidden.

```
┌─────────────────────────────────────────────────────────────┐
│ ⚠ STATUTE OF LIMITATIONS                                     │
│ Calculated deadline: March 15, 2028 — 612 days remaining    │
│ Status: STANDARD                                             │
│ Disclaimer: This calculation uses the standard PI SOL for    │
│ California. Tolling, government entity requirements, and    │
│ discovery rules may apply. Attorney confirms applicable date.│
└─────────────────────────────────────────────────────────────┘
```

Color coding by urgency:
- Standard: neutral grey border
- Monitor: blue border
- Urgent: amber border + amber background
- Critical: red border + red background + pulsing indicator

---

## Part 7 — Build Sequence and Milestones

Build in this exact order. Do not start a phase before the previous one passes its acceptance criteria.

### Phase 1A — Infrastructure and Database (Weeks 1–2)

- [ ] AWS account configured: VPC, security groups, RDS instances (operational + PHI), S3 bucket with SSE-KMS
- [ ] PostgreSQL schemas created: all tables from Section 3.1
- [ ] Database roles and permissions applied: Section 3.2
- [ ] pgaudit extension enabled and logging to CloudWatch confirmed
- [ ] Auth0 tenant configured: MFA enforced, JWT validation working
- [ ] FastAPI skeleton: authentication middleware, audit logging middleware, error handling
- [ ] Fax.Plus API credentials configured: webhook endpoint registered, HIPAA mode confirmed

**Acceptance criteria:** A test request to any authenticated API endpoint is logged in audit_log with correct actor_id, timestamp, and action. An unauthenticated request returns 401. A request from firm A cannot access firm B's data.

### Phase 1B — Case Initialization and SOL (Weeks 2–3)

- [ ] PHI encryption/decryption via pgcrypto confirmed working
- [ ] Case initialization endpoint (Section 4.2) built and tested
- [ ] SOL calculation function (Section 5.4) built with full 50-state table
- [ ] NPI Registry API integration tested against 20 real provider lookups
- [ ] Provider extraction job skeleton (Section 5.1) built — NPI lookup working, spaCy entity extraction pending until Phase 1C
- [ ] Portal: Case list view and case initialization trigger from INTAKE

**Acceptance criteria:** Creating a case from a test intake record produces a case with correct SOL deadline, correct urgency label, and the disclaimer text. PHI is encrypted in the PHI store and not visible in the operational database.

### Phase 1C — Provider Confirmation and Record Request (Weeks 3–5)

- [ ] spaCy en_core_sci_md installed and tested on 10 sample intake transcripts
- [ ] Provider extraction NLP pipeline producing provider candidates from intake text
- [ ] Provider confirmation checklist UI built (all CRUD endpoints + confirm endpoint)
- [ ] Fax request generation (HIPAA cover sheet PDF creation) working
- [ ] Fax transmission via Fax.Plus API working with delivery confirmation webhook
- [ ] Portal: Provider review interface with confirm flow and request preview

**Acceptance criteria:** End-to-end test with a synthetic case: intake record → provider extraction → attorney confirms list → fax request generated → fax transmitted → webhook confirms delivery. All steps logged in audit_log.

### Phase 1D — Record Processing and Chronology (Weeks 5–8)

- [ ] Fax receive webhook processing working (document stored in S3, document record created)
- [ ] Manual upload endpoint working
- [ ] AWS Textract integration: async processing with SNS callback, confidence scoring, page flagging
- [ ] Clinical event extraction job (Section 5.3) producing chronology entries with source citations
- [ ] Gap detection job (Section 5.5) producing event nodes
- [ ] Billing reconciliation job (Section 5.6) with CPT extraction and prohibited string filter
- [ ] Prohibited string filter tested: confirm it blocks the prohibited terms list

**Acceptance criteria:** Process a set of 10 real PI medical record PDFs (de-identified) through the full pipeline. Chronology entries produced with source citations. At least one treatment gap and one billing discrepancy detected and flagged. All system_description values pass the prohibited string filter without triggering.

### Phase 1E — QA Interface and Approval (Weeks 8–10)

- [ ] Split-panel QA interface built (Section 6.3)
- [ ] PDF.js integration with pre-signed S3 URL flow working
- [ ] Click-to-source navigation working: selecting chronology entry loads source page in right panel
- [ ] Flag annotation inline UI built and connected to PATCH endpoint
- [ ] Demand-ready status bar showing live counts
- [ ] Demand-ready approval gate: locked until 0 unannotated priority flags confirmed working
- [ ] PDF export with disclaimer on every page
- [ ] JSON export in CMS-compatible format

**Acceptance criteria:** Full end-to-end attorney QA test: open a completed chronology, annotate all flags, confirm demand-ready status unlocks, approve, export PDF. Verify disclaimer appears on every exported page. Verify approval is recorded in audit_log.

### Phase 1F — Early Access Preparation (Weeks 10–12)

- [ ] SOC 2 Type II audit scope confirmed to include TRACE data systems
- [ ] HIPAA Security Risk Assessment updated to include TRACE
- [ ] BAA addendum template finalised with healthcare attorney
- [ ] Attorney responsibility addendum finalised
- [ ] TRACE onboarding flow built: BAA signing, HIPAA auth template configuration, test call
- [ ] Support escalation workflow documented and tools provisioned
- [ ] Penetration test scheduled and completed
- [ ] All acceptance criteria from Phases 1A–1E passing on production infrastructure (not local)

**Acceptance criteria:** First early access firm can complete the full TRACE workflow on production infrastructure with support contact present. Audit log complete. No PHI visible in logs, URLs, or notification content.

---

## Part 8 — Testing Requirements

### 8.1 Required Test Coverage

Every endpoint and background job must have:
- Unit tests for happy path
- Unit tests for each validation failure case
- Integration test against real (sandboxed) external services where applicable

### 8.2 PHI Handling Tests

These tests must pass before any real PHI is processed:

- **Audit log completeness:** Assert that every API endpoint call produces an audit_log entry with non-null actor_id, timestamp, resource_type, and resource_id
- **PHI isolation:** Assert that a request authenticated as firm A cannot retrieve any data for firm B's cases
- **No PHI in URLs:** Assert that no API endpoint URL or redirect URL contains client name, DOB, or case reference that includes PII
- **No PHI in logs:** Assert that CloudWatch log streams contain no plaintext client names or DOBs
- **Encryption at rest:** Assert that a direct SELECT on the clients table returns encrypted bytea, not plaintext
- **S3 URL expiry:** Assert that a pre-signed document URL returns 403 after 15 minutes

### 8.3 Checkpoint Gate Tests

- **Checkpoint 1 gate:** Assert that calling the fax send endpoint before provider list is confirmed returns 403
- **Checkpoint 2 gate:** Assert that the fax send endpoint requires the provider list confirm timestamp before transmitting
- **Checkpoint 3:** Assert that PATCH to an event node with an invalid attorney_annotation value returns 400
- **Checkpoint 4 gate:** Assert that the demand-ready approval endpoint returns 400 when unannotated_priority_flags > 0
- **Prohibited string filter:** Assert that each prohibited string in the PROHIBITED_STRINGS list triggers a ValueError when passed to filter_prohibited()

### 8.4 SOL Accuracy Tests

- Test all 50 states + DC produce a deadline date from a known incident date
- Test urgency label transitions at the correct day boundaries (180, 90, 30 days)
- Test that incident_date in the future returns a validation error
- Test that an invalid state code returns a clear error message

---

## Part 9 — Security Checklist Before Early Access Launch

Run this checklist against production infrastructure. All items must pass.

- [ ] All object storage buckets/containers: public access blocked, policy denies public reads, encryption at rest with customer-managed keys confirmed
- [ ] All database instances: not publicly accessible, in private subnet, encrypted at rest
- [ ] All application secrets: stored in your cloud's secrets management service (AWS Secrets Manager / GCP Secret Manager / Azure Key Vault), not in environment variables or code
- [ ] All API endpoints: require valid Auth0 JWT, return 401 without one
- [ ] MFA: enforced for all attorney portal accounts, cannot be disabled per-user
- [ ] Audit log: application role cannot SELECT, UPDATE, or DELETE audit_log — INSERT only
- [ ] PHI store: only accessible via trace_phi_role, not trace_app_role by default
- [ ] Pre-signed URLs: expiry set to 15 minutes, no wildcard permissions
- [ ] Prohibited string filter: unit tests passing, integrated into all LLM output pipelines
- [ ] Demand-ready gate: confirmed blocking with unannotated priority flags in place
- [ ] Provider list confirmation gate: confirmed blocking fax transmission before confirmation
- [ ] No client PII in any URL, log entry, notification subject line, or email body
- [ ] Penetration test: completed by qualified external firm, critical findings remediated
- [ ] HIPAA Security Risk Assessment: completed, all High residual risk items remediated
- [ ] BAA: executed with AWS, Fax.Plus, and Auth0

---

*Document version 1.0 — July 2026. Updates to this specification require product owner approval and must be reflected in the TRACE PRD before implementation. Any deviation from the technology stack decisions in Section 2 requires written approval from the Privacy Officer.*
