# 11: Runtime-role /ready evidence

**What to build:** Readiness proves the live connection identity instead of assuming it. `/ready` gains a `runtime_role` check executed on the runtime engine: expected login name matches both `current_user` and `session_user`, catalog flags confirm `rolsuper = false` and `rolbypassrls = false` (values only — never credentials or key material). Startup/readiness fail loudly on a wrong identity so a miswired deployment never serves traffic believing it is isolated.

**Blocked by:** 02 (Two-URL authority split).

**Status:** ready-for-agent

- [ ] `/ready` includes `runtime_role` check alongside database/migration/critical-tables/phi_key
- [ ] Check green only when identity = expected login AND both flags false
- [ ] Wrong-identity deployment reports explicit not_ready with role evidence values
- [ ] No secret or credential material appears in readiness output
- [ ] Tests cover green, wrong-user, and bypass-flagged variants
