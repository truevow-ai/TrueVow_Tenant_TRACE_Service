# ADR-002 — TRACE Phase 1B Architecture Plan
## Case Initialization, SOL, DocuSeal Signing, NPI Lookup

**Status:** Ready for Phase 1B Build  
**Date:** July 2026  
**Supersedes:** Nothing — extends ADR-001  
**Prerequisite reading:** ADR-001, TRACE PRD §3–§5, TRACE Technical Implementation Spec §4.0–§4.2, §5.1, §5.4  
**Phase 1A status:** Complete — 36/36 tests passing, schema migrated, all stubs in place

**Architecture decisions updated from agent gap analysis (July 2026):**
- Supabase: same project as LEVERAGE, trace + trace_phi schemas (not separate project)
- PHI encryption: app-level AES-256-GCM via cryptography library (not pgcrypto)
- Six pre-Phase-1B fixes required — see §13

---

## 1. What Phase 1B Builds

Phase 1B is the first phase that produces attorney-visible behavior. After Phase 1B, an attorney can:

1. See a case appear in their TRACE portal after INTAKE emits `matter.ready_for_signature`
2. Receive the HIPAA authorization and retainer package via DocuSeal for client signature
3. See the SOL deadline calculated and displayed with the correct disclaimer
4. See a provider list pre-populated from the intake record after the client signs

Nothing in Phase 1A was visible to the attorney. Everything in Phase 1B is.

**Event naming clarification:** The triggering event is `matter.ready_for_signature` — not "retainer-signed." The retainer is NOT signed at this point. The attorney has approved the draft package and is ready to send it. DocuSeal delivers the package. The client signs. Then the case advances to INITIALIZATION.

**Six deliverables in strict build order:**

```
0. Phase 1B-0 compliance preflight (BAA verification, PHI gate, secrets check)
1. PHI encryption (AES-256-GCM, app-level) ←─ must work before case_id → client_token link is safe
2. Case initialization endpoint ←─ must work before SOL and DocuSeal are useful  
3. SOL calculation ←─ runs synchronously inside case initialization
4. DocuSeal SigningService ←─ fires immediately after case is initialized
5. NPI Registry integration + provider extraction skeleton ←─ fires after client signs
```

Do not start 1 until the 6 pre-Phase-1B fixes from §13 are complete and tests pass.
Do not start 2 until 1 is tested. Do not start 4 until 2 and 3 are tested. Do not start 5 until 4 is tested.

### Phase 1B-0 — Compliance Preflight

All items must pass with binary yes/no before Deliverable 1 begins:

```
[ ] PHI_ENCRYPTION_KEY present in Fly.io secrets (32 bytes, base64)
[ ] trace + trace_phi schemas confirmed in Supabase project
[ ] RLS enabled on all trace.* tables
[ ] Firm isolation RLS policy confirmed: query from non-service
    role with firm_A JWT cannot read firm_B rows
[ ] PHI leakage test (test_phi_never_in_operational_db) in
    test suite and passing
[ ] signing_sent_at column confirmed on trace.cases
[ ] sol_table_version column confirmed on trace.cases
[ ] DocuSeal deployed on Fly.io, reachable at DOCUSEAL_API_URL
[ ] DocuSeal webhook endpoint registered
[ ] DOCUSEAL_API_TOKEN, DOCUSEAL_WEBHOOK_SECRET in Fly.io secrets
[ ] Fax vendor sandbox credentials in Fly.io secrets
[ ] unique_docuseal_submission constraint on signed_documents
[ ] 37/37 tests passing after all 6 fixes merged
[ ] assert_production_for_phi() raises in non-production environments
[ ] Synthetic PHI fixtures only in dev/staging — test_ prefix names
[ ] PHIRedactionFilter confirmed on root logger
[ ] Supabase BAA + HIPAA add-on active (production go-live gate)
[ ] Fly.io BAA signed (production go-live gate)
```

No real client PHI in Phase 1B dev/staging/local. Synthetic data only.

---

## 2. The Phase 1B Data Flow

```
INTAKE system fires case.created event
        ↓
TRACE subscribes to INTAKE outbox
        ↓
POST /api/v1/trace/cases (case initialization)
  ├─ Encrypt client PII → PHI store (pgcrypto AES-256)
  ├─ Write opaque client_token to cases table (not raw PII)
  ├─ Calculate SOL deadline (synchronous, 50-state table)
  ├─ Set case_stage = PENDING_SIGNATURE
  └─ Return case_id + SOL info to INTAKE
        ↓
POST /api/v1/trace/cases/{case_id}/signing/send (DocuSeal)
  ├─ Retrieve client contact from PHI store (just-in-time)
  ├─ Call DocuSeal API → generate retainer + HIPAA auth package
  ├─ Attorney signature template auto-applied
  ├─ Client receives SMS + email with signing link
  └─ Client contact deleted from memory immediately after call
        ↓
Client signs on phone (DocuSeal handles, no TRACE involvement)
        ↓
POST /api/v1/trace/webhooks/docuseal/signing-complete
  ├─ Verify HMAC signature (reject if invalid)
  ├─ Download signed PDF → Supabase Storage (signed-documents bucket)
  ├─ Update signed_documents record
  ├─ Update cases: hipaa_auth_status = SIGNED, case_stage = INITIALIZATION
  └─ Trigger provider extraction job (async)
        ↓
Provider extraction job (async, Spec §5.1)
  ├─ Load Benjamin intake record JSON
  ├─ OpenMed NER stub → provider candidates (real NER in Phase 1C)
  ├─ NPI Registry lookup per candidate
  └─ Write providers table with confidence labels
        ↓
Attorney notified: "Provider list ready for your review"
```

---

## 3. PHI Encryption Architecture

**Three-layer encryption model:**

```
Layer 1 — Supabase Vault:  Service secrets (Fax API key, DocuSeal webhook
                            secret, database-adjacent credentials).
                            Single string values accessible only via
                            service_role. Referenced by ID, never in
                            application code.

Layer 2 — trace_phi schema: Structured PHI records. App-level AES-256-GCM
                            via Python cryptography library. Key in Fly.io
                            secrets (PHI_ENCRYPTION_KEY). RLS for firm
                            scoping. Queryable with foreign keys.

Layer 3 — Disk encryption:    AES-256 at rest for all Supabase data
                            (platform default, always on).
```

Vault is correct for single-string service secrets. It is not correct for structured relational PHI — you cannot store name + DOB + address + phone as separate queryable fields with foreign keys and firm-scoped RLS using `vault.secrets`. The app-level AES-256-GCM approach in Layer 2 is what Supabase recommends for structured PHI workloads. Additionally, Vault requires disabling statement logging to prevent secrets appearing in logs — acceptable for API keys, unacceptable for a year-spanning case audit trail.

**Phase 1B Vault task:** Insert fax vendor API key and DocuSeal webhook secret into Supabase Vault via SQL function with `SECURITY DEFINER`.

**Why this is the first deliverable:** Every subsequent operation in Phase 1B passes client PII through the system. If encryption is not working before case initialization is built, client PII could be stored unencrypted in a test run and never caught.

**Encryption mechanism: app-level AES-256-GCM (not pgcrypto)**

The original ADR spec called for pgcrypto's `pgp_sym_encrypt`. The implementation uses app-level AES-256-GCM via Python's `cryptography` library. Keep the app-level approach — it is correct and superior:

- AES-256-GCM is a stronger cipher mode than pgp_sym_encrypt (which uses AES-256-CFB by default)
- The encryption key lives in Fly.io secrets (`PHI_ENCRYPTION_KEY`), never in the database or application code
- The test suite works against SQLite — pgcrypto requires a running PostgreSQL instance with the extension enabled
- The abstraction is cleaner — encryption is a service concern, not a database concern

**Two-schema pattern (same Supabase project):**

```
trace schema        — operational data, no raw PII
trace_phi schema    — PHI store, column-level AES-256-GCM encryption

trace.cases         — contains client_token (UUID), never raw client name/DOB
trace_phi.clients   — contains encrypted_name, encrypted_dob, encrypted_address
```

```python
# phi_service.py
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os, base64

PHI_KEY = base64.b64decode(os.environ["PHI_ENCRYPTION_KEY"])  # 32 bytes, from Fly.io secrets

def encrypt_phi(plaintext: str) -> str:
    """AES-256-GCM. Returns base64-encoded ciphertext + nonce."""
    aesgcm = AESGCM(PHI_KEY)
    nonce = os.urandom(12)  # 96-bit nonce, unique per encryption
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()

def decrypt_phi(encrypted: str) -> str:
    """Decrypts base64-encoded ciphertext + nonce."""
    data = base64.b64decode(encrypted)
    nonce, ciphertext = data[:12], data[12:]
    aesgcm = AESGCM(PHI_KEY)
    return aesgcm.decrypt(nonce, ciphertext, None).decode()
```

**Two-schema pattern (updated from separate project to same project with schemas):**

Per agent gap analysis: HIPAA add-on applies at the Supabase organization level, not per-project. Cost and compliance scope are identical whether TRACE uses a separate project or a separate schema in the existing project. The schema approach is cleaner for RLS and permission scoping.

```sql
-- Run once on existing Supabase project
CREATE SCHEMA IF NOT EXISTS trace;
CREATE SCHEMA IF NOT EXISTS trace_phi;

-- RLS on all trace tables
ALTER TABLE trace.cases ENABLE ROW LEVEL SECURITY;
-- ... (all trace.* tables)

-- RLS policy — firm_id from Clerk JWT claim
CREATE POLICY firm_isolation ON trace.cases
    USING (firm_id = (auth.jwt()->>'firm_id')::uuid);
```

**Test that must pass before anything else:**

```python
async def test_phi_never_in_operational_db(db_session, phi_db_session):
    known_name = "Jane Testclientphileak"
    
    case = await case_service.initialize_case(
        client_data=ClientData(name=known_name, dob="1985-04-12", ...),
        ...
    )
    
    # Search all operational tables — PHI must not appear in any of them
    for table in ["cases", "providers", "documents", 
                  "chronology_entries", "event_nodes", "audit_log"]:
        result = await db_session.execute(
            text(f"SELECT * FROM trace.{table} WHERE "
                 f"cast({table}::text as text) ILIKE :name"),
            {"name": f"%{known_name}%"}
        )
        rows = result.fetchall()
        assert len(rows) == 0, (
            f"PHI '{known_name}' found in trace.{table}. "
            f"PHI must never appear in the operational database."
        )
```

This test must stay in the suite permanently. If it ever fails, stop the build.

---

## 4. Case Initialization Endpoint

Full spec in Technical Implementation Spec §4.2. Key decisions for Phase 1B:

**Case stage on creation is PENDING_SIGNATURE, not INITIALIZATION.**

The case does not move to INITIALIZATION until DocuSeal confirms the client has signed. This is enforced at the database level — the `valid_stage` constraint lists PENDING_SIGNATURE as a valid value and the default.

```python
# On case creation
case.case_stage = "PENDING_SIGNATURE"  # NOT "INITIALIZATION"

# After DocuSeal webhook fires with signing.completed
case.case_stage = "INITIALIZATION"
case.hipaa_auth_status = "SIGNED"
case.signing_completed_at = webhook_payload["completed_at"]
```

**INTAKE integration — event subscription not synchronous POST:**

Per ADR-001 Decision #19, TRACE subscribes to the INTAKE outbox event (`case.created`) rather than receiving a synchronous POST from INTAKE. The implementation in Phase 1B:

```python
# Background worker — subscribes to INTAKE event queue
# Implementation detail: Supabase Realtime subscription or polling
# depending on what INTAKE outbox mechanism uses
async def handle_intake_case_created(event: IntakeCaseCreatedEvent):
    """
    Called when INTAKE marks a lead as retainer-signed.
    Decoupled from INTAKE — INTAKE does not wait for this to complete.
    """
    assert_production_for_phi()  # always first line in any PHI-adjacent function
    
    await case_service.initialize_case(
        intake_record_id=event.intake_record_id,
        client_data=event.client_data,
        incident_date=event.incident_date,
        jurisdiction_state=event.jurisdiction_state,
        firm_id=event.firm_id,
    )
```

**What the endpoint returns:**

```json
{
    "case_id": "a3f8e2b1-...",
    "case_stage": "PENDING_SIGNATURE",
    "sol_deadline": "2028-03-15",
    "sol_urgency": "Standard",
    "sol_days_remaining": 612,
    "sol_disclaimer": "This calculation is based on the standard personal injury statute of limitations for the indicated state and incident date. Tolling provisions, discovery rules, government entity notice requirements, and other state-specific exceptions may apply. The attorney is responsible for confirming the applicable deadline before relying on this calculation for any purpose.",
    "signing_status": "NOT_YET_SENT"
}
```

---

## 5. SOL Calculation

Runs synchronously inside case initialization. Returns before the response is sent. The 50-state table is in Spec §5.4 — use it exactly as specified.

**Three things the SOL display must do without exception:**

1. Show the deadline date in a format a non-technical person reads immediately — "March 15, 2028 — 612 days from today" not "2028-03-15T00:00:00Z"
2. Show the urgency label with color coding (Standard/grey, Monitor/blue, Urgent/amber, Critical/red with pulse)
3. Show the disclaimer text in full, every time, non-dismissible

**The disclaimer is not a tooltip or a collapsed section.** It is displayed inline under the deadline date. Always. An attorney who misses a SOL deadline because they dismissed the disclaimer and relied on TRACE's calculation is a malpractice case that traces back to a UX decision. Do not make that decision.

**Labeling: "Standard SOL Estimate" — not "SOL Deadline."**

The UI must use "Standard SOL Estimate" to reflect that this calculation does not account for tolling, discovery rules, government-entity notice, or state-specific exceptions. The attorney confirmation is required before relying on the calculation.

**Attorney confirmation fields on Case model (store now, UI in Phase 1E):**

```sql
ALTER TABLE trace.cases
  ADD COLUMN sol_attorney_confirmed_at TIMESTAMPTZ,
  ADD COLUMN sol_attorney_confirmed_by UUID,
  ADD COLUMN sol_confirmation_note TEXT;
```

These fields exist on the model in Phase 1B so the confirmation UI in Phase 1E has the data model to write to. Set null on case initialization — filled when attorney clicks "Confirm deadline reviewed" in a later phase.

**SOL calculation edge cases to test explicitly:**

```python
def test_sol_edge_cases():
    # Standard cases
    assert calculate_sol("CA", date(2024, 1, 15)).urgency == "Standard"  # 2 years out
    
    # Urgency threshold transitions
    assert calculate_sol("TX", date(2024, 1, 15)).urgency == "Monitor"   # approaching
    assert calculate_sol("FL", date(2023, 12, 1)).urgency == "Urgent"    # <90 days
    assert calculate_sol("NY", date(2023, 11, 1)).urgency == "Critical"  # <30 days
    
    # Future incident date should fail
    with pytest.raises(ValidationError):
        calculate_sol("CA", date(2030, 1, 1))
    
    # Unknown state code should fail loudly, not silently return None
    with pytest.raises(ValueError, match="State not found in SOL table"):
        calculate_sol("XX", date(2024, 1, 1))
    
    # SOL table version must be present in the response
    result = calculate_sol("CA", date(2024, 1, 15))
    assert result.table_version is not None  # traceability for attorney deposition
```

---

## 6. DocuSeal SigningService

Full pattern in Technical Implementation Spec §4.0. Phase 1B builds two methods: `send_signing_package()` and `handle_signing_webhook()`.

**Pre-conditions before building:**

- DocuSeal is deployed on Fly.io (Phase 1A checklist item)
- Firm templates are uploaded (retainer, fee agreement, HIPAA auth)
- Attorney signature field is pre-configured in templates
- `DOCUSEAL_API_URL`, `DOCUSEAL_API_TOKEN`, `DOCUSEAL_WEBHOOK_SECRET` are in Fly.io secrets

**The attorney experience this produces:**

Attorney marks a lead as retainer-signed in INTAKE → TRACE initializes the case → within 2 minutes the client receives:

*"[Firm Name] is ready to represent you. Please review and sign your documents here: [link]. Takes about 3 minutes on your phone. Questions? Call [attorney phone]."*

Client taps link → signs with finger → attorney portal shows: "Client has signed. Provider list is being prepared."

The attorney did not send an email, did not prepare a document, did not follow up. The case started the same day as the intake call.

**Webhook verification is non-negotiable:**

```python
async def _verify_webhook_signature(self, request: Request) -> None:
    """
    Every DocuSeal webhook must be verified before processing.
    A spoofed signing-complete webhook could advance a case
    without the client actually signing — this is a HIPAA
    and professional responsibility failure.

    Verify the RAW request body bytes, not reserialized JSON.
    json.dumps() reserialization can fail if the received payload's
    byte order, whitespace, or encoding differs from your format.
    Parse JSON only AFTER signature verification passes.
    """
    import hmac, hashlib

    raw_body = await request.body()
    signature = request.headers.get("X-Docuseal-Signature", "")

    expected = hmac.new(
        os.environ["DOCUSEAL_WEBHOOK_SECRET"].encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        logger.warning(
            "DocuSeal webhook signature verification failed",
            extra={"signature_received": signature[:8] + "..."}
        )
        raise WebhookSignatureError("Invalid webhook signature")

    # Only parse JSON after signature passes
    payload = json.loads(raw_body)


async def handle_signing_webhook(self, request: Request) -> None:
    """Process DocuSeal signing-complete webhook with replay protection."""
    await self._verify_webhook_signature(request)

    payload = json.loads(await request.body())
    docuseal_event_id = payload["event_id"]
    docuseal_submission_id = payload["submission_id"]

    # Replay protection: if we've already processed this event, return 200
    # without processing again. docuseal_submission_id is unique per signing
    # package. A second webhook for the same submission is silently accepted.
    existing = await self._lookup_submission(docuseal_submission_id)
    if existing and existing.signing_status == "COMPLETED":
        return  # idempotent — already processed

    # Download signed PDF and store
    # ... remainder of webhook processing
```

**Reminder workflow built in Phase 1B:**

If the client has not signed within 24 hours, TRACE sends an automated reminder via DocuSeal API. At 48 hours, the attorney receives a portal notification: "Client has not yet signed. Case is in PENDING_SIGNATURE stage." The attorney can resend the link with one click.

```python
# Background job — runs every hour, checks for unsigned packages
async def check_signing_reminders():
    unsigned_cases = await db.execute(
        select(cases)
        .where(cases.c.case_stage == "PENDING_SIGNATURE")
        .where(cases.c.hipaa_auth_status == "SENT")
    )
    
    for case in unsigned_cases:
        hours_since_sent = (now() - case.signing_sent_at).total_seconds() / 3600
        
        if hours_since_sent >= 24 and not case.reminder_sent:
            await docuseal_service.resend_reminder(case.docuseal_submission_id)
            await db.mark_reminder_sent(case.case_id)
            
        if hours_since_sent >= 48:
            await notify_portal(
                firm_id=case.firm_id,
                case_id=case.case_id,
                message="Client has not yet signed. "
                        "You can resend the signing link from the case detail page."
            )
```

---

## 7. NPI Registry Integration and Provider Extraction Skeleton

Per ADR-001 Decision #18, TRACE reuses INTAKE's jurisdiction JSON files rather than building a parallel SOL lookup. For provider extraction, Phase 1B builds the NPI Registry integration but uses a stub for OpenMed NER — real NLP extraction lands in Phase 1C.

**NPI Registry API calls:**

```python
NPI_REGISTRY_BASE = "https://npiregistry.cms.hhs.gov/api/"

async def lookup_provider_npi(
    provider_name: str,
    state: str,
    specialty: str | None = None
) -> list[NpiResult]:
    """
    Queries CMS NPI Registry. No PHI transmitted — only provider name + state.
    Government API, no BAA needed.
    Rate limit: 20 requests/second per IP. Apply exponential backoff.
    """
    params = {
        "version": "2.1",
        "name": provider_name,
        "state": state,
        "limit": 5,  # return top 5 candidates for attorney selection
    }
    if specialty:
        params["taxonomy_description"] = specialty
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(NPI_REGISTRY_BASE, params=params)
        response.raise_for_status()
    
    results = response.json().get("results", [])
    return [
        NpiResult(
            npi=r["number"],
            name=r["basic"].get("organization_name") or 
                 f"{r['basic'].get('first_name', '')} {r['basic'].get('last_name', '')}".strip(),
            fax=extract_fax(r.get("addresses", [])),
            address=extract_address(r.get("addresses", [])),
            specialty=extract_specialty(r.get("taxonomies", [])),
        )
        for r in results
    ]
```

**Test against 20 real providers — use these:**

Test the NPI lookup against real, publicly listed providers so the integration is proven against actual API responses before Phase 1C depends on it. Use publicly listed hospitals and medical groups in California, Texas, and Florida — the top three early access markets. No PHI involved — NPI Registry data is public.

```
Cedars-Sinai Medical Center (Los Angeles, CA)
Ronald Reagan UCLA Medical Center (Los Angeles, CA)  
Houston Methodist Hospital (Houston, TX)
Memorial Hermann (Houston, TX)
Jackson Memorial Hospital (Miami, FL)
AdventHealth Orlando (Orlando, FL)
... (14 more from target markets)
```

**Provider confidence taxonomy (per ADR-001 §24.2):**

The old HIGH/MEDIUM/LOW is replaced with attorney-actionable labels:

| NPI Result | Confidence Label | What attorney sees |
|-----------|-----------------|-------------------|
| Single exact name + state match | **Confirmed** | Auto-selected, attorney can change |
| Strong candidate, needs verification | **Likely Match** | Pre-selected with "Please verify" label |
| Multiple candidates | **Needs Client Confirmation** | Dropdown showing top 3 matches |
| Staff must select from multiple | **Needs Staff Review** | Flagged for manual selection |
| No NPI match | **Do Not Request** | Shown but excluded from fax batch |

**Provider extraction skeleton — OpenMed NER stub for Phase 1B:**

In Phase 1B, OpenMed NER is not yet wired into the pipeline (that is Phase 1C). The provider extraction job uses a simple stub that reads provider references from the Benjamin intake record JSON's structured fields — not from free-text NLP. This is sufficient to prove the pipeline flow and the NPI integration.

```python
async def extract_providers_from_intake(intake_record: dict) -> list[ProviderCandidate]:
    """
    Phase 1B stub — reads structured provider fields from Benjamin intake JSON.
    Phase 1C replaces this with OpenMed NER on the full transcript text.
    """
    candidates = []
    
    # Benjamin's structured intake record includes provider_references field
    for ref in intake_record.get("provider_references", []):
        candidates.append(ProviderCandidate(
            name=ref.get("name"),
            facility=ref.get("facility"),
            specialty=ref.get("specialty"),
            location=ref.get("location"),
            confidence="LIKELY_MATCH",  # stub confidence — Phase 1C upgrades this
            source="INTAKE_STRUCTURED_FIELD",
        ))
    
    # If no structured references, fall back to a single "Unknown Provider" 
    # for attorney to fill in manually
    if not candidates:
        candidates.append(ProviderCandidate(
            name=None,
            confidence="DO_NOT_REQUEST",
            note="No providers identified in intake record. Please add providers manually.",
        ))
    
    return candidates
```

---

## 8. Portal — Case List View

Phase 1B delivers the first attorney-visible UI: the TRACE case list. This is embedded in the existing portal, not a standalone page.

**What the case list shows:**

```
┌──────────────────────────────────────────────────────────────────────┐
│ TRACE Cases                                              [+ New Case] │
├───────────────┬────────────────────┬──────────────┬──────────────────┤
│ Client        │ Stage              │ SOL          │ Days in Stage    │
├───────────────┼────────────────────┼──────────────┼──────────────────┤
│ Matter #1042  │ ⏳ Awaiting Sig.   │ 612 days     │ 1 day            │
│ Matter #1039  │ ✅ Providers Ready │ 88 days ⚠️   │ 2 days           │
│ Matter #1031  │ 📄 Records In      │ 201 days     │ 8 days           │
│ Matter #1028  │ ✅ Demand Ready    │ 44 days 🔴   │ —                │
└───────────────┴────────────────────┴──────────────┴──────────────────┘
```

**Important: client identity in the case list.**

The attorney sees "Matter #1042" not the client's name in the list view. Client name is revealed only when the attorney clicks through to the case detail. This is a deliberate PHI minimization choice — if the attorney's laptop screen is visible in a coffee shop or courthouse, the case list does not expose client names.

The matter number is opaque — the attorney can configure a human-readable matter reference (e.g., "Smith MVA 2026") in the case settings, but the default is the opaque matter number.

**Stage labels the attorney sees (plain English, Phase 1B only):**

| Database value | Portal display |
|----------------|---------------|
| PENDING_SIGNATURE | ⏳ Awaiting Client Signature |
| INITIALIZATION | 🔄 Preparing Provider List |
| RETRIEVAL | 📨 Requesting Records |
| PROCESSING | ⚙️ Processing Records |
| CHRONOLOGY_READY | Hidden in Phase 1B — Phase 1D |
| ATTORNEY_REVIEW | Hidden in Phase 1B — Phase 1E |
| DEMAND_READY | Hidden in Phase 1B — Phase 1E |

Future stages must not appear in the Phase 1B case list. Showing "Demand Ready" before records, bills, liens, treatment gaps, chronology review, and attorney sign-off exist is misleading to the early access attorney.

**Add "Next Action" column:**

The attorney cares more about what to do next than the stage name:

| Stage | Next Action |
|-------|------------|
| PENDING_SIGNATURE | Waiting on client signature. [Resend link] |
| INITIALIZATION | Provider list being prepared — check back soon |
| RETRIEVAL | Review provider candidates

---

## 9. Phase 1B Acceptance Criteria

All of the following must pass before Phase 1C begins. No exceptions.

### 9.1 PHI Encryption

- [ ] `test_phi_never_in_operational_db` passes — searches all operational tables for test client name, asserts zero results
- [ ] Direct SELECT on `clients` table returns encrypted bytea, not plaintext
- [ ] Case record contains `client_token` UUID, no name, no DOB, no address
- [ ] `assert_production_for_phi()` raises in development environment — confirmed by test

### 9.2 Case Initialization

- [ ] POST to case initialization endpoint with test intake record creates a case
- [ ] Case starts in `PENDING_SIGNATURE` stage (not INITIALIZATION)
- [ ] `hipaa_auth_status` starts as `PENDING` (not SIGNED)
- [ ] SOL deadline calculated correctly for all target states (CA, TX, FL, NY, IL)
- [ ] SOL disclaimer text present in every response — exact text matches spec §5.1.4
- [ ] Duplicate intake record IDs return 409 with existing case_id (not 500)
- [ ] Future incident date returns 422 with plain-English validation error
- [ ] Invalid state code returns 422 with plain-English validation error

### 9.3 DocuSeal Signing Flow

- [ ] `send_signing_package()` calls DocuSeal API with correct payload
- [ ] Client contact info retrieved from PHI store, used, then deleted from memory — confirmed by absence in any log output
- [ ] `signed_documents` record created with `signing_status = SENT`
- [ ] Case `hipaa_auth_status` updates to `SENT`
- [ ] Webhook endpoint rejects requests with invalid signature — returns 400
- [ ] Valid webhook advances case to `INITIALIZATION` stage
- [ ] Valid webhook sets `hipaa_auth_status = SIGNED`
- [ ] Signed PDF stored in `signed-documents` Supabase Storage bucket
- [ ] Attorney portal notification fires after successful webhook
- [ ] 24-hour reminder job sends reminder to client if not signed
- [ ] 48-hour notification reaches attorney portal if client not signed

### 9.4 NPI Registry

- [ ] 20 real provider lookups return correct results (use the test provider list from §7)
- [ ] Single exact match → Confirmed confidence label
- [ ] Multiple matches → Needs Client Confirmation with top 3 shown
- [ ] No match → Do Not Request with note
- [ ] Rate limiting handled — exponential backoff on 429 responses
- [ ] CMS NPI Registry unavailability handled gracefully — does not crash the job

### 9.5 Provider Extraction Skeleton

- [ ] `extract_providers_from_intake()` stub reads structured provider fields from intake JSON
- [ ] Produces provider records with correct confidence labels
- [ ] NPI lookup runs on each candidate
- [ ] Providers written to database after client signs (not before)
- [ ] Zero providers found → single "Unknown Provider" record with note, attorney notified

### 9.6 Portal Case List

- [ ] Case list shows all TRACE cases for the authenticated firm
- [ ] Client name NOT shown in list view — matter number only
- [ ] Stage labels are plain English (not database values)
- [ ] SOL urgency displayed with correct color coding
- [ ] Cases in PENDING_SIGNATURE show "Awaiting Client Signature"
- [ ] Firm A cases not visible to firm B — confirmed by test

### 9.7 Firm Isolation (carry-forward from Phase 1A)

- [ ] Firm A cannot GET firm B's case by case_id — returns 403 or 404
- [ ] Firm A cannot see firm B's cases in the case list
- [ ] All database queries include firm_id filter — confirmed by grep across all service files

---

## 10. Decisions Made in Phase 1B (No Agent Discretion)

These are the architecture decisions that must not be varied:

| Decision | What it is | Why locked |
|----------|-----------|------------|
| Case starts in PENDING_SIGNATURE | Initial stage | Nothing downstream starts until client signs. INITIALIZATION means the client has signed and the attorney has their HIPAA auth. |
| PHI store is separate from operational DB | Two database connections | If operational DB is compromised, client PII is not exposed. This is the core of the PHI protection architecture. |
| DocuSeal webhook must be HMAC-verified before processing | Security | A spoofed webhook could advance a case without a real signature. |
| Client contact retrieved just-in-time for DocuSeal call | PHI minimization | Client name/email/phone should exist in memory for the minimum possible duration. Not cached, not stored in any intermediate state. |
| Client name NOT shown in case list | PHI minimization | The case list is visible on the attorney's screen in public. Matter numbers only. |
| SOL disclaimer non-dismissible | Liability | An attorney who misses a SOL based on TRACE's calculation without reading the disclaimer is a malpractice case. |
| Provider extraction runs after signing, not before | Workflow gate | Sending a HIPAA-authorized fax request before the client has signed the HIPAA authorization is a HIPAA violation. |

---

## 11. What Phase 1B Does NOT Build

Explicitly out of scope. Do not start these. They are Phase 1C.

- OpenMed NER integration (provider extraction uses stub)
- Provider confirmation checklist UI (attorneys cannot yet confirm providers)
- Fax request generation (fax vendor decision gate is Phase 1B prerequisite but fax API is Phase 1C)
- Any document processing (OCR, de-identification, chronology)
- Client upload link endpoint (documented, not yet implemented)
- Any attorney QA interface

If you find yourself building any of these in Phase 1B, stop and check whether Phase 1B acceptance criteria are complete.

---

## 12. Fax Vendor Decision Gate (Phase 1B Prerequisite for Phase 1C)

Phase 1B must complete the fax vendor selection before Phase 1C can begin. This is not a build task — it is a procurement task. The outcome is a decision recorded in writing and a sandbox API credential configured.

**What to do:**

1. Get a real enterprise quote from Fax.Plus — include compliance riders, volume overages above 4,000 pages/month, and any multi-user fees
2. Get a real enterprise quote from Documo — same scope
3. Apply the switch rule: if Fax.Plus total annual cost > 2× Documo at projected volume → select Documo
4. Record the decision with both actual quotes in the vendor evaluation doc
5. Set `FAX_PROVIDER` environment variable in Fly.io secrets pointing to the selected vendor's sandbox credentials
6. BAA execution is production-only — do not execute during Phase 1B

The Phase 1C fax transmission build depends on knowing which vendor's API to build against. This decision cannot be made during Phase 1C — it must be made before it starts.

---

*ADR-002 — July 2026. All decisions in §10 are locked for Phase 1B. Agent discretion applies only to implementation details within the constraints stated. Flag any deviations in PR description with explicit justification.*

---

## 13. Pre-Phase-1B Fixes (Required Before Phase 1B Build Begins)

Six issues found in the Phase 1A delivery during gap analysis. All must be fixed and tests passing before Phase 1B acceptance criteria begin. Listed in fix order — each depends on the previous.

### Fix 1 — Schema migration (architectural, blocking)

Migrate TRACE tables from `public` schema to `trace` and `trace_phi` schemas in the existing Supabase project.

```sql
CREATE SCHEMA IF NOT EXISTS trace;
CREATE SCHEMA IF NOT EXISTS trace_phi;
-- Move or recreate all TRACE tables under trace.*
-- Enable RLS on all trace.* tables
-- Create firm_id RLS policies on all trace.* tables
```

Update all Alembic migrations to use schema-qualified table names. Update all SQLAlchemy models to include `schema=` in `__table_args__`. Confirm all 36 existing tests pass after schema migration.

### Fix 2 — case_stage bug (red, blocking)

`routes/cases.py:115` hardcodes `case_stage = "INITIALIZATION"`, overriding the database default `PENDING_SIGNATURE`. Remove the override. The database default is correct. Case advances to `INITIALIZATION` only when the DocuSeal webhook fires with `signing.completed` — nowhere else.

```python
# WRONG — remove this line
case.case_stage = "INITIALIZATION"

# RIGHT — the DB default is PENDING_SIGNATURE, let it be
# case_stage is set to INITIALIZATION only in handle_signing_webhook()
```

Required test:
```python
def test_new_case_starts_in_pending_signature():
    case = create_test_case(...)
    assert case.case_stage == "PENDING_SIGNATURE"
    assert case.hipaa_auth_status == "PENDING"
```

### Fix 3 — signing_sent_at field missing (red, blocking)

The reminder workflow in §6 references `case.signing_sent_at` to calculate 24h/48h elapsed. The field does not exist. Without it the reminder job cannot run.

```sql
ALTER TABLE trace.cases ADD COLUMN signing_sent_at TIMESTAMPTZ;
```

Set `signing_sent_at = now()` in `send_signing_package()` when DocuSeal call succeeds. Also add to SOL versioning (Fix 6 below):

```sql
ALTER TABLE trace.cases ADD COLUMN sol_table_version VARCHAR(20);
```

### Fix 4 — PHI leakage test missing (red, blocking)

Write `test_phi_never_in_operational_db` per §3. This test is the single most important test in the entire suite. It must exist before any Phase 1B code is merged. It must never be deleted.

### Fix 5 — NPI rate limiting and confidence taxonomy (orange, blocking for NPI work)

Add exponential backoff to NPI Registry calls (max 4 attempts, 2^n second wait on 429 or timeout). Add confidence label assignment per the taxonomy in §7 — single match → Confirmed, 2–3 matches → Needs Client Confirmation, 4+ matches → Needs Staff Review, zero matches → Do Not Request.

### Fix 6 — SOL table version not in API response (orange, blocking for SOL correctness)

`SOL_TABLE_VERSION` is a module-level constant but not surfaced in the API response or stored in the case record. Add it to both:

```python
SOL_TABLE_VERSION = "2026-07-01"  # date the SOL table was last reviewed by an attorney

# In SolResult:
return SolResult(
    deadline=sol_deadline,
    days_remaining=days_remaining,
    urgency=urgency,
    table_version=SOL_TABLE_VERSION,  # in API response
    disclaimer=SOL_DISCLAIMER,
)
```

```sql
-- Store with the case so the table version is part of the immutable case record
ALTER TABLE trace.cases ADD COLUMN sol_table_version VARCHAR(20);
-- Set when SOL is calculated during case initialization
```

### Fix sequence summary

```
Fix 1 (schema)  → Fix 2 (stage bug) → Fix 3 (fields) → Fix 4 (PHI test)
     → Fix 5 (NPI) → Fix 6 (SOL version)
     → All 36 existing tests still passing
     → Phase 1B build begins
```

---

*ADR-002 updated July 2026 — §3 reflects app-level AES-256-GCM (not pgcrypto), same Supabase project with trace/trace_phi schemas (not separate project). §13 added with six pre-Phase-1B fixes from agent gap analysis.*
