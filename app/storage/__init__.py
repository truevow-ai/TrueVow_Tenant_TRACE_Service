"""Object storage abstraction."""

from app.storage.storage_service import StorageService, get_storage_service

__all__ = ["StorageService", "get_storage_service"]
