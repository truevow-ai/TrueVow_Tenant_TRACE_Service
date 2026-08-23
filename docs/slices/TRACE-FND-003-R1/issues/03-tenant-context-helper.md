# 03: Canonical tenant-context helper (expand phase)

**What to build:** One internal session factory exists beside the request-scoped dependency and yields sessions carrying the same three parameterized GUCs (`app.current_tenant_id`, `app.current_user_id`, `app.current_user_role`). It accepts explicit trusted context values (firm/user/role) and sets them transaction-locally via bound parameters. Pure addition: no callers change in this ticket, so nothing existing can break while the new seam lands.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Helper yields a session whose GUCs are set via parameterized statements (never string interpolation)
- [ ] Context values are transaction-local: after commit/rollback a reused pooled connection shows reset defaults (reset proven by test)
- [ ] Missing/empty trusted-context input fails closed (no silent unscoped session)
- [ ] Request-scoped dependency behavior unchanged; guarded suite untouched-green
- [ ] Unit tests cover set/reset/fail-closed semantics
