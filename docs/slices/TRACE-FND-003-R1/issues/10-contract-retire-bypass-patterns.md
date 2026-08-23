# 10: Contract — retire bypass patterns

**What to build:** The old direct-session pattern becomes impossible to reintroduce. After all migrate batches and the fail-close ticket complete, operational runtime code contains zero direct session/engine constructions outside the two canonical entry points; a guard (lint rule or suite test) fails CI on any future occurrence; the inventory ledger's final state shows every site classified and `INVALID_BYPASS_PATH = 0`.

**Blocked by:** 05, 06, 07, 08, 09.

**Status:** ready-for-agent

- [ ] Repo scan reproduces zero remaining direct opens in runtime code paths
- [ ] Guard added and demonstrably fires on an intentional violation (test-proven)
- [ ] Inventory ledger finalized: 100% classified, INVALID_BYPASS_PATH count = 0
- [ ] Migration/test/operator tooling usages remain confined to their classified lanes
- [ ] Guarded suite green
