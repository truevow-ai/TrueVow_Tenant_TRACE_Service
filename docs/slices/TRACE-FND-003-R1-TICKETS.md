# TRACE-FND-003-R1 — Ticket Map

**Slice:** Runtime Role Commissioning and Tenant-Context Closure
**Spec:** [`docs/slices/TRACE-FND-003-R1-SPEC.md`](../TRACE-FND-003-R1-SPEC.md) @ commit `53d119b` (spec gate review: 14/14 PASS)
**Decomposition:** approved by owner 2026-08-23 with edge corrections `08 ← 01,03` and `09 ← 06,07 (05 removed)`; 14-ticket granularity locked; 05 pre-split deferred to ledger verdict.

| # | Ticket | Blocked by | Delivers |
|---|---|---|---|
| 01 | [Versioned 0023 role/grant contract](issues/01-versioned-0023-role-contract.md) | — | `0023_fnd003_runtime_role` revising 0022; restricted login + grants as schema state |
| 02 | [Two-URL authority split](issues/02-two-url-authority-split.md) | 01 | Privileged migration URL required by tooling only; `/ready` expects 0023 |
| 03 | [Canonical tenant-context helper](issues/03-tenant-context-helper.md) *(expand)* | — | New seam, parameterized GUCs, reset-proven; zero callers changed |
| 04 | [Session inventory ledger](issues/04-session-inventory-ledger.md) | — | All ~57 sites classified; per-batch tables; batch-size verdict for 05 |
| 05 | [Migrate attorney-route callers](issues/05-migrate-attorney-route-callers.md) | 03, 04 | QA/lien/evidence routes on canonical context; batch rows flipped |
| 06 | [Migrate portal/activation/webhook trusted callers](issues/06-migrate-portal-activation-webhook-callers.md) | 03, 04 | Envelope/grant-derived context for activation, portal, signing |
| 07 | [Migrate services + shared-foundation stores](issues/07-migrate-services-shared-foundation.md) | 03, 04 | Service-layer + event store/consent/policy stores on helper; GLOBAL_READ_ONLY justifications |
| 08 | [Audit writer under real RLS](issues/08-audit-writer-under-rls.md) | **01, 03** | INSERT-only persistence under RLS proven against actual 0023 contract |
| 09 | [Fail-close unresolved tenant-context surfaces](issues/09-failclose-untrusted-context-callers.md) | **06, 07** | `BLOCKED_INTERNAL_TENANT_CONTEXT` on all 13 discovery-circular/untrusted sites (inbound ×5, fax-status, signing webhook, portal resolution ×6); no bypass role / definer resolver; PARTIAL/uncommissioned recorded |
| 10 | [Contract: retire bypass patterns](issues/10-contract-retire-bypass-patterns.md) *(contract)* | 05–09 | Zero operational direct opens; CI guard; INVALID_BYPASS_PATH = 0 |
| 11 | [Runtime-role /ready evidence](issues/11-runtime-role-readiness-evidence.md) | 02 | Live identity + flags in readiness; loud failure on wrong identity |
| 12 | [Guarded non-bypass adversarial acceptance](issues/12-guarded-nonbypass-adversarial-acceptance.md) | 01, 10 | Full guarded suite AS restricted login; adversarial set green; 0 failed/skipped |
| 13 | [Supabase commissioning + bounded smoke](issues/13-supabase-commissioning-bounded-smoke.md) | 11, 12 | Role applied via privileged URL→Alembic→0023 only; operator does password/URL/verify/smoke exclusively |
| 14 | [Gate evidence / PASS_CANDIDATE package](issues/14-gate-evidence-pass-candidate-package.md) | 13 | Evidence bundle + truth-doc status-delta proposal staged for Gate 003 |

## Release frontier at publish time

Unblocked now: **01, 03, 04** (three parallel fronts). Then: 02, 05–08 unlock progressively per edges above.

## Rules binding every ticket

- Status labels change only with accepted evidence (canonical truth §11).
- Mechanical caller changes only — no business-semantics drift.
- No BYPASSRLS role, no `SET ROLE`, no `SECURITY DEFINER`, no RLS weakening anywhere in this slice.
- Builder green ≠ Gate PASS; Gate 003 is independent.
