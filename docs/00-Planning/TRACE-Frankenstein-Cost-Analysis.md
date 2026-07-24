# The "Stitch-It-Together" Cost Analysis
## What a Law Firm Would Pay to Replicate TRACE with Existing Products

**Date:** July 2026  
**Scenario:** A solo PI attorney wants every capability TRACE offers. Since no single product does it all, they must buy multiple products. Here's what it costs.

---

## The Frankenstein Stack — Monthly Cost

| # | What They Need | Which Product | Monthly Cost | What They Get | What They DON'T Get |
|---|---------------|---------------|-------------|---------------|-------------------|
| 1 | Case Management (basic tracking) | Clio EasyStart | **$49/user** | Case files, document storage, calendaring | No medical features |
| 2 | Client Portal + Messaging | SmartVault | **$40/user** | Secure document sharing, client messaging | No medical processing |
| 3 | Record Retrieval (send faxes to providers) | ChartSwap | **$150/mo** (4 requests × ~$37 avg) | Provider records retrieved, digital delivery | Per-request billing, no built-in fax |
| 4 | Medical Chronology | TAVRN AI (Entry) | **$99/mo** | AI chronology, basic demand letters | No source citations, no flag detection |
| 5 | Medical Summaries | Eve.Legal (Solo) | **$500/mo** | AI medical overviews, demand letters, discovery | Prohibitively expensive for solo |
| 6 | Demand Letter Generation | Inquery.ai (Entry) | **$99/mo** | AI demand letters, medical summaries | No chronology, no records mgmt |
| 7 | Document Storage (HIPAA) | SmartVault (already included) | $0 | Already in #2 | — |
| 8 | Client Intake + Bilingual | YoCierge (Entry) | **$250/mo** | Bilingual intake, client communication | No medical processing |
| 9 | Deadline/SOL Tracking | Clio (already included) | $0 | Calendar deadlines (manual entry only) | No SOL auto-calculation |

**TOTAL MONTHLY (Frankenstein Stack):** $1,187/month

**ANNUAL COST:** $14,244/year

**What they STILL don't have after spending $14,244/year:**

| Missing Capability | Can Any Product Provide It? |
|-------------------|---------------------------|
| SOL auto-calculation from incident date | NO — nobody does this |
| 50-state statute reference with disclaimer | NO |
| Provider NPI lookup + confirmation gate | NO |
| Provider list lock (checkpoint) | NO |
| Built-in outbound fax (not a service) | NO |
| Inbound email/fax document reception | NO |
| SHA-256 document deduplication | NO |
| Deterministic (non-AI) chronology | NO — all competitors are AI-generated |
| **Clinical flag detection (15 types)** | **NO — TRACE only** |
| Flag annotation by attorney | NO |
| Source citations on every entry | NO |
| Readiness board / case dashboard | NO |
| Lien tracking (6 types, 4 statuses) | NO |
| Attorney work product disclaimer on export | NO |
| Separate encrypted PHI store | NO |
| HIPAA audit log (append-only) | NO |

**Total missing capabilities: 16 of 27 features (59%) are unachievable at any price.**

---

## Why the Frankenstein Stack Doesn't Work

### Problem 1: The Products Don't Talk to Each Other

```
Clio (case mgmt) ≠ ChartSwap (records) ≠ TAVRN (chronology) ≠ Inquery (demand)
```

The attorney has to manually transfer data between four different platforms:
- Export case info from Clio → type into ChartSwap request form
- Download records from ChartSwap → upload to TAVRN
- Copy chronology from TAVRN → paste into Inquery for demand letter
- Track liens in a spreadsheet

**Result:** The integration work that TRACE does in seconds takes the attorney hours of manual data entry per case.

### Problem 2: Service Latency Kills the Pipeline

ChartSwap takes 7-14 days to retrieve records (they're a service company, humans do the work). TRACE sends faxes instantly and receives inbound documents the same day. The Frankenstein stack has a built-in 2-week delay.

### Problem 3: The Clinical Flag Gap is Fatal

The 15 clinical flags are TRACE's only uncompetitive feature. The Frankenstein stack has ZERO clinical flag detection. The attorney has to manually read 500-1500 pages to find:
- Treatment gaps the carrier will exploit
- Credibility language from clinicians
- Pre-existing condition mentions
- Missing follow-ups
- MMI documentation gaps

This is the paralegal work that TRACE automates — and it costs $25-40/hour in paralegal time. At 15-20 hours per case, that's $375-$800 per case in paralegal costs that TRACE eliminates.

### Problem 4: Per-Request vs. Unlimited

ChartSwap charges per request. A case with 5 providers = $125-$325 in record retrieval fees alone. TRACE sends unlimited faxes. The Frankenstein stack gets more expensive the more providers a case has. TRACE stays flat.

---

## Cost Comparison: Frankenstein vs. TRACE

### For a Solo Attorney (4 cases/month, 3 providers per case)

| Item | Frankenstein | TRACE Professional |
|------|-------------|-------------------|
| Case management | Clio $49 | ✓ Included |
| Records retrieval | ChartSwap $90 | ✓ Included (unlimited fax) |
| Medical chronology | TAVRN $99 | ✓ Included (deterministic) |
| Medical summaries | Eve $500 (or skip) | ✓ Included |
| Demand package | Inquery $99 | ✓ Included (template) |
| Client portal | SmartVault $40 | ✓ Included (upload links) |
| Bilingual intake | YoCierge $250 | ✓ (via INTAKE) |
| SOL calculator | — (doesn't exist) | ✓ Included |
| Clinical flags | — (doesn't exist) | ✓ Included |
| Lien tracking | — (doesn't exist) | ✓ Included |
| HIPAA PHI store | — (doesn't exist) | ✓ Included |
| **Monthly cost** | **$1,027/mo** | **$0/mo (pay per case)** |
| **Per-case cost** | **$257/case** (assuming 4 cases) | **$99/case** |
| **Features covered** | 11 of 27 (41%) | **24 of 27 (89%)** |
| **Missing features** | 16 of 27 | 3 of 27 |

### For a Small Firm (12 cases/month, 3 providers per case)

| Item | Frankenstein | TRACE Professional |
|------|-------------|-------------------|
| Case management | Clio Advanced $119 × 3 users = **$357** | Included |
| Records retrieval | ChartSwap $270 | Included |
| Medical chronology | TAVRN Growth $299 | Included |
| Medical summaries | Eve Growth $1,000 | Included |
| Demand package | Inquery Growth $299 | Included |
| Client portal | SmartVault $60 × 3 = **$180** | Included |
| Bilingual intake | YoCierge $500 | ✓ (via INTAKE) |
| **Monthly cost** | **$2,905/mo** | **$0/mo (pay per case)** |
| **Per-case cost** | **$242/case** | **$99/case** |
| **Annual cost** | **$34,860/yr** | **$14,256/yr** (at $99 × 12 cases × 12 months) |
| **Savings with TRACE** | — | **$20,604/year** |

---

## The Bottom Line

**A law firm cannot stitch together what TRACE offers at any price.** Sixteen of TRACE's 27 features don't exist in any competing product.

For what IS available, the Frankenstein stack costs $1,027-$2,905/month, delivers only 41% of TRACE's features, and requires the attorney to manually transfer data between 4-6 disconnected platforms.

**TRACE at $99/case:**
- Costs $396/month for the average solo (4 cases) vs. $1,027/month for the Frankenstein stack
- Delivers 89% feature coverage vs. 41%
- Has zero data-transfer overhead (everything is integrated)
- Has no per-request fees (unlimited faxes)
- Is the ONLY product with clinical flag detection

**The choice for a solo PI attorney is not between TRACE and a competitor. It's between TRACE and 15-20 hours of paralegal work per case at $375-800/case — plus a dozen disconnected tools that still don't cover what TRACE does.**

---

## Recommendation: Use This in Sales Conversations

When a solo attorney objects to $99/case:

> "Let me show you what it would cost to get these capabilities elsewhere. Clio for case management: $49/mo. ChartSwap for records: $90/mo. TAVRN for chronology: $99/mo. Inquery for demand letters: $99/mo. SmartVault for secure docs: $40/mo. That's $377/month — and you STILL don't have clinical flags, lien tracking, or SOL calculation because nobody else offers those. TRACE is $99/case — not per month, per case. Four cases this month? $396. And you got all 24 features. The alternative is $377/month just for the 11 features other products can give you. The other 13 you can't buy anywhere."
