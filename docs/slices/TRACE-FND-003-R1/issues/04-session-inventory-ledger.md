# 04: Session inventory ledger

**What to build:** The factual migration ledger is frozen before any caller is touched. Every operational runtime occurrence of direct session/engine construction — session-maker opens, engine connect/begin, engine creation, runtime URL resolution — is enumerated and classified (`TENANT_REQUEST_SCOPED`, `TENANT_INTERNAL_SCOPED`, `GLOBAL_READ_ONLY`, `MIGRATION_TEST_ADMIN`, `INVALID_BYPASS_PATH`). Spec-time scan baseline: ~57 sites. For each migration-batch row record: files, session sites, tenant-context source, target ticket, and any special invariant (e.g., append-only audit). The ledger is committed as slice evidence and becomes the batch-sizing authority.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Ledger enumerates every site with file/location reference
- [ ] Each site classified into exactly one of the five classes with rationale where non-obvious
- [ ] Per-batch tables list: files / session sites / tenant-context source / target ticket / special invariant
- [ ] Baseline counts frozen; later batches flip rows rather than re-scan
- [ ] Batch-size verdict recorded: whether attorney-route batch stays whole or pre-splits into 05A/05B (sizing note only)
- [ ] Committed artifact reviewable by gate without running code
