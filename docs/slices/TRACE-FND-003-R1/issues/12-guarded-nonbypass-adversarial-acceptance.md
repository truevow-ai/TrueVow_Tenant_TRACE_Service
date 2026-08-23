# 12: Guarded non-bypass adversarial acceptance

**What to build:** The full guarded test suite executes against Postgres *as the restricted runtime login* and proves the security contract adversarially: cross-tenant access denied, missing-context denied, GUC reset across pooled reuse, audit INSERT-only enforced, same-tenant CRUD complete. Zero failed, zero skipped.

**Blocked by:** 01, 10.

**Status:** ready-for-agent

- [ ] Suite runs under the 0023-created login; connection identity asserted at session start
- [ ] Adversarial set green: cross-tenant SELECT/UPDATE/DELETE denied on tenant tables
- [ ] Missing-GUC sessions denied on tenant-operational access
- [ ] GUC reset proven transaction-locally across pooled connections
- [ ] Audit INSERT-only denial re-verified at suite level
- [ ] Full guarded run: 0 failed, 0 skipped
