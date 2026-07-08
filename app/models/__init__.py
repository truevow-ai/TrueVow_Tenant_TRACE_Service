"""SQLAlchemy models.

Models use portable column types (``Uuid``, ``JSON``, ``String``) so the same
metadata runs on Supabase Postgres in production and on in-memory SQLite in the
test suite. The full Section 3.1 DDL (with Postgres-native ``INET``/``JSONB``/
``DATERANGE`` and pgcrypto PHI columns) lives in the Alembic migration.
"""

from app.models.audit import AuditLog
from app.models.base import Base, TimestampMixin
from app.models.case import Case

__all__ = ["Base", "TimestampMixin", "Case", "AuditLog"]
