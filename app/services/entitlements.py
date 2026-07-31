"""TRACE Entitlement Gates — capability checks based on selected tier.

Billing specification §9: TRACE uses two levels of entitlement:
  1. Tenant-level — whether the firm can use TRACE commercially
  2. Matter-level — what capabilities are available for this specific Matter

Matter-level gates use the Matter's locked commercial selection (trace_plan_code).
Do not infer the tier only from a tenant-wide subscription.

Tier capabilities (from billing spec §9.2):
    TRACE Start ($35):
        TRACE_ENGAGEMENT, TRACE_CONFLICT_WORKFLOW, TRACE_SIGNATURE,
        TRACE_ACTIVATION, TRACE_ENGAGEMENT_HISTORY

    TRACE Essential ($179) — adds:
        TRACE_CLIENT_REQUESTS, TRACE_DOCUMENT_UPLOADS,
        TRACE_TREATMENT_TRACKING, TRACE_RECORDS_TRACKING,
        TRACE_STANDARD_READINESS

    TRACE Complete ($299) — adds:
        TRACE_DAMAGES_TRACKING, TRACE_WORK_IMPACT,
        TRACE_ADVANCED_EVIDENCE, TRACE_ADVANCED_READINESS,
        TRACE_ESCALATIONS, TRACE_COMPLETE_WORKFLOW
"""

from __future__ import annotations

TRACE_PLAN_CAPABILITIES: dict[str, set[str]] = {
    "trace_start_v1": {
        "TRACE_ENGAGEMENT",
        "TRACE_CONFLICT_WORKFLOW",
        "TRACE_SIGNATURE",
        "TRACE_ACTIVATION",
        "TRACE_ENGAGEMENT_HISTORY",
    },
    "trace_essential_v1": {
        "TRACE_ENGAGEMENT",
        "TRACE_CONFLICT_WORKFLOW",
        "TRACE_SIGNATURE",
        "TRACE_ACTIVATION",
        "TRACE_ENGAGEMENT_HISTORY",
        "TRACE_CLIENT_REQUESTS",
        "TRACE_DOCUMENT_UPLOADS",
        "TRACE_TREATMENT_TRACKING",
        "TRACE_RECORDS_TRACKING",
        "TRACE_STANDARD_READINESS",
    },
    "trace_complete_v1": {
        "TRACE_ENGAGEMENT",
        "TRACE_CONFLICT_WORKFLOW",
        "TRACE_SIGNATURE",
        "TRACE_ACTIVATION",
        "TRACE_ENGAGEMENT_HISTORY",
        "TRACE_CLIENT_REQUESTS",
        "TRACE_DOCUMENT_UPLOADS",
        "TRACE_TREATMENT_TRACKING",
        "TRACE_RECORDS_TRACKING",
        "TRACE_STANDARD_READINESS",
        "TRACE_DAMAGES_TRACKING",
        "TRACE_WORK_IMPACT",
        "TRACE_ADVANCED_EVIDENCE",
        "TRACE_ADVANCED_READINESS",
        "TRACE_ESCALATIONS",
        "TRACE_COMPLETE_WORKFLOW",
    },
}

TRACE_PLAN_PRICES: dict[str, int] = {
    "trace_start_v1": 3500,
    "trace_essential_v1": 17900,
    "trace_complete_v1": 29900,
}


def has_capability(plan_code: str, capability: str) -> bool:
    """Check if a TRACE plan supports a specific capability."""
    capabilities = TRACE_PLAN_CAPABILITIES.get(plan_code, set())
    return capability in capabilities


def get_capabilities(plan_code: str) -> set[str]:
    """Get all capabilities for a TRACE plan."""
    return TRACE_PLAN_CAPABILITIES.get(plan_code, set())


def get_plan_price_cents(plan_code: str) -> int:
    """Get the price in cents for a TRACE plan."""
    return TRACE_PLAN_PRICES.get(plan_code, 0)
