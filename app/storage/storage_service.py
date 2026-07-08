"""Object storage abstraction.

Per ADR-000 the application never talks to a cloud SDK directly — it depends on
this ``StorageService`` interface. The S3 implementation follows SETTLE's
``s3_service.py`` pattern, upgraded for PHI: server-side encryption with a
customer-managed KMS key and time-limited (15 min) pre-signed URLs. Swappable by
``STORAGE_PROVIDER`` so a future move to GCS/Azure needs only a new implementation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("trace.storage")


class StorageService(ABC):
    """Encrypted object storage for medical-record bytes (never stored in the DB)."""

    @abstractmethod
    def upload(self, key: str, data: bytes, content_type: str = "application/pdf") -> str:
        """Store bytes under ``key`` (encrypted at rest). Returns the object key."""

    @abstractmethod
    def presign(self, key: str, expiry_seconds: int | None = None) -> str:
        """Return a time-limited URL the browser can fetch directly."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete the object (used for retention/destruction workflows)."""


class S3StorageService(StorageService):
    """AWS S3 with SSE-KMS. boto3 is imported lazily so the dep is optional in dev."""

    def __init__(self) -> None:
        self._bucket = settings.trace_s3_bucket
        self._region = settings.trace_s3_region
        self._kms_key_id = settings.trace_s3_kms_key_id
        self._default_expiry = settings.presigned_url_expiry_seconds
        self._client = None  # lazy

    @property
    def configured(self) -> bool:
        return bool(self._bucket and self._kms_key_id)

    def _get_client(self):
        if self._client is None:
            import boto3  # type: ignore[import-untyped]  # lazy import

            self._client = boto3.client(
                "s3",
                region_name=self._region,
                aws_access_key_id=settings.trace_aws_access_key_id or None,
                aws_secret_access_key=settings.trace_aws_secret_access_key or None,
            )
        return self._client

    def upload(self, key: str, data: bytes, content_type: str = "application/pdf") -> str:
        if not self.configured:
            raise RuntimeError("S3 storage is not configured (bucket/KMS key missing).")
        self._get_client().put_object(
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="aws:kms",
            SSEKMSKeyId=self._kms_key_id,
        )
        return key

    def presign(self, key: str, expiry_seconds: int | None = None) -> str:
        if not self.configured:
            raise RuntimeError("S3 storage is not configured (bucket/KMS key missing).")
        return self._get_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expiry_seconds or self._default_expiry,
        )

    def delete(self, key: str) -> None:
        if not self.configured:
            raise RuntimeError("S3 storage is not configured (bucket/KMS key missing).")
        self._get_client().delete_object(Bucket=self._bucket, Key=key)


def get_storage_service() -> StorageService:
    provider = settings.storage_provider.lower()
    if provider == "s3":
        return S3StorageService()
    raise RuntimeError(f"Unsupported STORAGE_PROVIDER: {settings.storage_provider!r}")
