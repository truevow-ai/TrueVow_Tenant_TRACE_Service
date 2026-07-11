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

## Part 0 — Agent Discretion: Choices Neither Document Addresses

The PRD and this spec govern all product, compliance, and architecture decisions. For the engineering infrastructure choices below — where neither document specifies a preference and the choice does not affect HIPAA compliance, attorney-facing behavior, or data model integrity — the agent has full discretion. Make the choice that best fits the existing TrueVow repo conventions. If TrueVow conventions are not yet established for a category, use the defaults listed here.

**Database migration tool**

Use **Alembic** (Python, integrates natively with SQLAlchemy/asyncpg). Migrations live in `/migrations/versions/`. Every schema change in Section 3.1 is a separate numbered migration file. Never edit a migration after it has been applied to any environment. The Phase 1A acceptance criterion requires all Section 3.1 tables and roles to be created via Alembic migrations — not raw SQL run manually.

**Test framework**

Use **pytest** with **pytest-asyncio** for async FastAPI endpoint tests. Use **httpx.AsyncClient** as the test HTTP client (pairs cleanly with FastAPI's `app` object without running a live server). Factories for test data via **factory_boy**. Minimum coverage target: 80% on all files under `/app/api/` and `/app/jobs/`. Coverage report generated on every CI run and failing below 80% blocks merge.

**Repo layout**

```
/trace
  /app
    /api          # FastAPI routers — one file per resource (cases, providers, documents, etc.)
    /jobs         # Background processing jobs (provider_extraction, ocr, chronology, gap_detection)
    /models       # SQLAlchemy ORM models matching Section 3.1 schema
    /services     # Business logic (storage_service, fax_service, sol_service, prohibited_filter)
    /middleware   # Auth middleware, audit middleware
    main.py       # FastAPI app instantiation, router registration, middleware registration
  /migrations     # Alembic migration files
  /tests
    /api          # Endpoint tests
    /jobs         # Job unit tests
    /services     # Service unit tests
    /fixtures     # Shared test factories and synthetic PHI-free test data
  fly.toml        # Fly.io deployment configuration
  Dockerfile
  requirements.txt
  .env.example    # Template — never commit a real .env
```

**IaC tool**

Use **Fly.io CLI** (`flyctl`) for application deployment and secrets management. Supabase schema and role setup is handled via Alembic migrations (not Terraform or Supabase Dashboard manual clicks). If TrueVow later adopts Terraform for multi-service IaC, the Fly.io and Supabase resources can be imported — but for Phase 1A, flyctl + Alembic is sufficient and keeps dependencies minimal.

**Local development and emulation**

Supabase provides a local development stack via `supabase start` (Docker-based local Supabase instance including PostgreSQL, Storage, and Auth). Use this for local development so engineers never connect to the production Supabase project during development. Local Supabase runs on `localhost:54321` (API) and `localhost:54323` (Studio UI). Configure a `.env.local` file that points to the local Supabase instance — never to production credentials.

For Fly.io local emulation, use `fly proxy` or run the FastAPI app directly with `uvicorn app.main:app --reload` against the local Supabase instance. No Fly.io-specific local emulator is needed.

For PaddleOCR-VL 1.5 local testing: use a small set of de-identified test PDFs (no real PHI) and run `PaddleOCR().ocr()` locally. All processing is on-device — no external API calls. Confirm that no network calls are made during OCR processing by running with network disabled as part of the air-gap verification in Phase 1D acceptance criteria.

**Anything else not specified**

If you encounter an engineering choice not covered by the PRD, this spec, or the agent discretion categories above — flag it in a comment in the code (`# AGENT CHOICE: [description] — flagged for review`) and proceed with the most conservative option. Do not block progress on undocumented micro-decisions. Flag, proceed, review in the next check-in.

**AuthContext abstraction — consume @truevow/auth-client, never raw Clerk objects**

Clerk is the platform-wide authentication standard across all TrueVow products and domains. TRACE does not implement its own Clerk integration — it consumes the shared `@truevow/auth-client` library (`ClerkWrapper`) that every TrueVow service imports. Do not import `@clerk/nextjs` or `@clerk/backend` directly in TRACE code.

Every TRACE service receives authentication context through a normalized `AuthContext` object populated by the ClerkWrapper. This abstraction exists for three reasons: TRACE services are testable without a live Clerk instance (mock `AuthContext` directly), function intent is readable without knowing Clerk's JWT schema, and any future changes to custom claims are isolated to a single adapter file.

```python
# app/middleware/auth_context.py
from dataclasses import dataclass
from uuid import UUID
from fastapi import HTTPException, Request

@dataclass(frozen=True)
class AuthContext:
    """
    Normalized auth context. Populated from Clerk JWT via @truevow/auth-client.
    All TRACE services consume this — never raw Clerk objects or JWT fields directly.
    """
    user_id: UUID
    firm_id: UUID
    role: str          # "attorney" | "paralegal" | "admin"
    permissions: list[str]

async def get_auth_context(request: Request) -> AuthContext:
    """
    Extracts normalized AuthContext from the validated Clerk JWT.
    The ClerkWrapper (shared-libraries/auth-client) handles JWT verification.
    This function only extracts the claims TRACE cares about.
    """
    clerk_payload = request.state.clerk_payload  # set by ClerkWrapper middleware
    if not clerk_payload:
        raise HTTPException(401, "Missing or invalid session token")

    firm_id_str = clerk_payload.get("org_id") or clerk_payload.get("firm_id")
    if not firm_id_str:
        raise HTTPException(
            403,
            "Your account is not associated with a firm. "
            "Contact support@truevow.law"
        )

    return AuthContext(
        user_id=UUID(clerk_payload["sub"]),
        firm_id=UUID(firm_id_str),
        role=clerk_payload.get("role", "attorney"),
        permissions=clerk_payload.get("permissions", []),
    )
```

**OpenMed version target: 1.8.x**

Pin OpenMed to version 1.8.x. OpenMed 1.8.0 is installed and in production. Do not upgrade to 1.9.x+ without reviewing release notes for breaking changes to the `deid_text()` and `analyze_text()` interfaces.

```
# requirements.txt
openmed>=1.7.0,<1.9.0
```

Note: Phase 1C delivered OpenMed 1.8.0 with regex-based provider extraction (`extraction_source="INTAKE_REGEX"`). The OpenMed transformer NER pipeline (`extraction_source="INTAKE_NER"`) is Phase 1D scope. Regex-extracted candidates must never surface as CONFIRMED — cap at LIKELY_MATCH. See assign_confidence_label() in provider_extraction_service.py.

**Environment variable reference** (additions from ChatGPT review, July 2026):

All environment variables required by TRACE. Set via `fly secrets set` for production. Set in `.env.local` for local development (never commit). The `.env.example` file in the repo root lists all keys with placeholder values and descriptions.

| Variable | Required | Used by | Description |
|----------|----------|---------|-------------|
| `DOCUSEAL_API_URL` | Yes | DocuSeal signing | Base URL of the self-hosted DocuSeal instance (e.g., `https://sign.yourdomain.com`) |
| `DOCUSEAL_API_TOKEN` | Yes | DocuSeal signing | DocuSeal API authentication token |
| `DOCUSEAL_WEBHOOK_SECRET` | Yes | DocuSeal webhook | Webhook signature verification secret for signing completion callbacks |
| `DOCUSEAL_SIGNING_LINK_EXPIRY_DAYS` | No | DocuSeal signing | Days before signing link expires (default: 7) |
| `SUPABASE_URL` | Yes | All | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | All | Service role key — never exposed to browser, server-side only |
| `SUPABASE_ANON_KEY` | Yes | Frontend auth | Anon key for client-side Supabase queries — never used server-side for auth |
| `FAX_PROVIDER` | Yes | FaxService | `faxplus` or `documo` — set after vendor decision gate in Phase 1B |
| `FAX_API_KEY` | Yes | FaxService | Selected vendor API key |
| `FAX_INBOUND_NUMBER` | Yes | FaxService | TRACE dedicated inbound fax number for receiving records |
| `FAX_WEBHOOK_SECRET` | Yes | Fax webhook | Vendor webhook signature verification secret |
| `AZURE_OPENAI_ENDPOINT` | Yes (Phase 1D+) | Billing reconciliation LLM | Azure OpenAI resource endpoint |
| `AZURE_OPENAI_API_KEY` | Yes (Phase 1D+) | Billing reconciliation LLM | Azure OpenAI API key |
| `AZURE_OPENAI_DEPLOYMENT` | Yes (Phase 1D+) | Billing reconciliation LLM | Deployment name for GPT-4o-mini |
| `OPENMED_MODEL_BASE` | Yes | NLP jobs | Local path to downloaded OpenMed models (`/models/openmed`) |
| `NPI_REGISTRY_BASE_URL` | Yes | Provider extraction | CMS NPI Registry API base URL (`https://npiregistry.cms.hhs.gov/api/`) |
| `PHI_ENCRYPTION_KEY_ID` | Yes | PHI store | pgcrypto key reference for column-level encryption — managed via Supabase key management |
| `NLP_PROVIDER_BACKEND` | Yes | NLP jobs | `openmed` — explicit, never inferred. Pin to openmed for Phase 1C |
| `NLP_LONG_CONTEXT_BACKEND` | Yes | Phase 1D NLP | `disabled` in Phase 1C. Set to `bioclinical_modernbert` in Phase 1D when cross-record flag detection is built |
| `LLM_BACKEND` | Yes | LLM jobs | `disabled` in Phase 1C. No LLM until Phase 1D billing reconciliation |
| `LLM_PHI_ALLOWED` | Yes | LLM jobs | `false` in all non-production environments. `true` only when LLM provider BAA is confirmed and active |
| `ENVIRONMENT` | Yes | All | `development`, `staging`, or `production` — guards prevent real PHI processing outside production |
| `LOG_LEVEL` | No | All | `DEBUG` in development, `INFO` in production — never log PHI values at any level |

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

- **Never allow a chronology to be marked demand-ready with unannotated Priority flags** — the demand-ready approval endpoint must check that all Event Nodes with `flag_priority = 'PRIORITY'` have a non-null `attorney_annotation` field. If any are null, return a 400 with the count of unannotated PRIORITY flags. Do not hardcode specific flag_type values in this check — the gate must cover all current and future PRIORITY flag types automatically.

- **Never display PHI in any URL, notification subject line, email subject, or log entry** — client names, dates of birth, and case details must reference only the opaque case ID and tokenized client reference in all system layers except the encrypted PHI store and the authenticated portal session.

- **Never store any case data locally on the attorney's device** — no localStorage, no IndexedDB, no service worker cache of PHI. The portal is a server-rendered or API-driven interface only.

- **Never process real PHI outside the production environment** — all jobs that handle PHI must check `os.environ.get('ENVIRONMENT')` at the start of execution. If the value is not `production`, the job must refuse to process any data that originated from a real HIPAA authorization. In development and staging, all test data must be synthetic. Enforce this with a module-level guard:

```python
# phi_guard.py — import at the top of every job that touches PHI
import os

def assert_production_for_phi():
    """
    Call this at the start of any job that processes real PHI.
    Raises in non-production environments to prevent accidental PHI processing.
    """
    env = os.environ.get("ENVIRONMENT", "development")
    if env != "production":
        raise RuntimeError(
            f"PHI processing attempted in {env} environment. "
            "Real PHI may only be processed in production. "
            "Use synthetic test data in development and staging."
        )
```

---

## Part 2 — Technology Stack

### 2.1 Stack Decisions [DECISION LOCKED]

Every technology choice below is final for Phase 1. The reasons are stated. Do not substitute.

**Backend: Python 3.11+ with FastAPI**

Reason: FastAPI's async request handling is necessary for the document processing pipeline where multiple records can be processed simultaneously. Python is the language of the medical NLP ecosystem (spaCy, QuickUMLS, OMOP mappings). The TrueVow team can maintain Python. Do not substitute Node.js, Go, or any other language.

**Database: PostgreSQL 15+ via Supabase managed instance**

Reason: TRACE's case data schema has relational integrity requirements — chronology entries must link to source documents, event nodes must link to chronology entries, and all links must be enforced at the database level, not the application level. PostgreSQL's foreign key constraints provide the schema integrity required by PRD Section 8.4. Do not substitute MongoDB, DynamoDB, or any document store.

Note on audit logging: Supabase's managed PostgreSQL does not expose the pgaudit extension to tenant projects. HIPAA audit logging is implemented at the application level via the FastAPI audit middleware (see Part 5, audit_middleware.py) which writes to the append-only audit_log table before every response. The INSERT-only permission on audit_log for the application role enforces immutability. This is the correct and compliant approach for Supabase-hosted PostgreSQL.

**PHI Store: Separate encrypted PostgreSQL instance (Supabase) with column-level encryption AND OpenMed text-level de-identification**

Reason: PHI protection now operates at two levels:

**Level 1 — Text-level de-identification (OpenMed Nemotron Privacy Filter):** All 18 HIPAA Safe Harbor identifiers are redacted from OCR text immediately after extraction, before any downstream processing. This means clinical NER, chronology assembly, gap detection, and all job intermediary states operate on de-identified text. PHI never flows through the processing pipeline in raw form.

**Level 2 — Encrypted storage (pgcrypto + Supabase):** PHI that must be retained for re-identification at attorney portal display (client name for the portal header, dates for chronology rendering, provider names for the portal view) is stored encrypted in a separate Supabase database table using pgcrypto AES-256. The phi_map from OpenMed's de-identification step is the key that links redacted tokens back to their original values. The phi_map itself is encrypted at rest.

The case operational database (chronology_entries, event_nodes, documents) contains only redacted text and opaque tokens — it never contains raw PHI. If the operational database is compromised, no patient PII is exposed. The encrypted PHI store and the phi_map are the only locations where identifiable information exists, both encrypted at column level.

Encryption keys managed via Supabase's key management — never stored in application code or environment variables accessible to the application process.

**File Storage: Supabase Storage (via supabase-py SDK) [IMPLEMENTATION CHOICE — stack confirmed as Fly.io + Supabase]**

Reason: TrueVow's existing repos run on Fly.io (application hosting) with Supabase (PostgreSQL + object storage + auth). TRACE uses the same stack for consistency — no new infrastructure provider, no new BAA negotiation beyond what is already in place.

Supabase Storage is S3-compatible object storage backed by AWS S3 under the hood, covered by Supabase's Business Associate Agreement for HIPAA-eligible projects. Supabase's HIPAA BAA is available on the Team plan and above — confirm it is already executed for TrueVow's Supabase project before Phase 1A begins. If not yet executed, execute it as part of Phase 0 compliance infrastructure before any PHI enters the system.

All object access uses Supabase Storage signed URLs with 15-minute expiry. Documents are stored in a private bucket — no public access policy. Encryption at rest is provided by the underlying AWS S3 infrastructure under Supabase's BAA.

```python
# storage_service.py — Supabase Storage implementation
from supabase import create_client, Client
import os

class SupabaseStorageService:
    def __init__(self):
        self.client: Client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"]  # service role — never exposed to browser
        )
        self.bucket = "trace-medical-records"  # private bucket, created in Phase 1A

    def upload(self, key: str, data: bytes, content_type: str = "application/pdf") -> str:
        self.client.storage.from_(self.bucket).upload(
            path=key,
            file=data,
            file_options={"content-type": content_type, "upsert": False}
        )
        return key

    def presign(self, key: str, expiry_seconds: int = 900) -> str:
        result = self.client.storage.from_(self.bucket).create_signed_url(
            path=key,
            expires_in=expiry_seconds  # 900 = 15 minutes — do not increase
        )
        return result["signedURL"]

    def delete(self, key: str) -> None:
        self.client.storage.from_(self.bucket).remove([key])
```

**Non-negotiable regardless of storage provider:**
- Bucket policy: private, no public access, confirmed in Phase 1A acceptance criteria
- Signed URL expiry: 900 seconds (15 minutes) maximum — hard-coded, not configurable per request
- No PHI in object keys — keys use case_id + document_id only, never client name or DOB
- Supabase HIPAA BAA must be executed before the first real PHI case is processed — this is a production go-live requirement, not a development prerequisite (see Part 9)

**Supabase HIPAA configuration — all 11 items required before Phase 1A acceptance criteria pass:**

Based on Supabase's shared responsibility model documentation (updated July 9, 2026):

| # | Requirement | How to verify |
|---|------------|--------------|
| 1 | Team Plan minimum — HIPAA add-on not available on Free or Pro | Dashboard plan settings |
| 2 | HIPAA add-on enabled via Supabase dashboard HIPAA add-on request | Dashboard → Organization → HIPAA |
| 3 | BAA signed with Supabase | Executed BAA document on file |
| 4 | TRACE project(s) marked as HIPAA projects in project settings | Dashboard → Project → Settings → General → High Compliance |
| 5 | MFA enforced on all Supabase accounts in TrueVow organization | Dashboard → Organization → Auth → Require MFA |
| 6 | Point in Time Recovery enabled (requires compute add-on) | Dashboard → Project → Database → Backups |
| 7 | SSL Enforcement enabled | Dashboard → Project → Settings → Database |
| 8 | Network Restrictions enabled | Dashboard → Project → Settings → Network Restrictions |
| 9 | Postgres connection logging explicitly ON — Supabase sets log_connections to OFF by default for new projects from July 9, 2026. HIPAA projects must override this | Run: `ALTER SYSTEM SET log_connections = on; SELECT pg_reload_conf();` |
| 10 | Supabase AI editor data sharing disabled | Dashboard → Organization → Settings → AI features |
| 11 | PHI not processed through Supabase Edge Functions — all TRACE jobs processing PHI run on Fly.io application servers only | Code review: no Edge Function invocations in OCR job, NLP job, or any PHI-handling path |

Engineering lead must confirm all 11 items checked before the Phase 1A acceptance criteria are evaluated. This checklist is included in the Phase 1A acceptance criteria section below.

**OCR: PaddleOCR-VL 1.5 + Docling (self-hosted, air-gapped) [IMPLEMENTATION CHOICE — updated July 2026]**

deepdoctection + DocTr was the original Tier 1B OCR engine. It is replaced by PaddleOCR-VL 1.5 (released January 2026) which achieves 94.5% on OmniDocBench, supports 109 languages, installs cleanly via a single pip install, and runs on CPU with no GPU requirement. The deepdoctection dependency chain caused hours of version conflict resolution and is eliminated entirely.

**Four-tier OCR routing:**

| Tier | Tool | Document type | Notes |
|------|------|--------------|-------|
| 0 | pypdf | Digital PDFs with embedded text | Free, instant, 100% accurate on typed text |
| 1A | Docling | Digital-born PDFs without text layer | VLM-based, structure-aware, 30x faster than OCR |
| 1B | PaddleOCR-VL 1.5 | Scanned, faxed, handwritten | 94.5% OmniDocBench, 109 languages, self-hosted |
| 2 | Mistral OCR API | Pages where PaddleOCR-VL < 80% confidence | Cloud, only if Tier 1B insufficient |

All tiers except Mistral OCR run inside the Fly.io HIPAA boundary. No BAA needed for Tiers 0–1B. Mistral OCR Tier 2 requires BAA evaluation before activation.

```python
# requirements.txt — complete OCR stack
numpy<2
paddlepaddle>=2.6.0
paddleocr>=2.7.0
docling
openmed>=1.7.0,<1.9.0
```

```python
# ocr_service.py — PaddleOCR-VL 1.5 backend
from paddleocr import PaddleOCR

def build_analyzer():
    """
    Build the PaddleOCR-VL pipeline.
    Call once at startup — not per document.
    DocTr runs locally; no external API calls.
    """
    cfg = dd.set_config_by_yaml("trace_analyzer_config.yaml")
    # config specifies: layout model (Detectron2 or Torchscript),
    # OCR engine: DocTr (not Textract — air-gapped)
    analyzer = dd.get_dd_analyzer(config=cfg)
    return analyzer

ANALYZER = build_analyzer()  # module-level singleton

def process_document(pdf_bytes: bytes) -> dict:
    """
    Submit document bytes to PaddleOCR-VL pipeline.
    Returns structured extraction: pages, text blocks, tables,
    per-block confidence scores, and page-level layout.
    Raises ValueError if mean page confidence below threshold.
    """
    df = ANALYZER.analyze(path_list=[pdf_bytes], output_format="dict")
    pages = []
    for page in df:
        mean_confidence = sum(
            block.get("score", 1.0) for block in page["annotations"]
        ) / max(len(page["annotations"]), 1)

        pages.append({
            "page_number": page["page_number"],
            "text_blocks": page["annotations"],
            "mean_confidence": mean_confidence,
            "flag_for_review": mean_confidence < 0.80  # threshold per PRD §6.2
        })
    return {"pages": pages}
```

**Accuracy note vs Textract:**

PaddleOCR-VL 1.5 achieves 94.5% on OmniDocBench. Pages below 80% confidence are flagged for attorney manual review. If accuracy on handwritten notes is insufficient, activate Mistral OCR Tier 2 via OCR_CLOUD_BACKEND=mistral_api.

**Supabase Storage interaction with OCR:**

The OCR job retrieves document bytes from Supabase Storage, processes them locally through PaddleOCR-VL 1.5, and stores the structured extraction output (JSON) back to Supabase Storage alongside the original document. Document bytes are never sent to any external service.

**Cloud Fax: Fax.Plus Enterprise OR Documo [IMPLEMENTATION CHOICE — vendor locked before Phase 1C]**

Both vendors confirmed HIPAA-compliant with BAA in July 2026 research. Published pricing is the starting point only — actual enterprise costs frequently include compliance riders, volume overage rates, and support tiers that materially change the comparison. The decision protocol below governs the final selection.

| Vendor | BAA availability | Published HIPAA price (2026) | SOC 2 | API depth |
|--------|-----------------|------------------------------|-------|-----------|
| **Fax.Plus** | Enterprise plan only | $99.99/month annual (4,000 pages) — enterprise riders may apply | SOC 2 Type II + ISO 27001 | REST API + webhooks, strong |
| **Documo** | All plans | Contact sales — no public enterprise pricing | HITRUST CSF + SOC 2 Type II | REST API + webhooks |

**Decision protocol — vendor switch trigger and deadline:**

Run this comparison before Phase 1C endpoints are built. The switch has zero architecture impact — both APIs are wrapped identically through the `FaxService` abstraction layer (see Part 5, fax transmission job). Switching after Phase 1C adds no engineering cost.

```
Step 1 — Get real pricing for the actual early access use case:
  - Request Fax.Plus Enterprise BAA quote: include compliance riders,
    volume overage rate above 4,000 pages, and support tier cost.
  - Request Documo enterprise BAA quote: same scope.
  Target volume for quote: 200–500 faxes/month at early access,
  scaling to 2,000–5,000/month at general availability.

Step 2 — Apply the switch rule:
  IF Fax.Plus total annual cost > 2x Documo total annual cost at same volume:
      → Switch to Documo
  ELSE:
      → Keep Fax.Plus Enterprise (stronger published API documentation)

Step 3 — Record the decision:
  Document the actual quotes, the comparison, and the selection
  in the Phase 0 vendor evaluation record before Phase 1C begins.
  The selected vendor's BAA must be executed before any fax is sent.
```

**Switch deadline: before Phase 1C endpoints are built.** Phase 1C builds the fax request generation and transmission endpoints. Once those are built and tested against a vendor's API, switching requires re-testing but no code changes — the `FaxService` interface is identical for both. If the pricing comparison has not been completed by the Phase 1B/1C boundary, default to Documo (all-plan BAA eliminates compliance risk from plan-gating) and re-evaluate at Phase 4.

**Critical constraint that applies regardless of vendor:**
Fax.Plus HIPAA is Enterprise-only — lower tiers (Basic $8.99, Premium $17.99, Business $34.99) do not include BAA coverage and must never be used for PHI transmission. Documo includes BAA on all plans. If Fax.Plus is selected, confirm Enterprise plan is provisioned before any fax API call is made.

**Non-negotiable for either vendor:**
- BAA executed before any PHI is transmitted
- HIPAA mode / Advanced Security Controls enabled (no PHI in email notification content)
- Delivery confirmation webhook integrated — every transmitted fax must log: provider fax number, transmission timestamp, delivery confirmation or failure
- TLS 1.2+ in transit confirmed
- AES-256 at rest confirmed
- SOC 2 Type II or HITRUST current report reviewed before vendor is provisioned

**Clinical NLP and PHI De-identification: OpenMed (self-hosted, air-gapped) [IMPLEMENTATION CHOICE — confirmed by agent, verified Apache-2.0]**

OpenMed is a local-first healthcare AI library providing clinical NER and HIPAA PII de-identification that runs 100% on-device with 1,000+ medical models and 247 PII checkpoints across 12 languages. Apache-2.0, pip-installable, no telemetry, no outbound calls at runtime, no data leaving the infrastructure boundary.

This replaces two previous stack components simultaneously:

**Previous:** scispaCy `en_core_sci_md` (clinical NLP) + pgcrypto only (PHI de-identification at DB level)
**Now:** OpenMed (clinical NER at text level) + OpenMed Nemotron Privacy Filter (all 18 HIPAA Safe Harbor PHI identifiers at text level before any data reaches the database) + pgcrypto (encrypted storage of the PHI that must be retained)

The PHI de-identification upgrade is significant. Previously, PHI de-identification happened only at the database level — raw PHI could exist in OCR output, job intermediary states, and log entries between document ingestion and database write. OpenMed's Nemotron Privacy Filter de-identifies at the text level immediately after OCR, before any clinical extraction runs, ensuring that PHI never appears in unprotected intermediary states.

```python
# nlp_service.py — OpenMed for clinical NER and PHI de-identification
from openmed import analyze_text, deid_text

# Step 1: PHI de-identification immediately after OCR
# Runs before any other processing — PHI never enters downstream jobs as raw text
def deidentify_clinical_text(raw_ocr_text: str) -> dict:
    """
    Apply OpenMed Nemotron Privacy Filter to OCR output.
    Redacts all 18 HIPAA Safe Harbor identifiers.
    Returns: redacted_text (for NLP processing) + phi_map (for encrypted PHI store)
    """
    result = deid_text(
        text=raw_ocr_text,
        model_name="OpenMed/openmed-deid-large",  # 247 PII checkpoints
        return_map=True  # returns offset map for re-identification if needed
    )
    return {
        "redacted_text": result.redacted,
        "phi_map": result.phi_map,  # encrypted and stored separately — never in logs
        "phi_types_detected": result.detected_types  # logged for audit (types only, not values)
    }

# Step 2: Clinical NER on de-identified text
def extract_clinical_entities(redacted_text: str) -> dict:
    """
    Run OpenMed clinical NER on already-de-identified text.
    Extracts: diseases, chemicals, procedures, anatomy, medications, dates (relative only).
    No PHI in input — safe for logging and intermediary storage.
    """
    result = analyze_text(
        text=redacted_text,
        model_name="OpenMed/openmed-ner-clinical-large"
    )
    return {
        "entities": [
            {
                "text": entity.text,
                "label": entity.label,  # DISEASE/CHEMICAL/PROCEDURE/ANATOMY/MEDICATION
                "start": entity.start,
                "end": entity.end,
                "confidence": entity.score
            }
            for entity in result.entities
        ]
    }
```

**Processing sequence with OpenMed:**

```
Raw OCR text (from PaddleOCR-VL)
    ↓
OpenMed Nemotron Privacy Filter (deid_text)
    → redacted_text (PHI replaced with [NAME], [DATE], [ADDRESS] etc.)
    → phi_map (encrypted, stored in PHI store — for attorney-initiated re-identification only)
    ↓
OpenMed Clinical NER (analyze_text on redacted_text)
    → clinical entities (diseases, procedures, medications, anatomy)
    → no PHI in entity values — dates appear as relative references only
    ↓
Chronology assembly (clinical events with source citations)
    → clinical_description uses redacted text values
    → PHI re-introduced only at attorney portal display, fetched from PHI store at render time
```

**HIPAA Safe Harbor compliance via OpenMed:**

The 18 Safe Harbor identifiers are all covered by OpenMed's 247 PII checkpoints: names, geographic data, dates (except year), phone numbers, fax numbers, email addresses, Social Security numbers, medical record numbers, health plan beneficiary numbers, account numbers, certificate/license numbers, vehicle identifiers, device identifiers, URLs, IP addresses, biometric identifiers, full-face photographs, and any other unique identifying numbers.

**Spanish language records:**

OpenMed supports 12 languages including Spanish. The same `deid_text` and `analyze_text` calls work on Spanish-language clinical records — language detection is automatic. This directly resolves PRD §12 Open Question 6 (Spanish records handling) without a separate translation layer.

**Model download and air-gap:**

Download OpenMed models from Hugging Face once to a private model registry or shared filesystem inside the deployment boundary. At runtime, OpenMed loads from local paths — no Hugging Face calls at inference time. Specify local model paths via environment variable:

```
OPENMED_MODEL_BASE=/models/openmed   # populated during Docker build or volume mount
```

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

Reason: PDF.js renders PDFs directly in the browser without sending documents to an external service. It supports page-level navigation, zoom, and annotation. It runs entirely client-side — the actual document bytes are fetched directly from Supabase Storage using a 15-minute signed URL. No document content passes through the Fly.io application server. The application server generates the signed URL and returns it to the browser; the browser fetches the document bytes directly from Supabase Storage. This is the correct HIPAA data flow for document display.

**Authentication: Clerk via @truevow/auth-client [DECISION LOCKED]**

Reason: Clerk is the platform-wide authentication standard across all TrueVow products and domains (PLATFORM_OPERATORS, SALES_SUPPORT, TENANTS). The shared `@truevow/auth-client` library wraps Clerk and provides the `ClerkWrapper` that all services import. TRACE uses this shared library — it does not implement its own Clerk integration. HIPAA technical safeguard requirement for unique user IDs and MFA is met via Clerk's MFA enforcement. All portal routes require a valid Clerk session token validated by the ClerkWrapper.

Do not import `@clerk/nextjs`, `@clerk/backend`, or any Clerk package directly in TRACE. Import from `@truevow/auth-client` only. Do not implement custom authentication.

**Infrastructure: Fly.io [IMPLEMENTATION CHOICE — confirmed stack]**

Reason: TrueVow's existing repos deploy to Fly.io. TRACE uses the same platform for consistency — same CI/CD pipeline, same secrets management, same deployment tooling, no new vendor relationship.

Fly.io provides SOC 2 Type II certification, multi-region deployment, and private networking between application instances and the Supabase database via Fly.io private network or Supabase connection pooling (PgBouncer). Geographic redundancy: deploy TRACE application instances in two Fly.io regions minimum (e.g., `iad` us-east and `lax` us-west or `sea` us-northwest) to satisfy PRD Section 6.3 RTO/RPO requirements.

Secrets management: use Fly.io secrets (`fly secrets set`) for all environment variables containing credentials. Never store secrets in `fly.toml`, Dockerfiles, or application code. The SUPABASE_SERVICE_ROLE_KEY, fax API key, and OCR API key all go into Fly.io secrets.

**Audit Logging: Supabase audit_log table + Fly.io log aggregation [IMPLEMENTATION CHOICE — confirmed stack]**

Reason: TRACE's audit_log table (defined in Section 3.1) is the primary PHI access log — every database-level action on PHI-adjacent tables is captured by the application before writing. This replaces the need for pgaudit (which requires superuser access Supabase does not expose on managed instances).

Application-level audit logging pattern:

```python
# audit_middleware.py — FastAPI middleware
# Every request writes to audit_log before returning response
async def audit_middleware(request: Request, call_next):
    actor_id = get_actor_id_from_jwt(request)  # from Clerk JWT via AuthContext (ClerkWrapper)
    response = await call_next(request)
    await db.execute(
        """
        INSERT INTO audit_log 
            (actor_id, actor_type, action, resource_type, resource_id, 
             case_id, firm_id, ip_address, user_agent, details)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
        actor_id, "ATTORNEY", f"{request.method} {request.url.path}",
        extract_resource_type(request), extract_resource_id(request),
        extract_case_id(request), extract_firm_id(request),
        request.client.host, request.headers.get("user-agent"),
        json.dumps({"status_code": response.status_code})
    )
    return response
```

Fly.io application logs (stdout/stderr from FastAPI) ship to Fly.io's built-in log aggregation. For 6-year HIPAA retention, configure Fly.io log shipping to an external store — options: Supabase (write log events to a separate append-only Supabase table), Papertrail, or Logtail. PHI must not appear in application logs — log only case_id, firm_id, and actor_id, never client names or DOBs.

**Important — Supabase managed PostgreSQL and pgaudit:** Supabase's managed PostgreSQL does not expose pgaudit to tenant projects. Application-level audit logging (the middleware pattern above) is the correct approach for Supabase-hosted TRACE. The audit_log table defined in Section 3.1 is the HIPAA-compliant audit trail. The INSERT-only permission on audit_log for the application role enforces immutability.

## Part 2 — Technology Stack

### 2.1 BAA and HIPAA Compliance Audit — All Stack Vendors

Every vendor in the TRACE stack that could touch PHI must have a signed BAA before Phase 1A begins. This section documents the BAA status, HIPAA plan requirements, published pricing, and known hidden costs for every vendor. Published pricing is a floor — enterprise riders, compliance add-ons, volume overages, and support minimums frequently increase actual cost by 20–100%.

Apply the same decision protocol used for fax vendors to any vendor where actual enterprise pricing is materially higher than published pricing: get real quotes, document the comparison, and lock the vendor before the relevant phase begins.

---

**VENDOR 1 — Fly.io (Application Hosting)**

| Item | Status |
|------|--------|
| BAA available | Yes — pre-signed, active upon customer signature |
| BAA process | Dashboard → Compliance Package → request at fly.io/dashboard/personal/compliance |
| SOC 2 Type II | Yes — audited |
| HIPAA plan requirement | Compliance Package add-on required |
| Published HIPAA price | **$99/month add-on** (on top of compute costs) |
| Compute pricing | Pay-per-second per machine; volumes $0.15/GB/month |
| Hidden cost risks | Enterprise riders may apply for dedicated support SLAs; region-specific markups on compute |
| Action required | Sign BAA via dashboard compliance package before Phase 1A. Confirm $99/month compliance add-on is active on the TrueVow production organization |
| Key constraint | Production environment must be separate from staging/test environments per Fly.io HIPAA guidance |

**Verdict: Straightforward. BAA is pre-signed and self-service. $99/month compliance add-on is the only HIPAA-specific cost beyond normal compute.**

---

**VENDOR 2 — Supabase (PostgreSQL + Storage + Auth)**

| Item | Status |
|------|--------|
| BAA available | Yes — Team Plan and above only |
| BAA process | Submit HIPAA add-on request in Supabase dashboard; request goes to Supabase team for review |
| SOC 2 Type II | Yes — annual audits |
| HIPAA plan requirement | Team Plan minimum + HIPAA add-on enabled |
| Published HIPAA price | **$350/month HIPAA add-on** on top of Team Plan ($25/month) = ~$375/month minimum |
| Hidden cost risks | Point in Time Recovery requires a compute add-on (additional cost); database compute add-ons scale with usage |
| Action required | Upgrade to Team Plan, submit HIPAA add-on request, execute BAA, enable all 11 configuration requirements in §12 Q13 before Phase 1A |
| Key constraint | HIPAA add-on not available on Pro or Free plans. Self-hosted Supabase does not support HIPAA controls — hosted only |

**Verdict: Clear path but non-trivial cost. $375/month minimum before compute. Confirm the HIPAA add-on request is approved before Phase 1A begins — approval is not instantaneous.**

---

**VENDOR 3 — Clerk (Authentication)**

| Item | Status |
|------|--------|
| BAA available | Yes — via enterprise agreement. Referenced in TRACE failover runbook. |
| BAA process | Confirm Clerk BAA is active for the TrueVow organization before production PHI. Check existing enterprise agreement — this may already be in place platform-wide. |
| SOC 2 Type II | Yes |
| HIPAA plan requirement | Enterprise agreement required |
| Published HIPAA price | Custom — verify current agreement covers TRACE as a new product |
| Action required | Confirm existing Clerk enterprise BAA explicitly covers TRACE before production go-live. If not, extend the agreement. |
| Key constraint | Do not use Clerk directly in TRACE code — import from `@truevow/auth-client` only. Platform operators (non-firm-scoped) must not access firm-scoped TRACE data. The ClerkWrapper handles domain separation. |

**Verdict: Clerk is already the platform standard. Verify BAA coverage extends to TRACE before production. No new vendor relationship needed.**

---

**VENDOR 4 — Azure OpenAI GPT-4o-mini (Billing Reconciliation LLM)**

| Item | Status |
|------|--------|
| BAA available | Yes — automatically incorporated via Microsoft Data Protection Addendum (DPA) for Enterprise Agreement, Microsoft Customer Agreement, or CSP customers |
| BAA process | No separate signing required for EA/MCA/CSP. BAA is active upon qualifying licensing. Verify coverage at Microsoft Service Trust Portal |
| SOC 2 Type II | Yes |
| HIPAA plan requirement | Any paid Azure subscription with qualifying licensing — no separate enterprise tier required for HIPAA |
| Published HIPAA price | **No HIPAA add-on fee.** Standard Azure OpenAI pricing applies: GPT-4o-mini at $0.15/1M input tokens, $0.60/1M output tokens (pay-as-you-go, Global Standard) |
| Hidden cost risks | Azure support plan required for production SLAs (Developer $29/month, Standard $100/month, Professional Direct $1,000/month); data egress fees; infrastructure overhead adds 15–20% above token costs in practice |
| Estimated TRACE cost | Billing reconciliation processes ~200–1,000 cases/month at early access. Assuming 5,000 input tokens + 500 output tokens per reconciliation comparison: 200 cases × 5,500 tokens = 1.1M tokens/month ≈ **~$0.50/month at early access volume.** Even at 5,000 cases/month: ~$12/month in tokens |
| Key constraint | BAA covers text inputs only. Image inputs (DALL-E), audio inputs, and preview features are not covered by default. TRACE uses text-only — covered. Do not pass PHI through image or audio modalities |
| Action required | Verify Azure subscription is under EA, MCA, or CSP (not pay-as-you-go consumer account). Confirm coverage at Service Trust Portal. Enable private endpoints and VNet for PHI traffic |

**Verdict: Best value in the stack. Token costs at TRACE volume are negligible. BAA is automatic under qualifying licensing. No hidden compliance cost.**

---

**VENDOR 5 — AWS Textract (OCR — cross-cloud API call)**

| Item | Status |
|------|--------|
| BAA available | Yes — AWS standard BAA covers Textract as a HIPAA-eligible service |
| BAA process | AWS Business Support plan minimum required. BAA request through AWS console or account manager |
| SOC 2 Type II | Yes — AWS has multiple compliance certifications |
| HIPAA plan requirement | Business Support plan minimum (~$100/month or 10% of monthly AWS spend, whichever is higher) |
| Published HIPAA price | No Textract-specific HIPAA add-on. **Business Support plan is the cost.** Textract pricing: $1.50/1,000 pages (document text detection), $15/1,000 pages (forms and tables analysis) |
| Hidden cost risks | Business Support plan minimum; data transfer costs for cross-cloud API calls (Fly.io → AWS); consider whether Textract is cost-effective vs. PaddleOCR-VL 1.5 at expected volume |
| Estimated TRACE cost | 200 cases × 300 pages average = 60,000 pages/month. At $1.50/1,000 pages = **$90/month in Textract fees** + Business Support plan minimum ~$100/month = ~$190/month. At 5,000 cases: ~$2,350/month |
| Key constraint | Textract is the fallback if PaddleOCR-VL 1.5 handwriting accuracy spike fails. Not Phase 1 default — PaddleOCR-VL 1.5 is the default (no AWS account needed if handwriting spike passes) |
| Action required | Only needed if handwriting spike fails and Textract fallback is activated. If activated: execute AWS BAA, enable Business Support plan, confirm Textract is in the list of HIPAA-eligible services for the account |

**Verdict: Only relevant as a fallback. If PaddleOCR-VL 1.5 passes the handwriting spike, AWS account for Textract is not required and this cost does not apply.**

---

**VENDOR 6 — Fax.Plus Enterprise OR Documo (Cloud Fax)**

*(Full decision protocol documented in Section 2.1 above — see Cloud Fax entry)*

| Item | Fax.Plus Enterprise | Documo |
|------|--------------------|----|
| BAA available | Enterprise plan only | All plans |
| Published HIPAA price | $99.99/month annual (4,000 pages) | Contact sales |
| SOC 2 | SOC 2 Type II + ISO 27001 | HITRUST CSF + SOC 2 Type II |
| Hidden cost risks | Enterprise riders, volume overages above 4,000 pages, support tiers | No published pricing — enterprise quote required |
| Switch trigger | If Fax.Plus total annual cost >2x Documo at same volume → switch to Documo |
| Switch deadline | Before Phase 1C endpoints are built |

---

**VENDOR 7 — PaddleOCR-VL 1.5 (OCR — self-hosted)**

| Item | Status |
|------|--------|
| BAA | Not required — self-hosted within Fly.io HIPAA boundary, covered by Fly.io BAA |
| SOC 2 | Not applicable — self-hosted |
| HIPAA cost | $0 — no external API calls, no vendor BAA needed |
| License | Apache 2.0 — free for commercial use |
| Hidden cost risks | Fly.io compute cost for running the OCR pipeline (CPU-intensive); model storage costs |
| Estimated compute cost | PaddleOCR-VL 1.5 is CPU-intensive. Estimate 1–5 CPU-seconds per page. At 60,000 pages/month × 3 CPU-seconds = 50 CPU-hours/month on Fly.io. At ~$0.02/CPU-hour: **~$1/month in compute**. Actual cost depends on machine sizing — benchmark during Phase 1D |
| Action required | No BAA action. Include PaddleOCR-VL 1.5 in the Fly.io HIPAA security risk assessment as a data processing component within the HIPAA boundary |

**Verdict: Zero compliance overhead. All costs are compute costs within the Fly.io billing relationship already established.**

---

**VENDOR 8 — OpenMed (Clinical NLP + PHI De-identification — self-hosted)**

| Item | Status |
|------|--------|
| BAA | Not required — self-hosted within Fly.io HIPAA boundary |
| SOC 2 | Not applicable — self-hosted |
| HIPAA cost | $0 — no external API calls |
| License | Apache 2.0 — free for commercial use |
| Hidden cost risks | Fly.io compute cost for model inference (GPU or CPU); model download bandwidth (one-time); model storage |
| Estimated compute cost | OpenMed NER inference is lighter than OCR. Estimate 60,000 pages/month at ~0.5 CPU-seconds per page = 8 CPU-hours/month ≈ **<$1/month in compute**. De-identification (`deid_text`) adds comparable compute. Total OpenMed compute: **~$2/month at early access volume** |
| Action required | No BAA action. Download models to private model registry during Phase 1A. Confirm `OPENMED_MODEL_BASE` env var set to local path. Verify no outbound network calls during inference — run with network disabled in Phase 1D air-gap test |

**Verdict: Zero compliance overhead. All costs are compute within Fly.io.**

---

---

**VENDOR 9 — DocuSeal (Electronic Document Signing)**

| Item | Status |
|------|--------|
| BAA required | No — self-hosted within Fly.io HIPAA boundary. Covered by Fly.io BAA |
| Deployment | Self-hosted on Fly.io alongside the TRACE FastAPI application |
| License | AGPL-3.0. Use DocuSeal unmodified via its REST API — do not modify DocuSeal source code. All TrueVow customization happens in the TRACE application layer calling the DocuSeal API. This keeps TrueVow code proprietary while using DocuSeal legally |
| SOC 2 | Not applicable — self-hosted within TrueVow's own HIPAA boundary |
| HIPAA cost | $0 — no vendor BAA needed, no compliance add-on, compute only |
| Published price | Free (open-source). Cloud version available at docuseal.com but not used — self-hosted only |
| Estimated compute cost | Lightweight Ruby on Rails app. Fly.io shared-cpu-1x machine sufficient at early access volume. Estimated ~$5–10/month additional compute |
| PHI handling | Client name and contact info passed from TRACE PHI store to DocuSeal API for sending the signing link. This is the only PHI that touches DocuSeal. The signed PDF contains client name and DOB (HIPAA authorization requires these) — stored encrypted in Supabase Storage. DocuSeal itself stores no PHI beyond what is embedded in the signed document |
| Action required | Deploy DocuSeal on Fly.io during Phase 1A infrastructure setup. Configure firm templates during TRACE onboarding. Run test signing session before first real case |
| Key constraint | Do not use DocuSeal's cloud service (docuseal.com) for PHI documents — self-hosted only. The cloud service would require a separate BAA and data residency evaluation |

Minimum monthly cost to operate TRACE in a HIPAA-compliant configuration at early access scale (200 cases/month):

| Vendor | HIPAA-specific cost/month | Notes |
|--------|--------------------------|-------|
| Fly.io | $99 | Compliance Package add-on |
| Supabase | ~$375 | Team Plan $25 + HIPAA add-on $350 |
| Clerk | Verify existing BAA covers TRACE | Platform enterprise agreement — confirm it extends to TRACE before production |
| Azure OpenAI GPT-4o-mini | ~$0.50 | Token costs only; BAA automatic |
| AWS Textract | $0 (fallback only) | Only if PaddleOCR-VL 1.5 fails handwriting spike |
| Documo | $25–125/mo | Quality-first fax selection |
| PaddleOCR-VL 1.5 | ~$1 | Compute only, no compliance cost |
| OpenMed | ~$2 | Compute only, no compliance cost |
| DocuSeal (self-hosted) | ~$5–10 | Compute only, no BAA needed |
| **Total confirmed** | **~$507–612/month + Clerk** | Clerk cost shared across platform — verify existing agreement covers TRACE |

### 2.3 What Not to Use [DECISION LOCKED]

These are explicitly prohibited for TRACE Phase 1:

- **No scispaCy en_core_sci_md** — replaced by OpenMed clinical NER models (confirmed by agent)
- **No raw PHI in any processing pipeline intermediary state** — OpenMed de-identification runs immediately after OCR before any downstream job receives text. This is enforced in the OCR job — not optional
- **No local LLM (Ollama, LMStudio, local Llama3, DeepSeek self-hosted)** — PHI cannot be processed on unmanaged local hardware
- **No DeepSeek API (any version)** — no HIPAA BAA available, China-based infrastructure creates data residency risk incompatible with HIPAA. Do not use until a BAA is published and approved by the Privacy Officer in writing
- **No LLM API from any provider without a signed HIPAA BAA** — this rule supersedes any cost or performance argument. BAA first, then evaluate
- **No Docker deployment to attorney machines** — TRACE is cloud-hosted SaaS only
- **No Streamlit** — not appropriate for a production HIPAA-compliant multi-tenant SaaS application
- **No Docspell** — replaced by PaddleOCR-VL 1.5 for document processing
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
    docuseal_submission_id VARCHAR(255),       -- opaque DocuSeal signing session ID, no PHI
    signing_completed_at TIMESTAMPTZ,          -- timestamp all signatures collected
    provider_list_status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    case_stage          VARCHAR(30) NOT NULL DEFAULT 'PENDING_SIGNATURE',
    approval_attorney_id UUID,
    approval_timestamp  TIMESTAMPTZ,
    approval_text       TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_hipaa_status CHECK (hipaa_auth_status IN ('PENDING','SENT','SIGNED','EXPIRED')),
    CONSTRAINT valid_provider_status CHECK (provider_list_status IN ('DRAFT','CONFIRMED','LOCKED')),
    CONSTRAINT valid_stage CHECK (case_stage IN (
        'PENDING_SIGNATURE','INITIALIZATION','RETRIEVAL','PROCESSING',
        'CHRONOLOGY_READY','ATTORNEY_REVIEW','DEMAND_READY'
    ))
);

-- Signed documents table — DocuSeal integration
-- Stores signing session metadata and audit trail
-- Actual signed PDFs are in Supabase Storage (signed-documents bucket)
CREATE TABLE signed_documents (
    signing_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id                 UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    firm_id                 UUID NOT NULL,
    docuseal_submission_id  VARCHAR(255) NOT NULL,  -- opaque reference, no PHI
    document_type           VARCHAR(50) NOT NULL,   -- RETAINER_PACKAGE / HIPAA_AUTHORIZATION / SUPPLEMENTAL
    signing_status          VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    client_signed_at        TIMESTAMPTZ,
    attorney_template_applied_at TIMESTAMPTZ,
    signed_pdf_storage_key  VARCHAR(1024),          -- Supabase Storage key, signed-documents bucket
    docuseal_audit_trail    JSONB,                  -- embedded audit from DocuSeal: IP, timestamp, method
    reminder_sent_at        TIMESTAMPTZ,
    expires_at              TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT valid_doc_type CHECK (document_type IN (
        'RETAINER_PACKAGE','HIPAA_AUTHORIZATION','SUPPLEMENTAL'
    )),
    CONSTRAINT valid_signing_status CHECK (signing_status IN (
        'PENDING','SENT','PARTIALLY_SIGNED','SIGNED','EXPIRED','DECLINED'
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
    source              VARCHAR(30) NOT NULL DEFAULT 'ATTORNEY_UPLOAD',
    sha256_hash         VARCHAR(64),           -- computed after storage, used for dedup
    original_filename   VARCHAR(255),          -- what the file was named when received, for attorney recognition
                                               -- NEVER log this field — client filenames sometimes contain PHI
                                               -- (e.g., "John_Smith_records.pdf", "DOB_1985_xray.pdf")
                                               -- Store in DB column only. PHIRedactionFilter covers logs but
                                               -- defense-in-depth: never write original_filename to any log statement
    page_count          INTEGER,
    received_at         TIMESTAMPTZ DEFAULT NOW(),
    ocr_status          VARCHAR(20) DEFAULT 'PENDING',
    ocr_confidence      DECIMAL(5,2),
    -- OCR routing fields (populated in Phase 1D, nullable in Phase 1C)
    -- Add now so Phase 1D never needs a migration touching existing records
    document_type_guess VARCHAR(50),    -- e.g. ER_NOTE, LAB_REPORT, BILLING, IMAGING
    page_type_guess     VARCHAR(30),    -- TYPED | HANDWRITTEN | MIXED | FORM
    ocr_route           VARCHAR(30),    -- DOCLING | DOCTR | MISTRAL_LOCAL | LLAMAPARSE
    ocr_backend         VARCHAR(30),    -- which engine actually ran
    needs_escalation    BOOLEAN DEFAULT FALSE,  -- true if Tier 1 confidence below threshold
    source_spans_available BOOLEAN DEFAULT FALSE, -- true when OpenMed source spans are stored
    quality_flags       TEXT[],                -- LOW_OCR_CONFIDENCE, HANDWRITTEN_NOTE_DETECTED, etc.
    is_duplicate        BOOLEAN DEFAULT FALSE,
    is_misfiled         BOOLEAN DEFAULT FALSE,
    CONSTRAINT valid_source CHECK (source IN (
        'PROVIDER_FAX',
        'ATTORNEY_UPLOAD',
        'CLIENT_UPLOAD',
        'SCAN',
        'DOCUSEAL_SIGNED',
        'UNKNOWN'
    ))
);

-- Index for O(1) dedup lookup within a case
CREATE INDEX idx_documents_case_hash ON documents(case_id, sha256_hash)
WHERE sha256_hash IS NOT NULL;

-- Upload links table — secure expiring upload URLs for client document submission
-- No client accounts. No authentication. Token-scoped, expiring.
CREATE TABLE upload_links (
    token           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         UUID NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    firm_id         UUID NOT NULL,
    created_by      UUID NOT NULL,        -- attorney Clerk user ID (from @truevow/auth-client)
    label           TEXT,                 -- shown to client e.g. "Please upload your ER discharge papers"
    expires_at      TIMESTAMPTZ NOT NULL, -- default NOW() + 48 hours
    revoked_at      TIMESTAMPTZ,          -- null until attorney revokes early
    used_at         TIMESTAMPTZ,          -- timestamp of first successful upload
    upload_count    INTEGER DEFAULT 0,    -- incremented per file uploaded
    created_at      TIMESTAMPTZ DEFAULT NOW()
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
    flag_type           VARCHAR(50) NOT NULL,
    flag_priority       VARCHAR(15) NOT NULL DEFAULT 'PRIORITY', -- PRIORITY/ADVISORY/INFORMATIONAL
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
    CONSTRAINT valid_flag_type CHECK (flag_type IN (
        'TREATMENT_GAP',
        'BILLING_DISCREPANCY',
        'ESCALATION_FLAG',
        'DELAYED_INITIAL_TREATMENT',
        'SUDDEN_TREATMENT_STOP',
        'FOLLOWUP_NO_RECORD',
        'NON_COMPLIANT_LANGUAGE',
        'BILL_NO_PROCEDURE_REPORT',
        'CREDIBILITY_LANGUAGE',
        'NEW_PROVIDER_NO_REFERRAL',
        'CHANGING_INCIDENT_DESCRIPTION',
        'CHANGING_SYMPTOM_COMPLAINTS',
        'PRE_EXISTING_CONDITION_SIGNAL',
        'FUNCTIONAL_IMPACT',
        'IMAGING_CROSS_REFERENCE'
    )),
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
- Valid Clerk JWT in Authorization header (validated by ClerkWrapper)
- Firm ID validated against authenticated user's firm membership
- Every request logged to audit_log before response is returned

### 4.0 Document Signing Endpoints (DocuSeal Integration)

```
POST /api/v1/trace/cases/{case_id}/signing/send          -- send package for client signature
GET  /api/v1/trace/cases/{case_id}/signing/status        -- check signing status
POST /api/v1/trace/cases/{case_id}/signing/resend        -- resend signing link to client
GET  /api/v1/trace/cases/{case_id}/signing/documents     -- list signed documents
GET  /api/v1/trace/cases/{case_id}/signing/documents/{id}/download  -- download signed PDF
POST /api/v1/trace/webhooks/docuseal/signing-complete    -- DocuSeal webhook (no auth — verified by signature)
```

**DocuSeal Service Pattern:**

```python
# services/signing_service.py
import httpx
import hmac
import hashlib
import os
from uuid import UUID

class SigningService:
    """
    Wraps DocuSeal API for document package generation and signing.
    DocuSeal is self-hosted on Fly.io — no external API calls, no BAA needed.
    PHI minimization: client contact info (name + phone/email for delivery) 
    retrieved from PHI store just-in-time and never cached or logged.
    """
    def __init__(self, db: AsyncSession, phi_store: PhiStoreService, audit_logger: AuditLogger):
        self._db = db
        self._phi = phi_store
        self._audit = audit_logger
        self._base_url = os.environ["DOCUSEAL_API_URL"]
        self._token = os.environ["DOCUSEAL_API_TOKEN"]

    async def send_signing_package(self, case_id: UUID, firm_id: UUID) -> SigningResult:
        """
        Generate and send retainer + HIPAA auth package to client for signature.
        Attorney signature is pre-applied via firm template.
        Client receives SMS + email with signing link — no account required.
        """
        # Retrieve client contact info from PHI store — just-in-time, not cached
        client_contact = await self._phi.get_contact_for_signing(
            client_token=await self._get_client_token(case_id, firm_id)
        )

        # Get firm's configured templates
        firm_templates = await self._get_firm_templates(firm_id)

        # Call DocuSeal API — internal Fly.io network, no public internet
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/api/submissions",
                headers={"X-Auth-Token": self._token},
                json={
                    "template_id": firm_templates.retainer_package_id,
                    "send_email": True,
                    "send_sms": True,
                    "submitters": [
                        {
                            "role": "Client",
                            "name": client_contact.name,    # from PHI store
                            "email": client_contact.email,  # from PHI store
                            "phone": client_contact.phone,  # from PHI store
                        }
                        # Attorney role is pre-filled via template — no attorney submitter needed
                    ],
                    "message": {
                        "subject": f"Please sign your documents — {firm_templates.firm_name}",
                        "body": (
                            f"Hi {client_contact.first_name},\n\n"
                            f"{firm_templates.firm_name} is ready to represent you. "
                            f"Please review and sign your documents below. "
                            f"Takes about 3 minutes on your phone.\n\n"
                            f"If you have questions, call us at {firm_templates.firm_phone}."
                        )
                    }
                }
            )
            response.raise_for_status()
            submission = response.json()

        # Store signing session — no PHI in the signing record
        signing_record = await self._create_signing_record(
            case_id=case_id,
            firm_id=firm_id,
            docuseal_submission_id=submission["id"],  # opaque ID
            document_type="RETAINER_PACKAGE",
        )

        # Update case manifest
        await self._update_case_signing_status(case_id, "SENT", submission["id"])

        # Log — no PHI in log entry
        await self._audit.log(
            actor_type="SYSTEM",
            action="SIGNING_PACKAGE_SENT",
            resource_type="SIGNED_DOCUMENT",
            resource_id=signing_record.signing_id,
            case_id=case_id,
            firm_id=firm_id,
        )

        # PHI (client contact info) goes out of scope here — not stored anywhere
        del client_contact

        return SigningResult(signing_id=signing_record.signing_id, status="SENT")

    async def handle_signing_webhook(self, payload: dict, signature: str) -> None:
        """
        Called by DocuSeal webhook when all signatures are complete.
        Verifies webhook authenticity before processing.
        Updates case status and stores signed PDF.
        """
        # Verify webhook signature — never trust without verification
        self._verify_webhook_signature(payload, signature)

        submission_id = payload["submission"]["id"]
        status = payload["event"]  # e.g. "submission.completed"

        if status != "submission.completed":
            return  # Ignore non-completion events

        # Look up case by DocuSeal submission ID
        case = await self._get_case_by_submission_id(submission_id)

        # Download signed PDF from DocuSeal and store in Supabase Storage
        signed_pdf_key = await self._store_signed_pdf(
            submission_id=submission_id,
            case_id=case.case_id,
        )

        # Update signing record with audit trail
        await self._update_signing_record(
            submission_id=submission_id,
            status="SIGNED",
            signed_pdf_storage_key=signed_pdf_key,
            audit_trail=payload.get("submission", {}).get("audit_log"),
        )

        # Update case manifest — this triggers provider extraction
        await self._update_case_after_signing(
            case_id=case.case_id,
            signed_at=payload["submission"]["completed_at"],
        )

        await self._audit.log(
            actor_type="CLIENT",
            action="SIGNING_COMPLETED",
            resource_type="CASE",
            resource_id=case.case_id,
            case_id=case.case_id,
            firm_id=case.firm_id,
        )

    def _verify_webhook_signature(self, payload: dict, signature: str) -> None:
        """
        Verify DocuSeal webhook signature to prevent spoofed callbacks.
        Raises if signature is invalid — never process unsigned webhook payloads.
        """
        import json
        expected = hmac.new(
            os.environ["DOCUSEAL_WEBHOOK_SECRET"].encode(),
            json.dumps(payload, separators=(",", ":")).encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise WebhookSignatureError("DocuSeal webhook signature verification failed")
```

**Client experience this produces:**

The client gets a text that says: *"[Firm Name] is ready to represent you. Please review and sign your documents here: [link]. Takes about 3 minutes on your phone. If you have questions, call us at [attorney phone]."*

They tap the link. No app. No account. They see their name, the document, a signature field. They sign with their finger. Done.

The attorney gets: *"[Client first name] has signed. Provider list is being prepared."*

The case starts the same day as the intake call.



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
3. Computes SHA256 hash of document bytes
4. Stores in Supabase Storage with SSE-KMS encryption, source='PROVIDER_FAX'
5. Creates document record in database
6. Triggers OCR processing job (async)
7. Triggers deduplication job (async)
8. Writes to audit_log

**Manual upload handler (attorney):**
- Accepts PDF only (reject other formats with 415)
- Max file size 100MB per document, 2GB per case total
- source='ATTORNEY_UPLOAD'
- Same processing pipeline as fax receipt

### 4.5a Client Secure Upload Link

Attorney generates a one-time upload link and sends it to the client via text or email. Client uploads on their phone. No client account. No password. No TRACE portal access.

```
POST /api/v1/trace/cases/{case_id}/upload-link
  Auth: Clerk JWT via @truevow/auth-client (attorney only)
  Body: { "expires_hours": 48, "label": "Please upload your ER discharge papers" }
  Returns: { "upload_url": "https://truevow.law/upload/{token}", "expires_at": "..." }

GET  /upload/{upload_token}
  Auth: none — public, token-scoped
  Returns: minimal upload page (no nav, no TRACE branding, firm name + attorney label only)

POST /upload/{upload_token}
  Auth: none — token validated against upload_links table
  Body: multipart/form-data, files[]
  Processing:
    1. Validate token exists, not expired, not revoked
    2. Store files in Supabase Storage, source='CLIENT_UPLOAD'
    3. Create document records
    4. Trigger OCR + dedup jobs
    5. Increment upload_links.upload_count, set used_at if first upload
    6. Notify attorney via portal notification + email
    7. Return simple success page — no TRACE branding
  Returns: "Thank you. Your documents have been received by [Firm Name]."

DELETE /api/v1/trace/cases/{case_id}/upload-link/{token}
  Auth: Clerk JWT via @truevow/auth-client (attorney revokes early)
  Effect: sets upload_links.revoked_at, link immediately stops accepting uploads
```

**Token security:**
- Token is a UUID — 122 bits of entropy, unguessable
- Expiry enforced server-side — expired tokens return 410 Gone, not 401
- Revocation enforced server-side — revoked tokens return 410 Gone
- Token is single-use per document only in that 48-hour window — not rate-limited per document, but the attorney can revoke at any time
- Token never appears in any log entry — log case_id and upload_link_id only

**Client upload page design requirements:**
- Works on a phone as the primary device — large tap targets, no hover states
- Upload area doubles as a camera button on mobile (input type=file accept="image/*,application/pdf" capture=environment)
- No login prompt, no "create an account," no TRACE logo, no portal navigation
- Only visible elements: firm name, attorney's label, upload area, submit button
- After successful submit: "Thank you. Your documents have been received by [Firm Name]." — nothing else
- The client should not know what software the attorney uses

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

**Trigger:** Fires asynchronously after case initialization completes (after DocuSeal webhook confirms signing).

**Critical rule — NPI match is not authorization to fax:**

NPI lookup enriches provider candidates with publicly available information (name, fax number, specialty, address). It does not authorize a fax transmission. A confirmed NPI match means the provider exists in the CMS registry. It does not mean:
- The attorney's client actually received treatment from this specific provider
- The fax number in the NPI Registry is current and correct
- The attorney has reviewed and approved this provider for record requests

The following sequence is mandatory and cannot be short-circuited:

```
NPI lookup → CANDIDATE created (confidence label assigned)
                    ↓
         Attorney reviews provider checklist
                    ↓
         Attorney CONFIRMS each provider (Checkpoint 1)
                    ↓
         Attorney approves outgoing request list (Checkpoint 2)
                    ↓
         Fax transmitted
```

No fax may be sent based on NPI lookup alone. Ever. The Checkpoint 1 gate at `POST /cases/{id}/providers/confirm` and the Checkpoint 2 gate at `POST /cases/{id}/requests/send` enforce this in code. The rule is also enforced by the `hipaa_auth_status = SIGNED` check at Checkpoint 2 — the signed HIPAA authorization names specific providers the client authorizes records requests to. Sending a fax to a provider not confirmed by the attorney is a potential HIPAA violation regardless of NPI match quality.

**Steps:**
1. Load Benjamin intake record JSON for the case
2. **Run OpenMed Nemotron Privacy Filter on intake transcript text first** (`deid_text()`) — produces redacted transcript + phi_map
3. Run OpenMed clinical NER (`analyze_text()`) on redacted transcript text:
   - Extract named entities: ORG (organizations/facilities), PERSON (physician names — de-identified tokens), GPE (locations)
   - Filter for entities likely to be healthcare providers based on context window and entity label
4. Re-introduce provider name values from phi_map for NPI Registry lookup only — provider names are needed to query the NPI Registry but are not stored in the operational database as raw PII
5. For each extracted provider candidate:
   a. Query CMS NPI Registry API: `https://npiregistry.cms.hhs.gov/api/?version=2.1&name={provider_name}&state={jurisdiction}`
   b. If single confident match: create provider record with UNCONFIRMED status, pre-fill all fields from NPI response (NPI number, registered name, address, fax number)
   c. If multiple matches: create provider record with UNCONFIRMED status, flag as "Multiple matches — attorney selection required"
   d. If no match: create provider record with UNCONFIRMED status, flag as "Not found in NPI Registry — attorney entry required"
6. Update case_stage to RETRIEVAL
7. Notify attorney via portal notification and SMS/email alert: "Provider list ready for your review — {n} providers identified"

**Confidence scoring:**
- HIGH: explicit facility name or physician full name + specialty match in NPI Registry
- MEDIUM: partial name match or location-only reference
- LOW: implied provider ("the hospital", "my doctor") with no identifying information
- LOW-confidence providers are shown with a warning label in the provider confirmation checklist

### 5.1b Deduplication Job

**Trigger:** Fires immediately after a document is stored and its SHA256 hash is computed. Runs for every document regardless of source — fax, attorney upload, client upload, or DocuSeal signed document.

**Steps:**

```python
async def run_dedup_check(document_id: UUID, case_id: UUID) -> None:
    """
    Exact duplicate detection via SHA256 hash comparison within the same case.
    Near-duplicate detection (perceptual hashing for same content / different scan quality)
    is deferred to Phase 2 — too complex for Phase 1 early access scale.

    Never auto-deletes. Always requires attorney confirmation before removal.
    Tracks provenance so attorney can see which copy came from which source.
    """
    doc = await db.get_document(document_id)

    if not doc.sha256_hash:
        # Hash not yet computed — skip, dedup will run after OCR completes
        logger.warning("Dedup skipped: hash not available", extra={"document_id": str(document_id)})
        return

    # Look for exact match within this case — the index makes this O(1)
    existing = await db.execute(
        select(Document)
        .where(Document.case_id == case_id)
        .where(Document.sha256_hash == doc.sha256_hash)
        .where(Document.document_id != document_id)
        .where(Document.is_duplicate == False)  # only compare against non-duplicate copies
        .order_by(Document.received_at.asc())   # oldest copy is authoritative
        .limit(1)
    )

    if not existing:
        return  # No duplicate found — do nothing

    # Mark incoming document as duplicate — never auto-delete
    await db.update_document(document_id, is_duplicate=True)

    # Log with provenance — attorney needs to see both copies and decide
    await audit_logger.log(
        actor_type="SYSTEM",
        action="DUPLICATE_DOCUMENT_DETECTED",
        resource_type="DOCUMENT",
        resource_id=document_id,
        case_id=case_id,
        firm_id=doc.firm_id,
        details={
            "duplicate_of": str(existing.document_id),
            "original_source": existing.source,
            "original_received_at": existing.received_at.isoformat(),
            "duplicate_source": doc.source,
            # Note: never log document content, file name, or PHI here
        }
    )

    # Surface in portal — informational, not urgent, does not block any workflow
    await notify_portal(
        firm_id=doc.firm_id,
        case_id=case_id,
        notification_type="DUPLICATE_DOCUMENT",
        message=(
            f"A duplicate document was detected. "
            f"Original received from {existing.source} on {existing.received_at.date()}. "
            f"New copy received from {doc.source}. "
            f"Review both copies and confirm which to keep."
        )
    )
```

**What deduplication does NOT do:**
- Does not auto-delete either copy — attorney must confirm
- Does not flag as priority or block any checkpoint — it is informational
- Does not run near-duplicate detection (same content, different scan — deferred Phase 2)
- Does not deduplicate across cases — only within the same case

**Source provenance values and their meaning:**

| Source | What it means |
|--------|--------------|
| `PROVIDER_FAX` | Received via inbound fax from healthcare provider |
| `ATTORNEY_UPLOAD` | Attorney manually uploaded from their device |
| `CLIENT_UPLOAD` | Client submitted via secure upload link |
| `SCAN` | Staff scanned physical document and uploaded |
| `DOCUSEAL_SIGNED` | Signed document returned by DocuSeal webhook |

When a duplicate is detected, the portal shows the attorney both copies with their source labels so they know which is the authoritative provider copy and which is the client's personal copy.

### 5.2 OCR Processing Job

**Trigger:** Fires asynchronously when a document record is created (fax received or manual upload).

**Steps:**
1. Retrieve document bytes from Supabase Storage using document.s3_key (storage key)
2. Submit to PaddleOCR-VL: `ocr.ocr(document_bytes, cls=True)`
3. Receive structured page output with text blocks and per-block confidence scores
4. Evaluate per-page mean confidence scores:
   - Pages with mean confidence below 80%: flag as LOW_CONFIDENCE, mark for attorney manual review
   - Pages with mean confidence 80–95%: flag as MEDIUM_CONFIDENCE, include in processing but note in index
   - Pages with mean confidence above 95%: flag as HIGH_CONFIDENCE, proceed to extraction
5. **Immediately run OpenMed Nemotron Privacy Filter on each page's raw OCR text** (`deid_text()`)
   - Returns: redacted_text (PHI replaced with type tokens), phi_map (offset map of what was redacted), phi_types_detected (for audit log — types only, never values)
   - Store redacted_text only in the processing pipeline — raw PHI text is not stored in any intermediary state
   - Encrypt phi_map and store in PHI store alongside the document record
   - Log phi_types_detected to audit_log (entity types only — no values)
6. Store PaddleOCR-VL extraction output (JSON) and redacted page text back to Supabase Storage
7. Update document.ocr_status and document.ocr_confidence
8. If document.ocr_status = COMPLETE: trigger clinical event extraction job with **redacted text only**

### 5.3 Clinical Event Extraction Job

**Trigger:** Fires after OCR and de-identification are complete for a document. Receives **redacted text only** — no raw PHI in this job.

**Steps:**
1. Load redacted page text from Supabase Storage (output of OCR job — PHI already removed by OpenMed)
2. Run OpenMed clinical NER pipeline (`analyze_text()` with `openmed-ner-clinical-large`):
   - Named entity recognition: diseases, chemicals, procedures, anatomy, medications
   - Sentence segmentation for context window construction
   - Language auto-detected (handles Spanish records natively — resolves PRD §12 Open Question 6)
3. For each candidate clinical event (date reference + clinical action detected in entity output):
   a. Extract: event_date (normalized to ISO 8601 — relative dates resolved against incident_date from case manifest), provider token (de-identified reference), event_type (classified from entity labels), clinical_description (verbatim redacted sentence from source)
   b. Record source_document_id and source_page_number
   c. Apply deduplication: if same event_date + provider + event_type already exists in chronology for this case from a different document, flag as potential duplicate for attorney review
4. Write to chronology_entries table (redacted clinical_description — PHI tokens like [NAME] and [DATE] appear as-is in the stored record; attorney portal re-introduces de-identified values at display time by fetching from PHI store)
5. When all documents for a case are processed: trigger gap detection job

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
4. What authentication does the billing repo API use? (Should use the same Clerk service token or a service-to-service token.)

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
2. Receives Supabase Storage signed URL (900-second / 15-minute expiry)
3. PDF.js loads the document directly from Supabase Storage using this URL
4. Panel scrolls to the correct page automatically
5. No application server bytes involved in document display — document bytes flow directly from Supabase Storage to the browser

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

- [ ] Fly.io: TRACE production organization created, separate from staging/test — production environment isolation required per HIPAA guidance
- [ ] DocuSeal: self-hosted instance deployed on Fly.io (`fly deploy` from DocuSeal Docker image). Accessible at internal Fly.io private network URL — not exposed publicly. DOCUSEAL_API_URL, DOCUSEAL_API_TOKEN, DOCUSEAL_WEBHOOK_SECRET set in Fly.io secrets
- [ ] DocuSeal: firm retainer template, contingency fee template, and HIPAA authorization template uploaded. Attorney signature field pre-configured
- [ ] DocuSeal: webhook endpoint registered pointing to TRACE `/webhooks/docuseal/signing-complete`
- [ ] DocuSeal test: send a test signing package to a test email address, sign it, confirm webhook fires, confirm signed PDF stored in Supabase Storage `signed-documents` bucket, confirm `cases.hipaa_auth_status` updates to SIGNED
- [ ] Supabase: TRACE production project provisioned, marked as HIPAA / High Compliance in project settings
- [ ] PostgreSQL schemas created: all tables from Section 3.1, applied via Alembic migrations
- [ ] Database roles and permissions applied: Section 3.2
- [ ] Application-level audit logging middleware confirmed: every API request writes to audit_log with actor_id, timestamp, action, resource_type
- [ ] Clerk via @truevow/auth-client: ClerkWrapper middleware configured, JWT validation working in FastAPI, MFA enforced on all portal accounts, firm_id and role extracted into AuthContext from Clerk JWT claims
- [ ] FastAPI skeleton: authentication middleware, audit logging middleware, error handling
- [ ] Supabase Storage: `trace-medical-records` bucket created with private access policy confirmed
- [ ] OpenMed models downloaded to private model registry on Fly.io volume — `openmed.analyze_text()` returns result with no network calls

**⚠ VENDOR BAA AND HIPAA CONFIGURATION — all items below are PRODUCTION-ONLY actions. Do not request BAAs, enable HIPAA add-ons, or sign compliance agreements until the system is ready for production PHI. During development and testing, use synthetic data only — no real PHI enters the system until all BAAs are signed and all HIPAA configurations are confirmed.**

**When ready for production (not now — tracked separately from the build sequence):**
- [ ] Fly.io: Compliance Package signed via fly.io/dashboard/personal/compliance ($99/month add-on)
- [ ] Supabase: Team Plan active, HIPAA add-on request submitted and approved, BAA signed ($350/month add-on)
- [ ] **Clerk:** Existing platform enterprise BAA confirmed to cover TRACE. MFA enforcement active for attorney portal accounts. Confirm with TrueVow legal before first real attorney session.
- [ ] Supabase HIPAA configuration — all 11 items from §12 Q13 confirmed: HIPAA add-on enabled, TRACE project marked High Compliance, MFA enforced on all organization accounts, Point in Time Recovery enabled, SSL Enforcement enabled, Network Restrictions enabled, Postgres connection logging explicitly ON, AI editor data sharing disabled, no Edge Functions in PHI path
- [ ] Fax vendor BAA executed (per decision protocol — before fax endpoints go to production)
- [ ] Azure OpenAI: qualifying licensing confirmed (EA/MCA/CSP), BAA coverage verified at Microsoft Service Trust Portal, private endpoints enabled for PHI traffic

**Phase 1A development acceptance criteria (no PHI, no BAAs required at this stage):**
A test request to any authenticated API endpoint is logged in audit_log with correct actor_id, timestamp, and action. An unauthenticated request returns 401. A request from firm A cannot access firm B's data. Supabase Storage bucket `trace-medical-records` exists with private access policy confirmed. OpenMed models respond locally with no network calls. All Alembic migrations apply cleanly to a fresh database.

### Phase 1B — Case Initialization and SOL (Weeks 2–3)

- [ ] PHI encryption/decryption via pgcrypto confirmed working
- [ ] Case initialization endpoint (Section 4.2) built and tested
- [ ] SOL calculation function (Section 5.4) built with full 50-state table
- [ ] NPI Registry API integration tested against 20 real provider lookups
- [ ] Provider extraction job skeleton (Section 5.1) built — NPI lookup working, OpenMed NER pending until Phase 1C
- [ ] Portal: Case list view and case initialization trigger from INTAKE

**⚠ FAX VENDOR DECISION GATE — vendor selection must complete before Phase 1C begins. BAA execution is production-only (tracked separately):**
- [ ] Fax.Plus Enterprise pricing quote obtained — full cost including compliance riders, volume overages, support tier (no commitment, quote only)
- [ ] Documo enterprise pricing quote obtained — same scope (no commitment, quote only)
- [ ] Switch rule evaluated: if Fax.Plus total annual cost > 2x Documo at target volume → switch to Documo
- [ ] Selected vendor documented — decision recorded with actual quotes
- [ ] `FAX_PROVIDER` environment variable set in Fly.io secrets (`faxplus` or `documo`) pointing to sandbox/test credentials for development
- [ ] BAA execution deferred to production readiness — tracked in production go-live checklist, not Phase 1B

**Acceptance criteria:** Creating a case from a test intake record produces a case with correct SOL deadline, correct urgency label, and the disclaimer text. PHI is encrypted in the PHI store and not visible in the operational database. Fax vendor is selected and documented with actual quotes. Sandbox fax credentials configured and fax service layer tested against vendor sandbox environment.

### Phase 1C — Provider Confirmation and Record Request (Weeks 3–5)

- [ ] OpenMed installed and tested: `openmed.deid_text()` on 5 sample clinical text strings confirms all 18 Safe Harbor identifier types are redacted
- [ ] OpenMed clinical NER (`openmed.analyze_text()`) tested on 10 sample de-identified intake transcripts producing provider candidate entities
- [ ] Provider extraction NLP pipeline producing provider candidates from intake text using OpenMed NER
- [ ] Provider confirmation checklist UI built (all CRUD endpoints + confirm endpoint)
- [ ] Fax request generation (HIPAA cover sheet PDF creation) working
- [ ] Fax transmission via Fax.Plus API working with delivery confirmation webhook
- [ ] Portal: Provider review interface with confirm flow and request preview

**Acceptance criteria:** End-to-end test with a synthetic case: intake record → provider extraction → attorney confirms list → fax request generated → fax transmitted → webhook confirms delivery. All steps logged in audit_log.

### Phase 1D — Record Processing and Chronology (Weeks 5–8)

- [ ] Fax receive webhook processing working (document stored in S3, document record created)
- [ ] Manual upload endpoint working
- [ ] **PaddleOCR-VL 1.5 handwriting accuracy spike:** Benchmark against minimum 20 pages of de-identified handwritten clinical notes (urgent care notes + chiropractor notes). If mean accuracy below 80%, evaluate Google Document AI fallback — activate OCR_CLOUD_BACKEND=mistral_api in Fly.io secrets, no code changes
- [ ] PaddleOCR-VL 1.5 pipeline: `PaddleOCR().ocr()` processing a test PDF with no external API calls confirmed
- [ ] OpenMed `deid_text()` running immediately after OCR output confirmed — raw PHI not present in any downstream intermediary state (verified by inspecting job output before chronology write)
- [ ] OpenMed clinical NER running on de-identified text producing chronology entries with source citations
- [ ] Gap detection job (Section 5.5) producing TREATMENT_GAP event nodes
- [ ] **Extended Flag Registry — Tier 1 jobs (Section 5.5.3):**
  - [ ] T1-01 Delayed initial treatment job — date math on incident_date vs first_clinical_entry_date
  - [ ] T1-02 Sudden treatment stop job — last entry per provider checked for discharge/MMI strings
  - [ ] T1-03 Follow-up with no record job — string match on follow-up language + 60-day forward check
  - [ ] T1-04 Non-compliant language job — string match on non-compliant terms list, all instances flagged
  - [ ] T1-05 Bill with no procedure report job — CPT surgical range check vs document set completeness
  - [ ] T1-06 Clinician credibility language job — string match on credibility terms list, all instances flagged
- [ ] **Extended Flag Registry — Tier 2 jobs (Section 5.5.3):**
  - [ ] T2-01 New provider without referral job — provider introduction events vs preceding referral entities via OpenMed NER
  - [ ] T2-02 Changing incident description job — mechanism of injury entity cross-comparison across first entries per provider
  - [ ] T2-03 Changing symptom complaints job — body region entity tracking across chronology via OpenMed anatomy NER
  - [ ] T2-04 Pre-existing condition signal job — degenerative/prior condition string match + OpenMed body region NER on post-incident records; full cross-record comparison if pre-incident records opted in
  - [ ] T2-05 Functional impact tagging job — OpenMed NER for work restrictions, ADL limitations, ROM measurements, pain scores, future care language
  - [ ] T2-06 Imaging cross-reference link job — imaging order entity matched against imaging report documents within 90 days
- [ ] **flag_priority field populated correctly** for all new flag types per Section 5.5.4 priority table
- [ ] **Demand-ready gate updated** — confirms it counts only PRIORITY flags, not ADVISORY or INFORMATIONAL
- [ ] Billing reconciliation job (Section 5.6) with CPT extraction and prohibited string filter
- [ ] Prohibited string filter tested: confirm it blocks the prohibited terms list

**Acceptance criteria:** Process a set of 10 real PI medical record PDFs (de-identified before testing) through the full pipeline. PaddleOCR-VL 1.5 produces text extraction with per-page confidence scores. OpenMed `deid_text()` runs immediately after OCR — no raw PHI appears in any job output downstream. OpenMed clinical NER produces chronology entries with source citations. At least one treatment gap detected and flagged. All system_description values pass the prohibited string filter without triggering. No network calls made during OCR or NLP processing (air-gap confirmed).

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
- **No PHI in logs:** Assert that Fly.io application log streams contain no plaintext client names or DOBs — PHI values must never appear in any log output, only case_id and firm_id references
- **Encryption at rest:** Assert that a direct SELECT on the clients table returns encrypted bytea, not plaintext
- **Signed URL expiry:** Assert that a Supabase Storage signed document URL returns 403 after 900 seconds (15 minutes)

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

## Part 9 — Production Go-Live Checklist

**This checklist is separate from the build sequence. Do not action any item on this list until the system is built, tested on synthetic data, and explicitly ready for production PHI.**

All items must pass before the first real attorney BAA is signed or the first real case is processed.

### 9.1 Vendor BAA Execution (Production-Only — Do Not Action During Development)

- [ ] **Fly.io:** Compliance Package signed at fly.io/dashboard/personal/compliance. $99/month add-on active on production organization
- [ ] **Supabase:** Team Plan active, HIPAA add-on approved and enabled, BAA signed and on file (~$375/month). TRACE production project marked as HIPAA / High Compliance
- [ ] **Clerk:** Platform enterprise BAA confirmed to explicitly cover TRACE. MFA enforced on all attorney portal accounts. Verified by TrueVow compliance team.
- [ ] **Fax vendor (Fax.Plus Enterprise or Documo):** BAA executed with selected vendor. Confirm HIPAA mode / Advanced Security Controls ON. If Fax.Plus: confirmed on Enterprise plan only
- [ ] **Azure OpenAI:** Qualifying licensing confirmed (EA, MCA, or CSP — not pay-as-you-go consumer account). BAA coverage verified at Microsoft Service Trust Portal. Private endpoints and VNet enabled for PHI traffic

### 9.2 Supabase HIPAA Configuration (All 11 Items — Production Project Only)

- [ ] HIPAA add-on enabled in Supabase dashboard
- [ ] TRACE project marked as HIPAA / High Compliance in project settings
- [ ] MFA enforced on all Supabase accounts in the TrueVow organization
- [ ] Point in Time Recovery enabled (compute add-on required)
- [ ] SSL Enforcement enabled
- [ ] Network Restrictions enabled
- [ ] Postgres connection logging explicitly ON — `ALTER SYSTEM SET log_connections = on; SELECT pg_reload_conf();` (Supabase default is OFF for projects from July 9, 2026)
- [ ] Supabase AI editor data sharing disabled
- [ ] No Supabase Edge Functions in any PHI-handling code path — confirmed by code review
- [ ] Production environment separate from staging/test — separate Supabase project and Fly.io organization
- [ ] Point in Time Recovery tested — confirm recovery to a known state works before first PHI case

### 9.3 Infrastructure Security

- [ ] Supabase Storage bucket `trace-medical-records`: private access policy confirmed, no public access, HIPAA BAA active
- [ ] All application secrets in Fly.io secrets (`fly secrets set`) — not in `fly.toml`, Dockerfiles, or source code. Verify with `fly secrets list` — no secrets in git history
- [ ] All API endpoints require valid Clerk JWT (validated by ClerkWrapper) — return 401 without one
- [ ] MFA enforced for all attorney portal accounts (Clerk) — cannot be disabled per-user
- [ ] Audit log: application role has INSERT only on audit_log — no SELECT, UPDATE, or DELETE
- [ ] PHI store: accessible only via `trace_phi_role` — not `trace_app_role` by default
- [ ] Supabase signed URL expiry confirmed at 900 seconds maximum — no wildcard permissions
- [ ] No client PII in any URL, log entry, notification subject line, or email body — verified by log inspection

### 9.4 Functional Gates

- [ ] Prohibited string filter: unit tests passing on all terms in PROHIBITED_STRINGS list, integrated into all LLM output pipelines
- [ ] Demand-ready gate: confirmed blocking when unannotated PRIORITY flags > 0
- [ ] Provider list confirmation gate: confirmed blocking fax transmission before attorney confirmation timestamp
- [ ] Fax delivery confirmation webhook working: every transmitted fax logs provider fax number, timestamp, and delivery confirmation or failure
- [ ] HIPAA mode confirmed ON for fax vendor: no PHI in email notification content

### 9.5 Compliance Documentation

- [ ] HIPAA Security Risk Assessment: completed, all High residual risk items remediated
- [ ] Penetration test: completed by qualified external firm, critical findings remediated
- [ ] Healthcare attorney has reviewed and signed off on BAA template, attorney responsibility addendum, and HIPAA authorization template
- [ ] Privacy Officer and Security Officer designated in writing
- [ ] Workforce HIPAA training completed for all staff with PHI access — completion records retained
- [ ] Incident response plan documented and tested

### 9.6 Attorney Onboarding Readiness

- [ ] TrueVow ↔ attorney firm BAA template finalized by healthcare attorney
- [ ] Attorney responsibility addendum finalized
- [ ] HIPAA authorization template finalized and tested in retainer package workflow
- [ ] TRACE onboarding flow built: BAA signing, HIPAA auth template configuration, provider workflow walkthrough, test call
- [ ] Support contact workflow: first 3 cases per early access firm reviewed with support contact present
- [ ] All Phases 1A–1F acceptance criteria passing on production infrastructure

---

*Document version 1.0 — July 2026. Updates to this specification require product owner approval and must be reflected in the TRACE PRD before implementation. Any deviation from the technology stack decisions in Section 2 requires written approval from the Privacy Officer.*
