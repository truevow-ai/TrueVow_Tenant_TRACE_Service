"""Async database engine, session factory, and the request-scoped session dep.

On Postgres, the per-request session sets the RLS GUCs
(``app.current_tenant_id`` / ``app.current_user_id`` / ``app.current_user_role``)
so Row-Level Security enforces firm isolation as defense-in-depth. When no
database is configured the engine falls back to in-memory SQLite (dev/test),
where isolation is enforced by application-level filtering.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.auth.deps import AuthContext, get_current_context
from app.core.config import settings


def _create_engine(url: str):
    if url.startswith("sqlite"):
        return create_async_engine(
            url,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
            future=True,
        )
    connect_args: dict = {}
    if "pooler.supabase.com" in url:
        # Supabase transaction pooler (pgBouncer) requires disabling the prepared
        # statement cache.
        connect_args["statement_cache_size"] = 0
    return create_async_engine(url, pool_pre_ping=True, connect_args=connect_args, future=True)


engine = _create_engine(settings.effective_database_url)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def is_postgres() -> bool:
    return engine.dialect.name == "postgresql"


async def get_db(
    ctx: AuthContext = Depends(get_current_context),
) -> AsyncGenerator[AsyncSession, None]:
    """Yield a firm-scoped session. Requires an authenticated caller."""
    async with async_session_maker() as session:
        if is_postgres():
            await session.execute(
                text("SET LOCAL app.current_tenant_id = :t"), {"t": ctx.firm_id}
            )
            await session.execute(
                text("SET LOCAL app.current_user_id = :u"), {"u": ctx.user_id}
            )
            await session.execute(
                text("SET LOCAL app.current_user_role = :r"), {"r": ctx.role or ""}
            )
        yield session
