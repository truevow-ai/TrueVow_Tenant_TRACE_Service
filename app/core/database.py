"""Async database engine, session factory, and the request-scoped session dep.

TRACE persists only to Supabase/PostgreSQL (INV-TRACE-001). Engines are
Postgres async engines only; there is no SQLite branch and no fallback
persistence backend. The per-request session sets the RLS GUCs
(``app.current_tenant_id`` / ``app.current_user_id`` / ``app.current_user_role``)
so Row-Level Security enforces firm isolation as defense-in-depth.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.deps import AuthContext, get_current_context
from app.core.config import settings


class BlockedInternalTenantContext(RuntimeError):
    """Raised when operational work lacks trustworthy tenant identity.

    Fail-closed contract (FND-003-R1): internal paths needing tenant-owned
    data must carry explicit context from an authenticated/verified
    authority. RLS is never weakened to avoid this condition.
    """


def _create_engine(url: str, *, search_path: str = ""):
    connect_args: dict = {}
    if "pooler.supabase.com" in url:
        connect_args["statement_cache_size"] = 0
    if search_path:
        connect_args["server_settings"] = {"search_path": search_path}
    return create_async_engine(url, pool_pre_ping=True, connect_args=connect_args, future=True)


engine = _create_engine(settings.effective_database_url, search_path="trace")
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

phi_engine = _create_engine(settings.effective_phi_database_url, search_path="trace_phi")
phi_session_maker = async_sessionmaker(phi_engine, expire_on_commit=False, class_=AsyncSession)


async def get_db(
    ctx: AuthContext = Depends(get_current_context),
) -> AsyncGenerator[AsyncSession, None]:
    """Yield a firm-scoped session. Requires an authenticated caller.

    Always Postgres: the RLS GUCs are set transaction-locally via
    parameterized ``set_config`` (FND-003 hardening) — identity values are
    bound as parameters, never interpolated into SQL strings.
    """
    async with async_session_maker() as session:
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": ctx.firm_id},
        )
        await session.execute(
            text("SELECT set_config('app.current_user_id', :user_id, true)"),
            {"user_id": ctx.user_id},
        )
        await session.execute(
            text("SELECT set_config('app.current_user_role', :role, true)"),
            {"role": ctx.role or ""},
        )
        yield session


@asynccontextmanager
async def internal_tenant_session(
    *,
    tenant_id: str | uuid.UUID,
    user_id: str | uuid.UUID | None = None,
    role: str | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an operational session carrying explicit tenant context.

    The canonical seam for INTERNAL work outside the request cycle (audit
    writer, activation projection, scheduled jobs): identical parameterized,
    transaction-local GUCs as :func:`get_db`. Fails closed when no trusted
    tenant identity is supplied — an unscoped internal session can never be
    created from this seam.
    """
    tenant = str(tenant_id or "").strip()
    if not tenant:
        raise BlockedInternalTenantContext(
            "internal tenant session requires explicit tenant context"
        )
    async with async_session_maker() as session:
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": tenant},
        )
        if user_id:
            await session.execute(
                text("SELECT set_config('app.current_user_id', :user_id, true)"),
                {"user_id": str(user_id)},
            )
        if role:
            await session.execute(
                text("SELECT set_config('app.current_user_role', :role, true)"),
                {"role": role},
            )
        yield session
