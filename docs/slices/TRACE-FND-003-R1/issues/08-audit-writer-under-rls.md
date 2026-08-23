# 08: Audit writer under real RLS

**What to build:** The append-only audit writer persists successfully *under* Row-Level Security as the restricted identity — not beside it. The writer obtains the canonical helper session using the firm context carried by the audited action; INSERT succeeds when context matches the row's firm, fails closed without it. Proven specifically against the actual role/grant contract from migration 0023, including INSERT-only privilege, not against an arbitrary test role.

**Blocked by:** 01 (Versioned 0023 role/grant contract), 03 (tenant-context helper).

**Status:** ready-for-agent

- [ ] Audit write succeeds as the runtime login with matching tenant GUCs
- [ ] Audit write denied (fail closed) when tenant context absent or mismatched
- [ ] Runtime login SELECT/UPDATE/DELETE on audit table denied (INSERT-only verified against 0023 state)
- [ ] Writer no longer opens a bare operational session anywhere
- [ ] Best-effort audit semantics preserved: audit failure never breaks the served response
