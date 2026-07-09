# TRACE — Failover Runbook
## Region failover: iad → lax

**Last updated:** July 2026
**Reference:** ADR-001 §13.3

Manual steps to fail over from `iad` (us-east) to `lax` (us-west)
if the primary region becomes unavailable.

### Prerequisites
- [ ] Clerk BAA verified on file
- [ ] Fly.io HIPAA compliance package signed (pre-production gate)
- [ ] Supabase HIPAA add-on active (pre-production gate)
- [ ] Supabase connection string with pooler URL configured
- [ ] `flyctl` authenticated and targeting the `truevow-trace` app

### Failover Steps

1. **Add secondary region**
   ```bash
   fly regions add lax
   ```

2. **Scale to deploy an instance in lax**
   ```bash
   fly scale count 2
   ```

3. **Verify health endpoint in lax**
   ```bash
   fly ssh console --region lax
   curl http://localhost:8080/health
   ```

4. **Update DNS or internal service registry**
   Point the service registry entry to the lax instance.
   Internal Ops service registry: update `trace-service` target.

5. **Monitor for 5 minutes**
   Confirm attorney-facing portal is reachable and responsive.

6. **When iad recovers**
   ```bash
   fly regions remove iad
   fly scale count 1
   ```

### Rollback
- Reverse the steps: add `iad`, scale, verify, update registry, remove `lax`.

---

# BAA Verification Checklist

**Last updated:** July 2026
**Reference:** ADR-001 §21, §22

Every vendor that touches PHI or PHI-adjacent data must have a signed
BAA on file before the first real case is processed.

### Before Phase 1A (dev auth only)
- [ ] **Clerk BAA** — Verify on file for TrueVow-Tenants app.
  - Owner: Legal / Platform
  - Note: Clerk is the platform standard across ALL TrueVow services.
    BAA should be pre-existing. If not, execute before any TRACE auth
    middleware is built.

### Before Production Go-Live (PHI enters system)
- [ ] **Supabase BAA** — Execute + HIPAA add-on enabled.
  - Owner: DevOps / Platform
  - Requirements: Team Plan minimum, HIPAA add-on enabled (§16 checklist),
    SSL Enforcement on, Network Restrictions configured, PITR enabled,
    connection logging on, no PHI in Edge Functions or Fly Postgres.

- [ ] **Fly.io BAA** — Sign compliance package.
  - Owner: DevOps
  - Self-service at `fly.io/dashboard/personal/compliance`.
  - Must be done before any PHI touches a Fly.io container.

- [ ] **Fax.Plus BAA** — Already signed (Phase 0). Verify actual invoice.
  - Owner: Finance / Platform
  - Compare against Documo at projected volume per §17 switch trigger.

### Conditional (only if triggered)
- [ ] **LlamaParse BAA** — Execute only if Phase 1C handwriting spike fails.
  - Owner: Legal / Platform
  - Must be executed before Phase 1D OCR pipeline build begins.

### Not Required
- [ ] **OpenMed, deepdoctection, DeepSeek V4 Pro** — Self-hosted within Fly.io
  HIPAA boundary. Covered by Fly.io BAA. No separate BAA needed.
- [ ] **CMS NPI Registry** — Government API, no PHI transmitted.
- [ ] **Azure OpenAI** — BAA exists automatically under Microsoft DPA for
  qualifying services. No manual activation needed.
