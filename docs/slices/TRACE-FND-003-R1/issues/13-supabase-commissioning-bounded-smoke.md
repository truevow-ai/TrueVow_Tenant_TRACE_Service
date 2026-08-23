# 13: Supabase commissioning + bounded smoke

**What to build:** The staging Supabase project receives the role contract through the versioned migration chain — privileged URL into Alembic, `alembic upgrade` applying `0023_fnd003_runtime_role` — and the operator-only procedure then does exactly and only: set runtime password → securely construct/store `TRACE_DATABASE_URL` → connect as `trace_runtime_login` → run non-secret verification queries → execute the bounded adversarial smoke. The operator script never recreates role/grants itself; DDL authority stays exclusively in 0023.

**Blocked by:** 11 (Runtime-role /ready evidence), 12 (Guarded non-bypass adversarial acceptance).

**Status:** ready-for-agent

- [ ] Role applied on staging solely via `TRACE_MIGRATION_DATABASE_URL` → Alembic upgrade → 0023 (evidence: alembic version output)
- [ ] Runtime password set and runtime URL stored via secret-handling procedure; no secret material in Git or logs
- [ ] Non-secret verification output captured: `current_user`/`session_user`, `rolsuper = false`, `rolbypassrls = false`
- [ ] Bounded smoke executed as `trace_runtime_login`: same-tenant CRUD ok; cross-tenant denied; audit INSERT-only enforced
- [ ] `/ready` against staged runtime URL reports all checks green
