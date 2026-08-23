# 09: Fail-close untrusted-context callers

**What to build:** Runtime paths that need tenant-owned data but lack a trustworthy tenant identity — fax delivery-status callbacks and inbound email/fax processing as they stand — raise the explicit `BLOCKED_INTERNAL_TENANT_CONTEXT` condition instead of touching tenant rows unscoped. No BYPASSRLS role, no migration/admin connection, no `SECURITY DEFINER` resolver is introduced. Affected surfaces are recorded as fail-closed/PARTIAL/uncommissioned pending the successor integration-security slice (which also closes GAP-1/GAP-2).

**Blocked by:** 06, 07.

**Status:** ready-for-agent

- [ ] Untrusted-context paths raise `BLOCKED_INTERNAL_TENANT_CONTEXT`; no tenant-row access occurs on those paths
- [ ] Tests prove fail-closed behavior: no row reads/writes without trusted context
- [ ] No new privileged lookup mechanism, special system role, or definer function appears in the diff
- [ ] Ledger rows for these sites classified fail-closed (not INVALID_BYPASS_PATH)
- [ ] PARTIAL/uncommissioned status recorded for affected callbacks with successor-slice pointer
