"""Declarative base + shared mixins.

ADR-001 §25: operational tables live in the ``trace`` schema in production.
Schema routing is handled by the Alembic migration (0004_trace_schema_and_pipeline_audit_log)
and the ``search_path`` in the database connection URL — not hardcoded on the model
metadata. This keeps the test suite compatible with SQLite (which has no schemas).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
