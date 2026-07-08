-- TRACE database roles & permissions (Spec Part 3.2)
-- Apply once, after the operational schema migration. Least-privilege by design.

-- 1. Application role: read/write operational tables; INSERT-only on audit_log.
CREATE ROLE trace_app_role NOLOGIN;
GRANT SELECT, INSERT, UPDATE ON
    cases, providers, documents, chronology_entries, event_nodes
    TO trace_app_role;
GRANT INSERT ON audit_log TO trace_app_role;            -- append-only: no SELECT/UPDATE/DELETE

-- 2. PHI access role: separate, elevated only for attorney-authenticated PHI reads.
--    (Granted in the SEPARATE PHI database instance where the clients table lives.)
CREATE ROLE trace_phi_role NOLOGIN;
-- In the PHI instance:  GRANT SELECT, INSERT, UPDATE ON clients TO trace_phi_role;
-- Never open by default; never granted to trace_app_role.

-- 3. Read-only role: reporting/support. No audit_log, no clients.
CREATE ROLE trace_readonly_role NOLOGIN;
GRANT SELECT ON
    cases, providers, documents, chronology_entries, event_nodes
    TO trace_readonly_role;

-- Hard invariant: no application role may mutate the audit trail.
REVOKE UPDATE, DELETE ON audit_log FROM trace_app_role, trace_readonly_role;
