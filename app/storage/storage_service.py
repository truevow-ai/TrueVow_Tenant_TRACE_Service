"""Object storage abstraction.

ADR-001 §2: the application depends on ``StorageService`` interface.
The Supabase implementation uses the supabase-py SDK with the service
role key (never exposed to the browser). All object access goes through
time-limited (15-min) pre-signed URLs. Documents live in a private bucket
with no public access policy.

Swappable by ``STORAGE_PROVIDER`` env var.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("trace.storage")

PRESIGNED_URL_EXPIRY_SECONDS = 900


class StorageService(ABC):
    """Encrypted object storage for medical-record bytes (never stored in the DB)."""

    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str = "application/pdf") -> str:
        """Store bytes under ``key`` (encrypted at rest). Returns the object key."""

    @abstractmethod
    async def presign(self, key: str, expiry_seconds: int | None = None) -> str:
        """Return a time-limited URL the browser can fetch directly."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete the object (used for retention/destruction workflows)."""


class SupabaseStorageService(StorageService):
    """Supabase Storage client — private bucket, 15-min signed URLs.

    Uses the service role key (SUPABASE_SERVICE_ROLE_KEY) which must
    never be exposed to the browser. Follows the pattern defined in the
    Technical Spec §2.1.
    """

    def __init__(self) -> None:
        self._bucket = settings.storage_bucket
        self._client = None
        self._default_expiry = PRESIGNED_URL_EXPIRY_SECONDS

    @property
    def configured(self) -> bool:
        return bool(settings.storage_supabase_url and settings.storage_supabase_service_role_key)

    def _get_client(self):
        if self._client is None:
            from supabase import create_client

            self._client = create_client(
                settings.storage_supabase_url,
                settings.storage_supabase_service_role_key,
            )
        return self._client

    async def upload(self, key: str, data: bytes, content_type: str = "application/pdf") -> str:
        if not self.configured:
            raise RuntimeError("Supabase Storage is not configured (SUPABASE_URL / key missing).")
        self._get_client().storage.from_(self._bucket).upload(
            path=key,
            file=data,
            file_options={"content-type": content_type, "upsert": False},
        )
        return key

    async def presign(self, key: str, expiry_seconds: int | None = None) -> str:
        if not self.configured:
            raise RuntimeError("Supabase Storage is not configured (SUPABASE_URL / key missing).")
        result = self._get_client().storage.from_(self._bucket).create_signed_url(
            path=key,
            expires_in=expiry_seconds or self._default_expiry,
        )
        return result["signedURL"]

    async def delete(self, key: str) -> None:
        if not self.configured:
            raise RuntimeError("Supabase Storage is not configured (SUPABASE_URL / key missing).")
        self._get_client().storage.from_(self._bucket).remove([key])


def get_storage_service() -> StorageService:
    provider = settings.storage_provider.lower()
    if provider in ("supabase",):
        return SupabaseStorageService()
    raise RuntimeError(f"Unsupported STORAGE_PROVIDER: {settings.storage_provider!r}")
