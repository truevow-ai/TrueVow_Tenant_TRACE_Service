# 06: Migrate portal/activation/webhook trusted callers

**What to build:** Trusted webhook and portal surfaces open tenant context from verified authorities: the Matter activation handler derives context from the signed envelope's verified `tenant_id`; client portal routes use their granted client-access identity mapping to firm context; signing flow sessions carry the matter's firm context. No untrusted external identifier ever drives a privileged lookup.

**Blocked by:** 03 (tenant-context helper), 04 (session inventory ledger).

**Status:** ready-for-agent

- [ ] Activation projection runs entirely under envelope-verified tenant context via the canonical helper
- [ ] Client portal routes resolve firm context from the access grant, not raw path parameters alone
- [ ] Signing-path sessions carry the case's firm context before any tenant-row access
- [ ] Ledger rows for this batch flipped; guarded suite green
- [ ] Idempotent duplicate-event behavior unchanged
