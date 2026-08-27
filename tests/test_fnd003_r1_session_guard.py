"""FND-003-R1 — direct-session elimination guard (grows with each batch).

Every module below must contain zero direct operational session opens once
its owning ticket lands; the allowlist mirrors the inventory ledger and
Ticket 10 shrinks it to empty (INVALID_BYPASS_PATH = 0), at which point this
becomes the permanent CI guard.

The canonical seam itself (internal_tenant_session) is exempt by definition:
it is the only place a session is opened, and it is the boundary that enforces
tenant context — it is not a bypass.
"""

from __future__ import annotations

from pathlib import Path

SEAM_EXEMPTION = ("app/core/database.py",)

# module path → owning ticket / reason still pending
PENDING_BATCHES: dict[str, str] = {
    "app/api/v1/routes/signing.py": "T06B DocuSeal trusted routing (webhook site :129)",
    "app/api/v1/routes/client_portal.py": "TRACE-PORTAL-TRUST-001 grant-bound bootstrap",
    "app/api/v1/routes/webhooks.py": "T09 fail-close: Resend/Twilio/fax-status inbound trio",
    "app/services/inbound.py": "T09 fail-close: inbound email/fax processing",
    "app/main.py": "GLOBAL_READ_ONLY / T11 readiness",
}

MIGRATED_NOW_EMPTY = (
    "app/api/v1/routes/qa.py",
    "app/api/v1/routes/liens.py",
    "app/api/v1/routes/evidence.py",
    "app/services/matter_activation.py",
    "app/core/audit.py",
    "app/shared/consent_ledger.py",
    "app/shared/event_store.py",
    "app/shared/policy_registry.py",
)

_PATTERN = "async_session_maker("


def _read(rel: str) -> str:
    return Path(rel).read_text(encoding="utf-8")


def test_migrated_modules_have_no_direct_session_opens():
    for rel in MIGRATED_NOW_EMPTY:
        assert _PATTERN not in _read(rel), (
            f"{rel} regressed: direct session open reintroduced"
        )


def test_seam_implementation_is_the_only_open_in_database_py():
    """The canonical seam is exempt by definition; assert it is the ONLY
    consumer of the pattern in that file so the exemption cannot be abused
    to smuggle a bypass into the helper itself."""
    lines = [ln for ln in _read("app/core/database.py").splitlines()
             if _PATTERN in ln]
    assert len(lines) == 2, (
        f"database.py must hold only the two seam opens, found {lines}"
    )


def test_pending_allowlist_matches_ledger():
    """Guard against silent scope drift: every known pending module must
    still contain its bare opens until its ticket migrates them."""
    missing = [rel for rel in PENDING_BATCHES if _PATTERN not in _read(rel)]
    assert missing == [], (
        f"Allowlist stale — remove migrated modules from PENDING_BATCHES: {missing}"
    )