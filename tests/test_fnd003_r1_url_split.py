"""FND-003-R1 T02 — two-URL authority split invariants.

Proves the privileged migration URL cannot leak into runtime code paths and
that Alembic fails loudly without it (no runtime-URL fallback, either
direction).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ALLOWED_RUNTIME_FILES = {"config.py"}


def test_runtime_code_never_references_migration_url():
    """Only the settings module may know the privileged URL exists."""
    app_root = Path("app")
    violations: list[str] = []
    for path in app_root.rglob("*.py"):
        if path.name in ALLOWED_RUNTIME_FILES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "migration_database_url" in text or "TRACE_MIGRATION_DATABASE_URL" in text:
            violations.append(str(path))
    assert violations == []


def test_alembic_fails_loud_without_privileged_url():
    """No TRACE_MIGRATION_DATABASE_URL → hard failure even with runtime URL set.

    Deterministic: env.py raises before any connection is attempted, so this
    runs in the unguarded lane too.
    """
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("TRACE_MIGRATION")
    }
    env["TRACE_DATABASE_URL"] = "postgresql://unit:unit@127.0.0.1:1/unit"
    env["ENVIRONMENT"] = "test"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode != 0
    combined = (result.stderr or "") + (result.stdout or "")
    assert "TRACE_MIGRATION_DATABASE_URL" in combined
