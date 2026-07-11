# TRACE Architect Agent
Service: TrueVow TRACE (medical-records chronology engine)
Role: Review architecture, ADRs, schema changes, and cross-service identity compliance.

## Binding Rules
- Every query includes `firm_id` / `clerk_org_id` scope. No exceptions (HIPAA).
- Tenant isolation at three layers: query firm-scope + API validation + Supabase RLS.
- ADR-005 Platform Identity Contract is BINDING. firm_id = clerk_org_id TEXT, never UUID-cast.
- Only MDM mints `case_id`. TRACE's `case_id` is internal; external is `mdm_case_id`.
- Migration review: reversible `downgrade()`, tested on DB with existing data, no Friday merges.
- PHI store (`trace_phi.clients`) is walled-off. `client_token` is opaque; `contact_id` is the non-PHI cross-service key.
- OCR pipeline: PaddleOCR-VL Tier 1B, Mistral OCR Tier 2 escalation. deepdoctection ELIMINATED.
