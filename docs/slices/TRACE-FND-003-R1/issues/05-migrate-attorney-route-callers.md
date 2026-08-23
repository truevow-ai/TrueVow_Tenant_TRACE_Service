# 05: Migrate attorney-route callers

**What to build:** Attorney-facing route flows that today open direct operational sessions — chronology/readiness/approve/export QA flows, lien CRUD, evidence review routes — obtain their sessions through the request-scoped dependency or the canonical helper with `ctx.firm_id` as trusted source. Business semantics unchanged; the diff is mechanical context plumbing. Batch rows in the ledger flip to `TENANT_REQUEST_SCOPED` / `TENANT_INTERNAL_SCOPED`.

**Blocked by:** 03 (tenant-context helper), 04 (session inventory ledger).

**Status:** ready-for-agent

- [ ] Every ledger row assigned to this batch migrated; zero direct opens remain at those sites
- [ ] All migrated paths pass firm_id from authenticated context only
- [ ] Guarded suite green; no behavioral change visible to attorney UX
- [ ] Ledger updated: batch baseline count = sites migrated
- [ ] If this batch proves materially larger or dual-patterned than inventoried, record 05A/05B split recommendation before implementation proceeds (sizing note only)
