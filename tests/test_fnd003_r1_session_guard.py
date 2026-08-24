"""FND-003-R1 — direct-session elimination guard (grows with each batch).

Batch-05 modules must contain zero direct operational session opens. The
allowlist below mirrors the inventory ledger; Ticket 10 shrinks it to empty
(INVALID_BYPASS_PATH = 0) and this test becomes the permanent CI guard.
"""

from __future__ import annotations

from pathlib import Path

# module path → reason still pending (ticket that will clear it)
PENDING_BATCHES: dict[str, str] = {
    "app/api/routes/signing.py": "T06 trusted side",
    "app/api/routes/client_portal.py": "T09 fail-close",
    "app/api/routes/webhooks.py": "T09 fail-close",
    "app/services/chronology.py": "T07",
    "app/services/evidence.py": "T07",
    "app/services/fact_review.py": "T07",
    "app/services/followup.py": "T07",
    "app/services/providers.py": "T07",
    "app/services/inbound.py": "T09 fail-close",
    "app/services/matter_activation.py": "T06",
    "app/shared/consent_ledger.py": "T07",
    "app/shared/event_store.py": "T07",
    "app/shared/policy_registry.py": "T07",
    "app/core/audit.py": "T08",
    "app/main.py": "GLOBAL_READ_ONLY / T11 readiness",
}

MIGRATED_NOW_EMPTY = (
    "app/api/routes/qa.py",
    "app/api/routes/liens.py",
    "app/api/routes/evidence.py",
)

_PATTERN = "async_session_maker("


def test_batch05_modules_have_no_direct_session_opens():
    for rel in MIGRATED_NOW_EMPTY:
        source = Path(rel).read_text(encoding="utf-8")
        assert _PATTERN not in source, (
            f"{rel} regressed: direct session open reintroduced"
        )


def test_pending_allowlist_matches_ledger():
    """Guard against silent scope drift: every known pending module must
    still contain its bare opens until its ticket migrates them."""
    missing = []
    for rel in PENDING_BATCHES:
        if _PATTERN not in Path(rel).read_text(encoding="utf-8"):
            # A ticket already migrated it — the allowlist entry must be removed.
            missing.append(rel)
    assert missing == [], (
        f"Allowlist stale — remove migrated modules from PENDING_BATCHES: {missing}"
    )
