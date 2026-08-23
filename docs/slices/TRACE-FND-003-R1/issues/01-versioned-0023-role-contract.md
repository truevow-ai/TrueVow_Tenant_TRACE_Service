# 01: Versioned 0023 role/grant contract

**What to build:** The runtime database identity becomes version-controlled schema state. A new Alembic migration revising the FND-003 RLS reconciliation creates and configures the dedicated application login — `NOSUPERUSER`, `NOBYPASSRLS` — grants the minimal same-tenant operational DML across the tenant tables, grants INSERT-only on the append-only audit table, revokes ownership-derived broad rights and any legacy direct-grant path a pooled connection could inherit, denies all access to the PHI store, and downgrades cleanly if reversed. Running the migration chain on a fresh Postgres yields a login whose catalog facts are exactly the spec's acceptance contract.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] Migration applies idempotently and its revision records `0022_fnd003_rls_reconciliation` as parent
- [ ] After upgrade: `rolsuper = false`, `rolbypassrls = false` for the runtime login
- [ ] Runtime login owns no tenant table; cannot CREATE/ALTER/DROP in the trace schema
- [ ] Zero privileges in the PHI store for the runtime login
- [ ] Audit table rights = INSERT only (SELECT/UPDATE/DELETE denied)
- [ ] Same-tenant SELECT/INSERT/UPDATE/DELETE succeeds on every tenant-operational table under set tenant context
- [ ] Downgrade removes the role/grants safely or is proven no-op-safe; re-upgrade reproduces identical state
