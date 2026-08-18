"""TRACE-FND-001 — Supabase/Postgres-only database configuration.

Pure unit tests (no database connection) proving fail-closed database
resolution per FND001-INV-01..INV-05. The designated-Postgres acceptance
path is exercised by the persistence suite under TRACE_TEST_PG_URL.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from app.core.config import Settings


def _settings(**kwargs) -> Settings:
    """Instantiate Settings without dotenv loading.

    The DB fields carry ``validation_alias`` entries, so init values must be
    keyed by the env-var alias (e.g. TRACE_DATABASE_URL), not the field name.
    """
    aliased = {key.upper(): value for key, value in kwargs.items()}
    return Settings(_env_file=None, **aliased)


class TestDatabaseUrlResolution:
    def test_postgresql_url_normalizes_to_asyncpg(self):
        s = _settings(trace_database_url="postgresql://u:p@host:5432/db")
        assert s.effective_database_url == "postgresql+asyncpg://u:p@host:5432/db"

    def test_postgres_scheme_url_normalizes(self):
        s = _settings(trace_database_url="postgres://u:p@host:5432/db")
        assert s.effective_database_url == "postgresql+asyncpg://u:p@host:5432/db"

    def test_asyncpg_url_passthrough(self):
        s = _settings(trace_database_url="postgresql+asyncpg://u:p@host:5432/db")
        assert s.effective_database_url == "postgresql+asyncpg://u:p@host:5432/db"

    def test_missing_operational_db_fails_closed(self):
        s = _settings(trace_database_url=None, trace_phi_database_url="postgresql://u:p@h/db")
        with pytest.raises(RuntimeError, match="TRACE_DATABASE_URL"):
            _ = s.effective_database_url

    def test_missing_phi_db_fails_closed(self):
        s = _settings(trace_database_url="postgresql://u:p@h/db", trace_phi_database_url=None)
        with pytest.raises(RuntimeError, match="TRACE_PHI_DATABASE_URL"):
            _ = s.effective_phi_database_url

    @pytest.mark.parametrize("bad_url", [
        "sqlite:///local.db",
        "sqlite+aiosqlite:///:memory:",
        "mysql://u:p@host/db",
        "postgresql+psycopg2://u:p@host/db",
        "https://example.com/db",
        "not-a-url",
    ])
    def test_non_postgres_urls_rejected(self, bad_url):
        s = _settings(trace_database_url=bad_url, trace_phi_database_url="postgresql://u:p@h/db")
        with pytest.raises(RuntimeError, match="not a PostgreSQL URL"):
            _ = s.effective_database_url

    def test_phi_db_non_postgres_rejected(self):
        s = _settings(trace_database_url="postgresql://u:p@h/db", trace_phi_database_url="sqlite:///x.db")
        with pytest.raises(RuntimeError, match="not a PostgreSQL URL"):
            _ = s.effective_phi_database_url


class TestStartupFailsClosed:
    @pytest.mark.parametrize("env_patch", [
        {"TRACE_DATABASE_URL": ""},
        {"TRACE_DATABASE_URL": "sqlite:///forbidden.db", "TRACE_PHI_DATABASE_URL": "postgresql://u:p@h/db"},
        {"TRACE_PHI_DATABASE_URL": ""},
    ])
    def test_app_import_fails_under_forbidden_db_config(self, env_patch):
        """Engine construction must fail when DB config is missing or non-Postgres."""
        env = {k: v for k, v in os.environ.items()}
        env.update({
            "ENVIRONMENT": "test",
            "AUTH_MODE": "local",
            "LOCAL_JWT_SECRET": "test-secret-at-least-32-bytes-long-000",
            "TRACE_DATABASE_URL": env_patch.get("TRACE_DATABASE_URL", "postgresql://u:p@127.0.0.1:1/db"),
            "TRACE_PHI_DATABASE_URL": env_patch.get("TRACE_PHI_DATABASE_URL", "postgresql://u:p@127.0.0.1:1/db"),
        })
        env.pop("DATABASE_URL", None)
        env.pop("PHI_DATABASE_URL", None)
        env.pop("TRACE_TEST_PG_URL", None)
        result = subprocess.run(
            [sys.executable, "-c", "import app.core.database"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode != 0, (
            f"startup must fail closed for env {env_patch}; "
            f"stdout={result.stdout} stderr={result.stderr}"
        )
