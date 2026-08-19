"""FND-001A-R1 blocker 1: exported DB configuration must beat .env.local.

Subprocess proof: a conflicting .env.local exists in the working directory,
exported environment variables are set, and importing ``app.main`` must leave
the exported values untouched — in os.environ AND in the resolved Settings.
No database connection is attempted (placeholder URLs, no queries).
"""

from __future__ import annotations

import os
import subprocess
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_EXPORTED_OP = "postgresql://exported:op@127.0.0.1:1/exported_op"
_EXPORTED_PHI = "postgresql://exported:phi@127.0.0.1:1/exported_phi"

_CHILD_SCRIPT = f"""
import os

os.environ["TRACE_DATABASE_URL"] = {_EXPORTED_OP!r}
os.environ["TRACE_PHI_DATABASE_URL"] = {_EXPORTED_PHI!r}
os.environ["ENVIRONMENT"] = "test"
os.environ["AUTH_MODE"] = "local"
os.environ["LOCAL_JWT_SECRET"] = "test-secret-at-least-32-bytes-long-000"
os.environ.pop("DATABASE_URL", None)
os.environ.pop("PHI_DATABASE_URL", None)

import app.main  # noqa: E402,F401 — imports the runtime dotenv loading

from app.core.config import settings

assert os.environ["TRACE_DATABASE_URL"] == {_EXPORTED_OP!r}, (
    "exported TRACE_DATABASE_URL was replaced: %r" % os.environ.get("TRACE_DATABASE_URL")
)
assert os.environ["TRACE_PHI_DATABASE_URL"] == {_EXPORTED_PHI!r}, (
    "exported TRACE_PHI_DATABASE_URL was replaced: %r" % os.environ.get("TRACE_PHI_DATABASE_URL")
)
assert settings.trace_database_url == {_EXPORTED_OP!r}, settings.trace_database_url
assert settings.trace_phi_database_url == {_EXPORTED_PHI!r}, settings.trace_phi_database_url
print("DOTENV_PRECEDENCE_OK")
"""


def test_exported_db_env_beats_conflicting_dotenv(tmp_path):
    conflicting = tmp_path / ".env.local"
    conflicting.write_text(
        "TRACE_DATABASE_URL=postgresql://dotenv:dot@127.0.0.1:1/dotenv_op\n"
        "TRACE_PHI_DATABASE_URL=postgresql://dotenv:dot@127.0.0.1:1/dotenv_phi\n"
        "LOCAL_JWT_SECRET=dotenv-secret-must-not-win\n"
        "AUTH_MODE=clerk\n"
    )
    env = {k: v for k, v in os.environ.items()}
    env.pop("TRACE_DATABASE_URL", None)
    env.pop("TRACE_PHI_DATABASE_URL", None)
    env.pop("DATABASE_URL", None)
    env.pop("PHI_DATABASE_URL", None)
    env["PYTHONPATH"] = _REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")

    result = subprocess.run(
        [sys.executable, "-c", _CHILD_SCRIPT],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        env=env,
        timeout=300,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, f"child failed:\n{output}"
    assert "DOTENV_PRECEDENCE_OK" in output
