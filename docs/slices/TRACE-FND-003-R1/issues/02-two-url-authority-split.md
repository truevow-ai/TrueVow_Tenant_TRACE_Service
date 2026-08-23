# 02: Two-URL authority split

**What to build:** Database authority is split so privileged administration and application runtime can never share a connection string. The migration tooling requires the new privileged migration URL and fails loudly without it; the running application resolves only the existing runtime and PHI URLs and has no code path that reads the migration URL. The application's required-revision marker advances to `0023_fnd003_runtime_role`, making readiness enforce that the role contract is applied. Local/example environment documentation shows both variables and their distinct authorities.

**Blocked by:** 01 (Versioned 0023 role/grant contract).

**Status:** ready-for-agent

- [ ] Alembic runs when the privileged URL is set and aborts with an explicit error when it is absent
- [ ] Alembic never silently falls back to the runtime URL (and vice versa: the app never falls back to the privileged URL)
- [ ] Application boots against runtime URL alone, with no import/startup reference to the migration URL
- [ ] Required-revision marker equals `0023_fnd003_runtime_role`; `/ready` reports mismatch when DB sits at 0022
- [ ] Pooler-compatible connection behavior preserved unchanged
- [ ] Guarded suite green with the new configuration contract
