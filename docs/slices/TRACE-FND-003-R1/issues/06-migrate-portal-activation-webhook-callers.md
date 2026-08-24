# 06: Migrate trusted callers — activation envelope + attorney signing/send

**What to build:** Only callers already holding a trustworthy tenant identity before their first tenant-table read. The Matter activation handler derives context from the signed envelope's verified `tenant_id`; the DocuSeal attorney-side `/send` flow uses authenticated `ctx.firm_id` (including its `_get_case(firm_id)` helper path). Provider-authenticated webhook discovery and client-portal access-projection discovery are **explicitly out of this ticket** (reclassified to 09 — tenant-discovery-via-tenant-table is circular under real RLS).

**Blocked by:** 03 (tenant-context helper), 04 (session inventory ledger).

**Status:** ready-for-agent

- [ ] Activation projection runs entirely under envelope-verified tenant context via the canonical helper
- [ ] Attorney signing `/send` path carries `ctx.firm_id` via request-scoped dep or helper
- [ ] Ledger rows for this reduced batch flipped; guarded suite green
- [ ] Idempotent duplicate-event behavior unchanged
- [ ] No site migrated whose tenant identity requires a pre-context tenant-table lookup
