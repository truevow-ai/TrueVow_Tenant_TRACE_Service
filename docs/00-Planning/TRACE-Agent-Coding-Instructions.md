# TRACE — Coding Agent Operating Instructions
## Read This Before Writing a Single Line of Code
**Version:** 1.0  
**Date:** July 2026  
**Classification:** Engineering — Required Reading  
**Prerequisite:** TRACE PRD v0.5, TRACE Technical Implementation Spec v1.0, ADR-001

---

## The One Thing That Matters Most

The attorney using TRACE is a solo PI lawyer who is afraid of technology, has never heard of an API, and is already overwhelmed running a law firm alone. Every decision you make — every variable name, every error message, every UI state, every loading indicator — must be made with that person in mind.

Not you. Not the next engineer. That attorney.

If that attorney opens the portal and sees a spinner with no label, you have failed. If they get a 500 error with a stack trace, you have failed. If they have to click more than three times to do the most common thing they do, you have failed. If they call their nephew for help with something they should be able to do alone, you have failed.

Everything in this document serves that principle. Every rule below exists because breaking it eventually hurts that attorney.

---

## Part 1 — Build Philosophy

### 1.1 Boring is a Feature

Do not use a new framework because it's interesting. Do not use a pattern because you read about it last week. Do not abstract something because you might need to later. Use the oldest, most boring, most documented solution that works. Boring code is code that works in three years without anyone touching it.

**The question to ask before every decision:** *Has this been done 10,000 times before and does it have a Stack Overflow answer from 2018?* If yes, do it that way.

### 1.2 Simple is Not Simplistic

Simple code is the hardest code to write. It requires understanding the problem deeply enough to solve it without cleverness. Simple code has:
- One function that does one thing
- Variable names that say what they contain
- Functions that are short enough to see on one screen
- No nested ternaries, no lambda chains, no magic
- Comments that explain *why*, not *what*

Junior developer test: can a developer who has never seen this codebase understand what a function does in 30 seconds? If not, rewrite it.

### 1.3 No Premature Abstractions

Do not build a system that could handle future requirements that don't exist yet. Build the thing that is needed today. The abstractions that exist in the spec (LLMService, OCRService, StorageService) exist because they solve a real concrete problem — vendor switching without code changes. That is a known requirement.

Everything else: build the simplest thing that works. Extract and abstract only when you feel the pain of not having done so.

**The rule:** Write the code twice before you abstract it. If you find yourself writing the third copy, abstract it then. Not before.

### 1.4 The Attorney is Always Right About Their Experience

If the attorney would find something confusing, it is confusing. The fact that something is technically correct does not make it the right user experience. When in doubt about a UI decision, ask: *what would a non-technical person expect to happen here?* Build that.

---

## Part 2 — Code Quality Rules (Non-Negotiable)

### 2.1 Every Function Does One Thing

A function that does two things is two functions. Name it accordingly.

```python
# Wrong — this function does two things
def process_document_and_extract_entities(doc_bytes, case_id):
    ...

# Right — two functions, two responsibilities
def run_ocr(doc_bytes: bytes) -> OcrResult:
    ...

def extract_clinical_entities(ocr_text: str) -> list[ClinicalEntity]:
    ...
```

The maximum acceptable function length is what fits on one screen (approximately 40–50 lines including docstring). If it is longer, it is doing too many things.

### 2.2 Name Everything Like a Sentence

Code is read more than it is written. Name things so the code reads like a sentence.

```python
# Wrong — abbreviations, mystery variables
def proc_doc(d, cid):
    res = ocr.run(d)
    if res.conf < THRESH:
        ...

# Right — reads like a sentence
def process_incoming_document(document_bytes: bytes, case_id: UUID) -> ProcessedDocument:
    ocr_result = run_ocr_pipeline(document_bytes)
    if ocr_result.confidence_below_threshold:
        return flag_for_manual_review(ocr_result, case_id)
    ...
```

Never use single-letter variables outside of loop counters. Never use abbreviations unless the full word is longer than 15 characters. Never use `data`, `result`, `info`, `obj`, `thing`, or `stuff` as variable names.

### 2.3 Explicit Over Implicit

Never rely on Python's implicit behavior when explicit behavior is available. Never use positional arguments when keyword arguments are available. Never use `*args` or `**kwargs` in business logic functions. Never use `**dict_unpacking` when you can name the fields explicitly.

```python
# Wrong — implicit, fragile
create_case(*case_data.values())

# Right — explicit, stable, refactor-safe
create_case(
    case_id=case_data.case_id,
    client_token=case_data.client_token,
    incident_date=case_data.incident_date,
    jurisdiction_state=case_data.jurisdiction_state,
)
```

### 2.4 Type Everything

Every function signature must have type hints. Every model field must have a type. Every return value must have a return type annotation. Untyped code is a bug waiting to happen.

```python
# Wrong — no types
def get_case(case_id, firm_id):
    ...

# Right — fully typed
async def get_case(case_id: UUID, firm_id: UUID) -> Case | None:
    ...
```

Run `mypy` on every commit. Fail the CI pipeline if mypy reports errors. Type hints are not optional documentation — they are part of the code.

### 2.5 Handle Every Error Path

Every function that can fail must handle its failure. Every API endpoint must return a meaningful error response. No bare `except:` blocks. No swallowed exceptions. No silent failures.

```python
# Wrong — swallowed exception
try:
    result = fax_service.transmit(request)
except Exception:
    pass

# Wrong — bare except
try:
    result = fax_service.transmit(request)
except:
    logger.error("fax failed")

# Right — explicit exception type, meaningful response, never leaks internals
try:
    result = fax_service.transmit(request)
except FaxTransmissionError as e:
    logger.error(
        "Fax transmission failed",
        extra={"case_id": str(case_id), "provider_id": str(provider_id), "error_code": e.code}
        # Note: never log provider fax number or client data here
    )
    raise CaseFaxError(
        case_id=case_id,
        provider_id=provider_id,
        message="Record request could not be sent. Please try again or contact support.",
    ) from e
```

The attorney never sees an internal error message. They see a plain-English message and a support contact. Always.

### 2.6 Never Repeat Yourself — But Not at the Cost of Clarity

DRY (Don't Repeat Yourself) is a guideline, not a religion. If extracting a shared function makes the code harder to follow, the duplication is better than the abstraction. Use judgment.

The test: would removing the duplication require a reader to jump to another file to understand what is happening? If yes, leave the duplication and add a comment pointing to the other location.

### 2.7 Comments Explain Why, Not What

The code says what it does. The comment says why it does it.

```python
# Wrong — explains what (the code already says this)
# Increment the retry counter
retry_count += 1

# Right — explains why
# Fax.Plus rate-limits to 10 requests/second per account.
# We back off exponentially to avoid hitting the limit during
# bulk provider request transmission.
retry_count += 1
await asyncio.sleep(2 ** retry_count)
```

Comment anything that would make a developer say "why did they do it this way?" That question is the signal to add a comment.

### 2.8 Write the Test Before You Think You're Done

Every piece of business logic has a test before the PR is opened. Not after. Not "I'll add tests later." Before.

The test pyramid:
- Unit tests for every function with business logic
- Integration tests for every API endpoint
- At least one end-to-end test per user story (Story 1 through Story 6 in the PRD)

The 80% coverage minimum is a floor, not a target. Critical PHI handling code (OCR pipeline, de-identification, phi_map encryption) should be at 95%+. The demand-ready gate and all four checkpoint gates must have tests that confirm they block when they should block.

---

## Part 3 — Architecture Rules (Non-Negotiable)

### 3.1 One File Per Resource

The repo layout is defined in the spec. Follow it exactly. One FastAPI router file per resource — `cases.py`, `providers.py`, `documents.py`, `chronology.py`. No putting two resources in one file because they seem related.

```
/app/api/cases.py        # GET/POST/PATCH /cases
/app/api/providers.py    # GET/POST/PATCH/DELETE /cases/{id}/providers
/app/api/documents.py    # GET/POST /cases/{id}/documents
/app/api/chronology.py   # GET /cases/{id}/chronology
/app/api/flags.py        # GET/PATCH /cases/{id}/flags/{flag_id}
```

### 3.2 No Business Logic in Routers

FastAPI routers are for HTTP — request parsing, response formatting, authentication, and routing. Business logic goes in services. Database queries go in repositories or through SQLAlchemy models. No SQL in router files. No if/else business logic in router files.

```python
# Wrong — business logic in router
@router.post("/cases/{case_id}/providers/confirm")
async def confirm_providers(case_id: UUID, db: Session = Depends(get_db)):
    providers = db.query(Provider).filter(Provider.case_id == case_id).all()
    if not any(p.status == "CONFIRMED" for p in providers):
        raise HTTPException(400, "No providers confirmed")
    for provider in providers:
        if provider.status == "CONFIRMED":
            provider.status = "LOCKED"
    db.commit()
    ...

# Right — router delegates to service
@router.post("/cases/{case_id}/providers/confirm")
async def confirm_providers(
    case_id: UUID,
    current_firm: Firm = Depends(get_current_firm),
    provider_service: ProviderService = Depends(get_provider_service),
) -> ProviderConfirmationResponse:
    return await provider_service.confirm_and_lock_provider_list(
        case_id=case_id,
        firm_id=current_firm.id,
    )
```

### 3.3 The Service Layer Owns Business Logic

Every piece of business logic lives in a service class. Services take dependencies via constructor injection (not global imports). Services are testable without spinning up a database or HTTP server.

```python
class ProviderService:
    def __init__(
        self,
        db: AsyncSession,
        npi_client: NpiRegistryClient,
        audit_logger: AuditLogger,
    ):
        self._db = db
        self._npi = npi_client
        self._audit = audit_logger

    async def confirm_and_lock_provider_list(
        self,
        case_id: UUID,
        firm_id: UUID,
    ) -> ProviderConfirmationResult:
        # Business logic lives here, not in the router
        ...
```

### 3.4 Database Access is Explicit

No magic ORM queries. No lazy loading. Specify exactly what you are fetching and why. Use `selectinload` or `joinedload` explicitly when you need related records. Never let an N+1 query happen in production — the attorney's portal is slow enough without it.

```python
# Wrong — lazy loading, N+1 risk, magic
case = db.query(Case).get(case_id)
providers = case.providers  # triggers another query per case

# Right — explicit, predictable, one query
result = await db.execute(
    select(Case)
    .options(selectinload(Case.providers))
    .where(Case.id == case_id)
    .where(Case.firm_id == firm_id)  # ALWAYS scope to firm_id
)
case = result.scalar_one_or_none()
```

**Every single database query must include a `firm_id` filter.** No exceptions. This is the multi-tenant isolation guarantee. If you forget this on one query, one attorney can see another attorney's client data. That is a HIPAA breach. Build a base query helper that enforces firm scoping so it is physically impossible to forget:

```python
def scoped_case_query(firm_id: UUID):
    """Always use this as the base for any case query.
    Never query cases without firm scoping."""
    return select(Case).where(Case.firm_id == firm_id)
```

### 3.5 Migrations Are Permanent

Every database change is an Alembic migration. Never run raw SQL against the production database. Never edit a migration that has been applied to any environment. If you made a mistake in a migration, write a new migration that corrects it.

Migration files are named: `{version}_{brief_description}.py`. Example: `0001_create_cases_table.py`. The description must be readable by a human three years from now.

Every migration must have a `downgrade()` function that reverses it completely. Test the downgrade in development before the migration is merged.

### 3.6 Environment Variables are the Only Configuration

No hardcoded values in code except mathematical constants and string literals that are part of the domain logic (SOL disclaimer text, prohibited output strings). Every URL, every API key, every threshold that might change between environments goes in an environment variable.

Never commit a real `.env` file. The `.env.example` file in the repo root lists every variable with a description and a placeholder value. Keep it current — if you add a new env var, add it to `.env.example` in the same PR.

### 3.7 The PHI Guard is Not Optional

Every job that processes real PHI must call `assert_production_for_phi()` at the top. This is not a nice-to-have. This is the technical enforcement of the production-only PHI rule. If you skip this, a developer running the OCR pipeline locally against a real case file has just committed a HIPAA violation.

```python
# Every PHI-touching job starts with this:
from app.services.phi_guard import assert_production_for_phi

async def run_ocr_job(document_id: UUID) -> None:
    assert_production_for_phi()  # First line. Always.
    ...
```

---

## Part 4 — HIPAA Rules (Zero Tolerance)

### 4.1 PHI Never Appears in Logs

The log redaction filter (spec §8, ADR-001 §8) is applied at the root logger. But defense in depth means you also never write code that would log PHI even if the filter weren't there.

**Never log:**
- Client name, date of birth, address, phone number
- Any field from the `clients` table
- The contents of a medical record
- Any field from a fax transmission that includes client data
- The `phi_map` or any fragment of it
- Any exception message that might contain OCR output from a medical record

**Always log:**
- `case_id` (opaque UUID)
- `firm_id` (opaque UUID)
- `document_id` (opaque UUID)
- `provider_id` (opaque UUID)
- Error codes, not error messages containing PHI

### 4.2 PHI Never Appears in URLs

Every API endpoint that touches case data uses opaque UUIDs. Never include a client name, case name, or any human-readable identifier in a URL path or query parameter.

```
# Wrong — PHI in URL
GET /cases/john-smith-2024-accident/documents

# Right — opaque UUID
GET /cases/a3f8e2b1-4c7d-4e8f-9a0b-1c2d3e4f5a6b/documents
```

### 4.3 The phi_map Stays Encrypted

The phi_map — OpenMed's offset map linking redacted tokens to original PHI values — must be:
1. Encrypted with pgcrypto immediately after OpenMed de-identification completes
2. Zeroed in memory immediately after encryption write is confirmed
3. Never written to any log
4. Never included in any export
5. Never transmitted to SETTLE or any other system

The phi_map is accessed only for two purposes: re-identifying data for attorney portal display, and destruction when the case is purged. Every access to the phi_map is logged in audit_log.

### 4.4 Firm Isolation is Absolute

No attorney ever sees data belonging to another firm. This is enforced at three levels:
1. Database query level: every query includes `firm_id` filter
2. API level: every endpoint validates `firm_id` against the authenticated user's firm
3. Row-level security in Supabase: RLS policies on every table

All three must be in place before any case data is accessible via the API. Do not rely on any single layer. If one layer has a bug, the other two catch it.

---

## Part 5 — The Attorney Experience (This is the Product)

### 5.1 Error Messages are Written for a Non-Technical Person

The attorney sees a plain-English message in every error state. They never see:
- HTTP status codes
- Stack traces
- Internal error codes
- Database error messages
- JSON error objects
- The words "null", "undefined", "exception", "500", "timeout"

Every error message tells the attorney:
1. What happened (in plain English)
2. Whether it is temporary or permanent
3. What they can do about it

```python
# Wrong — technical
raise HTTPException(500, "Database connection pool exhausted")

# Wrong — vague
raise HTTPException(500, "Something went wrong")

# Right — human
return ErrorResponse(
    message="We couldn't save your changes right now. Please try again in a moment. If this keeps happening, contact us at support@truevow.law",
    is_temporary=True,
    support_contact="support@truevow.law",
)
```

### 5.2 Loading States are Informative

Every async operation that takes more than 200ms shows a loading indicator with a human-readable label. Not a spinner with no text. Not "Loading..." in every situation.

```
# Wrong — generic
"Loading..."

# Right — specific
"Benjamin is identifying providers from the intake record..."
"Sending record requests to 4 providers..."
"Building your treatment chronology..."
"Analyzing 247 pages for treatment gaps..."
```

The attorney should never wonder what the system is doing. They should never wonder if something is stuck. If an operation takes longer than 5 seconds, show a progress indicator or an estimated completion time.

### 5.3 Every Empty State Tells the Attorney What to Do Next

An empty state is not nothing. An empty state is an instruction.

```
# Wrong — empty provider list with no text

# Right — empty provider list with instruction
"No providers confirmed yet.
TRACE identified 3 providers from the intake record.
Review and confirm the list to begin requesting records."
[Review Provider List →]
```

Every empty state must:
1. Explain why it is empty
2. Tell the attorney what to do next
3. Give them a button or link to do it

### 5.4 Confirmations Prevent Irreversible Mistakes

Any action that cannot be undone requires a confirmation step. The confirmation must state exactly what will happen in plain English.

```
# Wrong confirmation
"Are you sure? [Yes] [No]"

# Right confirmation
"Send record requests to 4 providers?

Benjamin will send a HIPAA-compliant request to:
• Cedars-Sinai Emergency — fax (310) 123-4567
• Dr. Sarah Chen, Physical Therapy — fax (310) 987-6543
• Valley Chiropractic Center — fax (818) 555-1234
• Northridge Imaging — fax (818) 444-5678

Once sent, you cannot recall these requests.

[Send 4 Requests] [Go Back]"
```

The key details: who is being contacted, what is being sent, what happens after, and a clear way to go back.

### 5.5 The Demand-Ready Checklist is a Moment of Weight

When the attorney clicks "Mark Demand-Ready," they are certifying that a case file is ready for the most consequential step in the PI workflow. This is not a casual button click. The UX must communicate the weight of this action.

The demand-ready flow:
1. The "Mark Demand-Ready" button is visually locked (greyed, with a count of remaining items) until all PRIORITY flags are annotated
2. When the button becomes active, it is clearly highlighted — not just a standard button
3. Clicking it shows a full checklist (seven items per ADR-001 §24.8) with checkboxes the attorney explicitly confirms
4. Below the checklist: "By clicking 'Confirm Demand-Ready', I confirm I have reviewed this chronology and take responsibility for its use in this matter."
5. After confirmation: the status changes visibly, a timestamp is shown, and a confirmation email is sent to the attorney

The attorney should feel like they signed something. Because they did.

### 5.6 Notifications Are Helpful, Not Spammy

The attorney gets notified when something needs their attention. They do not get notified for system events that don't require action.

**Notify for (portal + SMS + email):**
- Provider list ready for review
- Provider non-response at day 25 (by name, not just "a provider")
- Chronology ready for QA review
- Demand-ready approval complete
- A provider responds after a long delay

**Notify for (portal only):**
- Individual record received
- OCR processing complete
- Flag detected (surface in portal, don't push to SMS)

**Never notify for:**
- System pipeline events
- Background job completions that don't require attorney action
- Status changes that are intermediate steps

Every notification message uses the attorney's name, the client matter name, and tells them exactly what to do next.

---

## Part 6 — Code Review Standards

### 6.1 The PR Description is Part of the Code

Every pull request must have:
- What changed (one paragraph, plain English)
- Why it changed (link to spec section, PRD section, or ADR)
- How to test it manually (step by step)
- Any risks or things to watch out for

A PR with "Fixed the thing" as a description is not mergeable.

### 6.2 The Four-Eyes Rule for PHI-Adjacent Code

Any code that:
- Touches the `clients` table or the phi_map
- Modifies the audit_log write path
- Changes any authentication or authorization logic
- Modifies the demand-ready gate or any checkpoint gate
- Changes how documents are stored or accessed in Supabase Storage

...must have explicit sign-off from a second reviewer before merge. Not just "approved" — a comment that says "reviewed PHI handling: [specific confirmation that it's correct]."

### 6.3 Database Migrations Require Extra Care

Before any migration is merged:
- `alembic upgrade head` has been run on a fresh database and succeeded
- `alembic downgrade -1` has been run and succeeded
- The resulting schema has been verified against the PRD §8.4 schema tables
- The migration has been run on a database with existing data (not just empty)

No migration is merged on a Friday.

### 6.4 No Dead Code

Do not leave commented-out code in the codebase. Do not leave unused imports. Do not leave TODO comments that are more than one sprint old. If something needs to be done, it is in a ticket. If it is in the code as a comment, it will never be done and it will confuse the next developer.

The one exception: `# AGENT CHOICE: [description] — flagged for review` comments defined in the spec. These are intentional and should be reviewed and resolved within the next sprint.

---

## Part 7 — Deployment Rules

### 7.1 Production is Sacred

Production is the environment where real attorneys interact with real case data. It is not a test environment. It is not a place to try things out.

The deployment pipeline:
1. Code merged to `main` → deploys to staging automatically
2. Staging runs full test suite → if tests pass, staging is live
3. Production deployment is manual and requires explicit sign-off
4. Every production deployment is logged with who deployed, when, and what changed

No one deploys to production on a Friday afternoon. No one deploys to production without having tested the change in staging.

### 7.2 Secrets Never Touch Git

`fly secrets set` for production secrets. `.env.local` for development. `.env.example` in git with placeholder values and descriptions. That is the complete secrets management system.

If a secret is ever accidentally committed to git:
1. Rotate the secret immediately (before anything else)
2. Remove it from git history using `git filter-branch` or `git filter-repo`
3. Force-push the cleaned history
4. Notify the team

### 7.3 Rollback Must Be Possible

Every deployment must be rollback-able. If a deployment breaks production, the rollback must be executable in under 5 minutes. Test the rollback procedure in staging before any significant deployment.

---

## Part 8 — The Simplicity Test

Before marking any piece of work complete, run it through these four questions:

**1. Would a developer joining the team today understand this code in 30 minutes without asking anyone?**
If no: simplify it or add comments until yes.

**2. Would the attorney experience be confusing to a non-technical person?**
If yes: redesign the UX until no.

**3. Is there any way this code could expose PHI — in a log, in a URL, in an error message, in a notification?**
If yes: fix it before merging.

**4. If this breaks at 2am on a Saturday with no engineers available, can the attorney continue working without data loss?**
If no: add graceful degradation, better error messages, or a support contact that can actually help.

---

## The Final Instruction

You are not building software. You are building the infrastructure that helps a solo PI attorney do their job — one attorney who has no paralegal, no IT support, and no patience for things that don't work. Every case they run through TRACE represents a client who was injured and is waiting for justice.

The code you write is the difference between an attorney who can prepare a demand in two weeks instead of twelve, and an attorney who gives up on the tool because it was too hard to use.

Write code like it matters. Because it does.

---

*These instructions apply to every line of code written for the TRACE system. They are not guidelines. They are the operating standard. Any deviation requires explicit justification in the PR description and sign-off from the product owner.*

*Last updated: July 2026*
