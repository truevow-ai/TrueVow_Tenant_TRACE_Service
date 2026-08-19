"""FND-001-R1 safety proofs: the harness can never destroy a runtime database.

These tests run pytest in a SUBPROCESS with controlled environment variables
and verify the conftest safety-guard behavior end to end:

  (a) TRACE_DATABASE_URL alone is NEVER treated as a test database.
  (b) without TRACE_TEST_PG_URL no migration/truncation can run.
  (c) without TRACE_TEST_ALLOW_DESTRUCTIVE no migration/truncation can run.
  (d) with BOTH guards the harness works against the designated test DB
      (positive control; runs only when the outer run has TRACE_TEST_PG_URL).

Persistence tests must FAIL (connection refused to the never-connectable
placeholder) whenever a guard is absent — proving the harness refused to
migrate/truncate anything. The full discriminating power of (a) requires a
reachable designated test database (container/CI environment).
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

# A REAL, reachable test database (docker bridge) — used to prove the harness
# ignores TRACE_DATABASE_URL and honors only the guarded TRACE_TEST_PG_URL.
_REACHABLE_TEST_DB = os.environ.get(
    "TRACE_FND001_SAFETY_DB_URL", "postgresql://trace:trace@172.17.0.3:5432/trace_test"
)

_TARGET = ["tests/test_phi_store.py"]
_NOTICE_MARKER = "TRACE_TEST_PG_URL"

_CLEAN = {
    "TRACE_TEST_PG_URL",
    "TRACE_TEST_PHI_PG_URL",
    "TRACE_TEST_ALLOW_DESTRUCTIVE",
    "TRACE_DATABASE_URL",
    "TRACE_PHI_DATABASE_URL",
    "DATABASE_URL",
    "PHI_DATABASE_URL",
}


def _run_pytest(extra_env: dict[str, str]) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in _CLEAN}
    env.update(extra_env)
    # `-s` keeps capture off so the conftest safety notice is visible in
    # stdout, which these proofs assert on.
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-s", *_TARGET],
        capture_output=True,
        text=True,
        env=env,
        timeout=600,
    )


def _assert_guards_blocked(result: subprocess.CompletedProcess) -> None:
    output = result.stdout + result.stderr
    # Persistence test must fail: engines resolved to the placeholder URL.
    assert result.returncode != 0, (
        f"persistence test unexpectedly passed without safety guards\n{output}"
    )
    # No destructive step ran: the Alembic migration step never executed.
    assert "alembic" not in output.lower(), (
        f"a migration/truncation step ran despite absent guards\n{output}"
    )
    # The safety notice was emitted, telling the operator what is missing.
    assert _NOTICE_MARKER in output


def test_trace_database_url_alone_is_never_a_test_db():
    """(a) A runtime DB URL is ignored; the harness does not touch it."""
    result = _run_pytest({"TRACE_DATABASE_URL": _REACHABLE_TEST_DB})
    _assert_guards_blocked(result)


def test_missing_test_pg_url_cannot_trigger_truncation():
    """(b) Without TRACE_TEST_PG_URL nothing can be migrated or truncated."""
    result = _run_pytest({})
    _assert_guards_blocked(result)


def test_missing_destructive_confirmation_cannot_trigger_truncation():
    """(c) TRACE_TEST_PG_URL alone is not enough — the latch must match."""
    result = _run_pytest({"TRACE_TEST_PG_URL": _REACHABLE_TEST_DB})
    _assert_guards_blocked(result)

    # A wrong latch value is equally rejected.
    result = _run_pytest({
        "TRACE_TEST_PG_URL": _REACHABLE_TEST_DB,
        "TRACE_TEST_ALLOW_DESTRUCTIVE": "WRONG_TOKEN",
    })
    _assert_guards_blocked(result)


@pytest.mark.skipif(
    not os.environ.get("TRACE_TEST_PG_URL"),
    reason="positive control requires the designated test DB (container/CI lane)",
)
def test_guarded_harness_works_against_designated_test_db():
    """(d) With BOTH guards the persistence suite runs against the test DB."""
    result = _run_pytest({
        "TRACE_TEST_PG_URL": _REACHABLE_TEST_DB,
        "TRACE_TEST_ALLOW_DESTRUCTIVE": "TRUEVOW_NONPROD_TEST_DB",
    })
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"guarded persistence run failed:\n{output}"
