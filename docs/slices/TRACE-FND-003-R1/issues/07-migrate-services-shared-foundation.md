# 07: Migrate services + shared-foundation stores

**What to build:** Service-layer and shared-foundation writers/readers that open direct operational sessions — chronology builder, fact review, follow-up scheduler, provider extraction, trusted inbound-processing parts, event store, consent ledger, policy registry — receive or create their sessions through the canonical helper with explicit trusted context. Shared-foundation stores are tenant-scoped by their owning flow's context; genuinely global reference reads are classified `GLOBAL_READ_ONLY` with justification in the ledger.

**Blocked by:** 03 (tenant-context helper), 04 (session inventory ledger).

**Status:** ready-for-agent

- [ ] All ledger rows assigned to this batch migrated; zero direct opens remain at those sites
- [ ] Every `GLOBAL_READ_ONLY` classification carries a written justification (table set touched, tenant-agnostic proof)
- [ ] Guarded suite green; no semantic change to evidence/chronology outputs
- [ ] Ledger updated with final batch counts
