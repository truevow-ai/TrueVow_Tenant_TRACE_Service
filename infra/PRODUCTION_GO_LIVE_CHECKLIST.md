# TRACE — Production Go-Live Checklist
## Spec Part 9 — Infrastructure, Compliance, Functional Gates, Onboarding

**Status:** Pre-production — all items must be confirmed with evidence before first real case  
**Date:** July 2026  
**Prerequisite:** Phase 1A-1E complete, all tests passing, load tests passing

---

## Part 9.1 — Vendor BAA Execution

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | **Fly.io**: Compliance Package signed ($99/mo add-on active) | ☐ | Dashboard screenshot |
| 2 | **Supabase**: Team Plan active, HIPAA add-on approved, BAA signed (~$375/mo) | ☐ | Supabase dashboard + BAA PDF |
| 3 | **Clerk**: Platform enterprise BAA confirmed to cover TRACE | ☐ | Email confirmation from Clerk |
| 4 | **Documo**: BAA executed, HIPAA mode ON, delivery webhook → production URL | ☐ | BAA PDF + Documo dashboard |
| 5 | **Azure OpenAI**: EA/MCA/CSP confirmed, BAA coverage verified at Microsoft Service Trust Portal | ☐ | Trust Portal screenshot |

---

## Part 9.2 — Supabase HIPAA Configuration (ADR-001 §16)

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | HIPAA add-on enabled on TRACE project | ☐ | Supabase dashboard |
| 2 | TRACE project marked High Compliance | ☐ | Supabase dashboard |
| 3 | MFA enforced on all Supabase org accounts | ☐ | Supabase dashboard |
| 4 | Point in Time Recovery enabled | ☐ | Supabase dashboard |
| 5 | SSL Enforcement enabled | ☐ | Supabase dashboard |
| 6 | Network Restrictions enabled (Fly.io IP only) | ☐ | Supabase dashboard |
| 7 | `log_connections = on` confirmed (default is OFF from Jul 9 2026) | ☐ | `SHOW log_connections;` output |
| 8 | AI editor data sharing disabled | ☐ | Supabase dashboard |
| 9 | No Supabase Edge Functions in PHI path | ☐ | Edge Functions list (empty) |
| 10 | Production project separate from staging/test | ☐ | Supabase dashboard |
| 11 | PITR recovery tested | ☐ | Recovery test log |

---

## Part 9.3 — Infrastructure Security

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | Supabase Storage bucket `trace-medical-records` — private access confirmed | ☐ | Storage policy screenshot |
| 2 | Supabase Storage bucket `signed-documents` — private access confirmed | ☐ | Storage policy screenshot |
| 3 | All secrets in Fly.io secrets, not in code, git, or env files | ☐ | `fly secrets list` output |
| 4 | All API endpoints return 401 without valid JWT | ☐ | Test output |
| 5 | MFA enforced on all attorney portal accounts (Clerk) | ☐ | Clerk dashboard |
| 6 | `audit_log`: INSERT only for `trace_app_role` confirmed | ☐ | PG role permissions |
| 7 | PHI store: accessible only via `trace_phi_role` | ☐ | PG role permissions |
| 8 | Signed URL expiry confirmed at 900 seconds | ☐ | Integration test |
| 9 | No client PII in any URL, log entry, notification, or email | ☐ | PHI leakage test passing |
| 10 | PHIRedactionFilter on root logger confirmed | ☐ | Log output verification |
| 11 | `assert_production_for_phi()` raises in non-production | ☐ | Test output |

---

## Part 9.4 — Functional Gates (Production)

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | Prohibited string filter passing all terms from PRD Appendix A | ☐ | Test output |
| 2 | Demand-ready gate blocks on PRIORITY flags with no annotation | ☐ | Test output |
| 3 | Provider list confirmation gate blocks fax before confirmation | ☐ | Test output |
| 4 | Signing gate blocks provider confirmation before HIPAA signed | ☐ | Test output |
| 5 | Documo delivery webhook working in production | ☐ | Webhook test log |
| 6 | Documo HIPAA mode confirmed ON | ☐ | Documo dashboard |
| 7 | Follow-up scheduler tested — faxes sent on day 10/20 | ☐ | Scheduler test log |
| 8 | Client upload link: token expiry enforced (410), revocation enforced (410) | ☐ | Integration test |
| 9 | Export disclaimer on every PDF page (not just cover) | ☐ | PDF verification |
| 10 | Export blocked if case_stage != DEMAND_READY | ☐ | Integration test |

---

## Part 9.5 — Compliance Documentation

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | HIPAA Security Risk Assessment completed | ☐ | SRA document |
| 2 | Penetration test completed, critical findings remediated | ☐ | Pentest report |
| 3 | Healthcare attorney signed off on BAA template | ☐ | Attorney email |
| 4 | Healthcare attorney signed off on attorney responsibility addendum | ☐ | Attorney email |
| 5 | HIPAA authorization template approved | ☐ | Approved template PDF |
| 6 | Privacy Officer designated in writing | ☐ | Appointment document |
| 7 | Security Officer designated in writing | ☐ | Appointment document |
| 8 | HIPAA workforce training completed (all staff with PHI access) | ☐ | Training records |
| 9 | Incident response plan documented and tested | ☐ | IR plan document |

---

## Part 9.6 — Attorney Onboarding Readiness

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | TrueVow ↔ attorney firm BAA template finalized | ☐ | BAA template |
| 2 | Attorney responsibility addendum finalized | ☐ | Addendum document |
| 3 | HIPAA authorization template finalized and tested | ☐ | Test signing completed |
| 4 | DocuSeal firm templates uploaded (retainer, fee agreement, HIPAA auth) | ☐ | DocuSeal dashboard |
| 5 | Attorney signature pre-configured in DocuSeal templates | ☐ | DocuSeal dashboard |
| 6 | Test signing session completed successfully | ☐ | Webhook test log |
| 7 | Support contact workflow documented (first 3 cases with support present) | ☐ | Support workflow doc |
| 8 | Attorney briefing document complete (what TRACE does/doesn't do, Board, flags, SOL) | ☐ | Briefing document |
| 9 | Full synthetic E2E workflow passes (init → sign → providers → fax → export) | ☐ | `test_e2e_synthetic.py` passing |

---

## Open Infrastructure Items

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Handwriting spike WER numbers documented | ☐ | `OCR_CLOUD_BACKEND` locked based on real numbers |
| 2 | BioClinical ModernBERT weights downloaded | ☐ | If yes: evaluation run, `NLP_LONG_CONTEXT_BACKEND` locked |
| 3 | If BioClinical not ready: `NLP_LONG_CONTEXT_BACKEND=disabled` confirmed | ☐ | Explicitly set in Fly.io secrets |

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Privacy Officer | | | |
| Security Officer | | | |
| Product Owner | | | |
| Engineering Lead | | | |

---

*Phase 1F is complete when all items are confirmed with evidence, load tests pass, and the first early access attorney BAA is signed. First real case with real PHI begins after sign-off.*
