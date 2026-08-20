"""Support helpers for standalone TRACE verification/seeding scripts.

Deliberately side-effect free apart from ``require_test_database``, which
prepares the environment BEFORE any application module is imported so the
fail-closed database layer resolves to the designated non-production test
database — never a runtime/production URL, never SQLite.

FND001-INV-08: destructive/reset behavior requires BOTH:
    TRACE_TEST_PG_URL=<designated non-production Postgres>
    TRACE_TEST_ALLOW_DESTRUCTIVE=TRUEVOW_NONPROD_TEST_DB
"""

from __future__ import annotations

import os
import sys
import uuid

DESTRUCTIVE_TOKEN = "TRUEVOW_NONPROD_TEST_DB"


def require_test_database() -> None:
    """Resolve test DB configuration into TRACE_* names, or exit clearly.

    Must be called before importing any ``app.*`` module. Fails with a clear
    message when either safety guard is absent.
    """
    test_pg = os.environ.get("TRACE_TEST_PG_URL", "")
    destructive = os.environ.get("TRACE_TEST_ALLOW_DESTRUCTIVE", "")
    if not test_pg:
        sys.exit(
            "TRACE_TEST_PG_URL is required: a designated non-production "
            "Postgres database. Runtime/production URLs are never accepted."
        )
    if destructive != DESTRUCTIVE_TOKEN:
        sys.exit(
            "TRACE_TEST_ALLOW_DESTRUCTIVE must equal "
            f"'{DESTRUCTIVE_TOKEN}' before this script may write to or reset "
            "the test database."
        )
    os.environ["TRACE_DATABASE_URL"] = test_pg
    os.environ["TRACE_PHI_DATABASE_URL"] = os.environ.get(
        "TRACE_TEST_PHI_PG_URL", test_pg
    )
    # Legacy aliases must not compete during settings resolution.
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("PHI_DATABASE_URL", None)
    # FND-002: PHI encryption has no fallback key. Synthetic-seeding scripts
    # must carry an explicit synthetic key; provide the documented test value
    # only when the operator has not supplied one.
    os.environ.setdefault(
        "TRACE_PHI_ENCRYPTION_KEY", "0123456789abcdef0123456789abcdef"
    )


def make_local_token(
    firm_id: str,
    user_id: str | None = None,
    role: str = "attorney",
) -> str:
    """Generate a locally-signed HS256 token for synthetic/local runs."""
    import jwt as pyjwt

    secret = os.environ.get(
        "LOCAL_JWT_SECRET", "test-secret-at-least-32-bytes-long-000"
    )
    payload = {
        "sub": user_id or str(uuid.uuid4()),
        "firm_id": firm_id,
        "role": role,
        "mfa": True,
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


def auth_header(firm_id: str, user_id: str | None = None) -> dict:
    return {"Authorization": f"Bearer {make_local_token(firm_id, user_id=user_id)}"}
