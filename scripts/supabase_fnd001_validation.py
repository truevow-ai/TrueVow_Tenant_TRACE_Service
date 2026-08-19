#!/usr/bin/env python3
"""FND-001 Supabase validation evidence collector (READ-ONLY).

Run against a DESIGNATED disposable/non-production Supabase project only —
never production, never a runtime database:

    $env:TRACE_SUPABASE_VALIDATION_URL="postgresql://<user>:<pw>@<host>:<port>/postgres"
    $env:TRACE_SUPABASE_VALIDATION_PHI_URL="..."   # optional; defaults to the above
    python scripts/supabase_fnd001_validation.py

Expected migration pre-step (performed separately, against THAT project only,
by the reviewer who owns its credentials):

    $env:TRACE_DATABASE_URL=<same URL>; alembic upgrade head

This script intentionally never runs DDL and never writes — it refuses to run
migrations and collects read-only evidence only.

Output is masked: credentials are never printed; only scheme/host/port/db are
shown. Produces the evidence set required by TRACE-FND-001-R1 §3:

    masked project reference/host, PostgreSQL version, SELECT 1,
    alembic current, alembic heads, version_num,
    alembic_version.version_num data type / max length,
    trace schema table count, trace_phi schema table count,
    GET /ready and GET /health responses,
    operational + PHI engine connection proof,
    no-sqlite proof (dialect + module check)
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from urllib.parse import urlsplit


def mask(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://***@{parts.hostname}:{parts.port or 5432}{parts.path}"


def main() -> None:
    op_url = os.environ.get("TRACE_SUPABASE_VALIDATION_URL", "")
    phi_url = os.environ.get(
        "TRACE_SUPABASE_VALIDATION_PHI_URL", op_url
    )
    if not op_url:
        sys.exit(
            "TRACE_SUPABASE_VALIDATION_URL is required (designated "
            "non-production Supabase project). Refusing to use any other URL."
        )
    if "pooler.supabase.com" not in op_url and "supabase.co" not in op_url:
        sys.exit(
            "TRACE_SUPABASE_VALIDATION_URL does not look like a Supabase "
            "endpoint; this script validates Supabase only."
        )

    os.environ["TRACE_DATABASE_URL"] = op_url
    os.environ["TRACE_PHI_DATABASE_URL"] = phi_url
    os.environ["AUTH_MODE"] = "local"
    os.environ["LOCAL_JWT_SECRET"] = "test-secret-at-least-32-bytes-long-000"
    os.environ.pop("DATABASE_URL", None)
    os.environ.pop("PHI_DATABASE_URL", None)

    from sqlalchemy import text

    from app.core.database import async_session_maker, engine, phi_engine, phi_session_maker
    from app.main import app as fastapi_app

    print("=== FND-001 SUPABASE VALIDATION (READ-ONLY) ===")
    print(f"operational: {mask(op_url)}")
    print(f"phi:         {mask(phi_url)}")
    print(f"engine dialect: {engine.dialect.name} / phi: {phi_engine.dialect.name}")
    print(f"aiosqlite imported: {'aiosqlite' in sys.modules}")
    print()

    async def collect() -> None:
        async with async_session_maker() as session:
            version = (await session.execute(text("SHOW server_version"))).scalar()
            one = (await session.execute(text("SELECT 1"))).scalar()
            rev = (await session.execute(
                text("SELECT version_num FROM alembic_version")
            )).scalar()
            col = (await session.execute(text(
                "SELECT data_type, character_maximum_length "
                "FROM information_schema.columns "
                "WHERE table_schema = current_schema() "
                "AND table_name = 'alembic_version' "
                "AND column_name = 'version_num'"
            ))).first()
            trace_count = (await session.execute(text(
                "SELECT count(*) FROM pg_tables WHERE schemaname = 'trace'"
            ))).scalar()
            phi_count = (await session.execute(text(
                "SELECT count(*) FROM pg_tables WHERE schemaname = 'trace_phi'"
            ))).scalar()
        async with phi_session_maker() as phi_session:
            phi_one = (await phi_session.execute(text("SELECT 1"))).scalar()

        print(f"PostgreSQL version: {version}")
        print(f"SELECT 1 (operational): {one}")
        print(f"SELECT 1 (phi engine):  {phi_one}")
        print(f"version_num: {rev}")
        print(f"alembic_version.version_num column: {col[0]} max_length={col[1]}")
        print(f"trace schema tables: {trace_count}")
        print(f"trace_phi schema tables: {phi_count}")

    asyncio.run(collect())

    for cmd in (["alembic", "current"], ["alembic", "heads"]):
        result = subprocess.run([sys.executable, "-m", *cmd], capture_output=True, text=True)
        print(f"$ alembic {' '.join(cmd[1:])} -> exit {result.returncode}")
        print(result.stdout.strip() or result.stderr.strip())

    from httpx import ASGITransport, AsyncClient

    async def http_checks() -> None:
        transport = ASGITransport(app=fastapi_app)
        async with AsyncClient(transport=transport, base_url="http://validation") as client:
            ready = await client.get("/ready")
            health = await client.get("/health")
        print(f"GET /ready  -> {ready.status_code} {ready.text[:400]}")
        print(f"GET /health -> {health.status_code} {health.text[:200]}")

    asyncio.run(http_checks())

    print("=== VALIDATION COLLECTED (no DDL, no writes were performed) ===")
    print("next: compare version_num to expected head; capture output for Gate 001.")


if __name__ == "__main__":
    main()
