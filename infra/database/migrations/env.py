"""Alembic migration environment (async).

Resolves the database URL EXCLUSIVELY from the privileged
``TRACE_MIGRATION_DATABASE_URL`` (FND-003-R1 T02 two-URL authority split):
the runtime ``TRACE_DATABASE_URL`` is never used for migrations and cannot
act as a fallback. Runs against Supabase Postgres. This is the ONLY
acceptance-schema path: tests never build the schema from SQLAlchemy
metadata (``metadata.create_all``) — persistence tests run migrations and
require a designated non-production Postgres.
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

from app.models import Base

# Load .env.local WITHOUT override: an explicitly exported
# TRACE_MIGRATION_DATABASE_URL must always win over a checked-out local file.
load_dotenv(".env.local", override=False)

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _db_url() -> str:
    url = os.getenv("TRACE_MIGRATION_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "Set TRACE_MIGRATION_DATABASE_URL (privileged admin connection) "
            "to run migrations. The runtime TRACE_DATABASE_URL is never used."
        )
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_db_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connect_args: dict = {"statement_cache_size": 0}
    if "pooler.supabase.com" in _db_url():
        connect_args["statement_cache_size"] = 0
    connect_args["server_settings"] = {"search_path": "trace"}
    engine = create_async_engine(_db_url(), pool_pre_ping=True, connect_args=connect_args)
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
