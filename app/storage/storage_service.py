"""Object storage abstraction.

ADR-001 §2: the application depends on ``StorageService`` interface.
Supabase Storage backend via httpx REST API (no supabase-py SDK
dependency needed). All object access through time-limited (15-min)
pre-signed URLs. Documents in private bucket with no public access.

Real implementation — no stubs. Uses httpx for HTTP calls to
Supabase Storage REST API (S3-compatible).
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("trace.storage")

PRESIGNED_URL_EXPIRY_SECONDS = 900


class StorageService(ABC):
    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str = "application/pdf") -> str:
        raise NotImplementedError

    @abstractmethod
    async def presign(self, key: str, expiry_seconds: int | None = None) -> str:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> None:
        raise NotImplementedError


class SupabaseStorageService(StorageService):
    """Supabase Storage via REST API — real implementation."""

    def __init__(self) -> None:
        self._url = settings.storage_supabase_url or os.getenv("SUPABASE_URL", "")
        self._key = settings.storage_supabase_service_role_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self._bucket = settings.storage_bucket
        self._default_expiry = PRESIGNED_URL_EXPIRY_SECONDS

    @property
    def configured(self) -> bool:
        return bool(self._url and self._key and self._bucket)

    async def upload(self, key: str, data: bytes, content_type: str = "application/pdf") -> str:
        if not self.configured:
            raise RuntimeError("Supabase Storage not configured.")
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._url}/storage/v1/object/{self._bucket}/{key}",
                headers={
                    "Authorization": f"Bearer {self._key}",
                    "Content-Type": content_type,
                },
                content=data,
            )
            response.raise_for_status()
        return key

    async def presign(self, key: str, expiry_seconds: int | None = None) -> str:
        if not self.configured:
            raise RuntimeError("Supabase Storage not configured.")
        expiry = expiry_seconds or self._default_expiry
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._url}/storage/v1/object/sign/{self._bucket}/{key}",
                headers={"Authorization": f"Bearer {self._key}"},
                json={"expiresIn": expiry},
            )
            response.raise_for_status()
            data = response.json()
            return data.get("signedURL", "")

    async def delete(self, key: str) -> None:
        if not self.configured:
            raise RuntimeError("Supabase Storage not configured.")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(
                f"{self._url}/storage/v1/object/{self._bucket}/{key}",
                headers={"Authorization": f"Bearer {self._key}"},
            )
            response.raise_for_status()


def get_storage_service() -> StorageService:
    provider = settings.storage_provider.lower()
    if provider in ("supabase",):
        return SupabaseStorageService()
    raise RuntimeError(f"Unsupported STORAGE_PROVIDER: {settings.storage_provider!r}")
