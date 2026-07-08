"""Application configuration.

Uses pydantic-settings, matching the TrueVow platform convention (see FM
``app/core/config.py``). Values load from environment and ``.env`` / ``.env.local``.
Secrets are never hardcoded; production supplies them via Fly.io secrets.
"""

from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- App ---
    app_name: str = "TrueVow TRACE Service"
    app_version: str = "0.1.0"
    environment: str = "development"  # development | staging | production

    # --- Auth (Clerk; platform standard) ---
    # local: dev/test HS256 tokens. clerk: production JWKS RS256.
    auth_mode: str = "local"
    local_jwt_secret: str = "insecure-dev-secret-change-me"
    local_jwt_algorithm: str = "HS256"
    clerk_jwks_url: str = ""
    clerk_issuer: str = ""
    clerk_audience: str = ""
    clerk_jwks_cache_ttl: int = 3600

    # --- Databases ---
    # Operational DB (Supabase Postgres). If unset, falls back to in-memory SQLite.
    trace_database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TRACE_DATABASE_URL", "DATABASE_URL"),
    )
    # Separate PHI store (Supabase Postgres, pgcrypto AES-256).
    trace_phi_database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TRACE_PHI_DATABASE_URL", "PHI_DATABASE_URL"),
    )
    # Application-level AES-256-GCM key for PHI columns (base64 or raw). In
    # production this is sourced from KMS/Secrets Manager, never committed.
    trace_phi_encryption_key: str = ""

    # --- Object storage (S3 + SSE-KMS + BAA) ---
    storage_provider: str = "s3"
    trace_s3_bucket: str = ""
    trace_s3_region: str = "us-west-2"
    trace_s3_kms_key_id: str = ""
    trace_aws_access_key_id: str = ""
    trace_aws_secret_access_key: str = ""
    presigned_url_expiry_seconds: int = 900  # 15 minutes (HIPAA data-flow requirement)

    # --- Observability ---
    otel_exporter_otlp_endpoint: str = ""
    sentry_dsn: str = ""

    # --- Cloud fax (Fax.Plus) ---
    fax_api_key: str = ""
    fax_return_number: str = ""
    fax_webhook_secret: str = ""
    # Reference to the signed HIPAA authorization on file (set during onboarding).
    hipaa_auth_reference: str = "PENDING-ONBOARDING"

    # --- CORS ---
    cors_allow_origins: str = "*"

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def effective_database_url(self) -> str:
        """Runtime operational DB URL as an async SQLAlchemy URL.

        Falls back to in-memory SQLite when no database is configured, so the
        service boots (and the test suite runs) without live cloud.
        """
        url = self.trace_database_url
        if not url:
            return "sqlite+aiosqlite:///:memory:"
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def effective_phi_database_url(self) -> str:
        """Runtime PHI-store DB URL (separate instance). SQLite fallback for tests."""
        url = self.trace_phi_database_url
        if not url:
            return "sqlite+aiosqlite:///:memory:"
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()
