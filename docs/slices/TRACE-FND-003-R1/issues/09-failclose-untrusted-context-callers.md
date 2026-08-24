# 09: Fail-close unresolved tenant-context surfaces

**What to build:** Every runtime surface that needs tenant-owned data but holds no trustworthy tenant UUID before its first tenant-table access raises `BLOCKED_INTERNAL_TENANT_CONTEXT` instead of touching tenant rows unscoped. In scope (13 ledger sites): inbound email, inbound fax, fax-status callback, **DocuSeal completion-webhook tenant discovery** (provider signature authenticates the vendor, not the tenant), **Client Portal initial access/tenant resolution** (`_verify_client_access()` discovers tenant from caller-supplied identifiers via ClientAccessProjection — circular under RLS). No BYPASSRLS role, no migration/admin connection, no `SECURITY DEFINER` resolver is introduced. A surface is migrated out of this set only if it already possesses a trustworthy tenant UUID before any tenant-table access.

**Blocked by:** 06, 07.

**Status:** ready-for-agent

- [ ] All 13 sites raise `BLOCKED_INTERNAL_TENANT_CONTEXT`; no tenant-row access occurs on those paths without prior trusted UUID
- [ ] Tests prove fail-closed behavior per surface class (inbound, fax-status, signing webhook, portal resolution)
- [ ] No new privileged lookup mechanism, special system role, or definer function appears in the diff
- [ ] Ledger rows reclassified fail-closed; INVALID_BYPASS_PATH count = 0 contribution confirmed with Ticket 10
- [ ] PARTIAL/uncommissioned status recorded for affected surfaces with successor Class-E trust-resolution pointer
