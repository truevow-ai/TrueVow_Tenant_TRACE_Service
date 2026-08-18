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
    # Operational DB (Supabase Postgres). REQUIRED — TRACE persists only to
    # Supabase/PostgreSQL (INV-TRACE-001). Missing or non-Postgres
    # configuration fails closed; there is no other persistence backend.
    trace_database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TRACE_DATABASE_URL", "DATABASE_URL"),
    )
    # Separate PHI store (Supabase Postgres, pgcrypto AES-256). REQUIRED.
    trace_phi_database_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("TRACE_PHI_DATABASE_URL", "PHI_DATABASE_URL"),
    )
    # Application-level AES-256-GCM key for PHI columns (base64 or raw). In
    # production this is sourced from KMS/Secrets Manager, never committed.
    trace_phi_encryption_key: str = ""

    # --- Object storage (Supabase Storage) ---
    storage_provider: str = "supabase"
    storage_supabase_url: str = ""
    storage_supabase_service_role_key: str = ""
    storage_bucket: str = "trace-medical-records"
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

    # --- DocuSeal (self-hosted e-signature) ---
    docuseal_api_url: str = ""
    docuseal_api_token: str = ""
    docuseal_webhook_secret: str = ""
    docuseal_signing_link_expiry_days: int = 7

    # --- Email inbound (Resend) ---
    resend_webhook_secret: str = ""

    # --- RETAINER activation inbound ---
    retainer_webhook_secret: str = ""

    # --- NLP backends ---
    nlp_provider_backend: str = "openmed"         # openmed | disabled
    nlp_long_context_backend: str = "disabled"     # disabled | bioclinical_modernbert (Phase 1D)

    # --- Billing LLM (Phase 1D) ---
    llm_backend: str = "disabled"                  # disabled | azure_openai | deepseek_api | anthropic
    llm_phi_allowed: bool = False                  # must be true before any PHI-adjacent prompt

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

    @staticmethod
    def _require_postgres(url: str | None, name: str) -> str:
        """Resolve a database URL to async-SQLAlchemy Postgres form.

        Fail closed (INV-TRACE-001 / INV-TRACE-002): missing configuration or
        any non-PostgreSQL scheme raises — SQLite is never substituted.
        """
        if not url:
            raise RuntimeError(
                f"{name} is not configured. TRACE persists only to "
                "Supabase/PostgreSQL and refuses to start without a database."
            )
        normalized = url
        if normalized.startswith("postgres://"):
            normalized = "postgresql://" + normalized[len("postgres://"):]
        if normalized.startswith("postgresql://"):
            normalized = normalized.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif normalized.startswith("postgresql+asyncpg://"):
            pass
        else:
            raise RuntimeError(
                f"{name} is not a PostgreSQL URL. TRACE supports only "
                "Supabase/PostgreSQL (postgresql:// or postgresql+asyncpg://)."
            )
        return normalized

    @property
    def effective_database_url(self) -> str:
        """Runtime operational DB URL as an async SQLAlchemy Postgres URL.

        Required. Raises RuntimeError when absent or non-Postgres.
        """
        return self._require_postgres(self.trace_database_url, "TRACE_DATABASE_URL")

    @property
    def effective_phi_database_url(self) -> str:
        """Runtime PHI-store DB URL. Required; same fail-closed rule."""
        return self._require_postgres(self.trace_phi_database_url, "TRACE_PHI_DATABASE_URL")


settings = Settings()
