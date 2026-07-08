"""HTTP middleware: correlation id + per-request audit logging."""

from __future__ import annotations

import uuid

from fastapi import Request

from app.core.audit import write_audit
from app.core.logging import get_logger

logger = get_logger("trace.middleware")

_API_PREFIX = "/api/v1/trace/"


async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("x-correlation-id") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


def _resource_type(path: str) -> str:
    if not path.startswith(_API_PREFIX):
        return "root"
    rest = path[len(_API_PREFIX):]
    return rest.split("/", 1)[0] or "root"


async def audit_middleware(request: Request, call_next):
    """Record an audit_log row for every authenticated API call.

    Runs after the route (so ``request.state.auth`` is populated by the auth
    dependency). Best-effort: an audit failure is logged but never breaks the
    response.
    """
    response = await call_next(request)

    ctx = getattr(request.state, "auth", None)
    if ctx is not None and request.url.path.startswith(_API_PREFIX):
        try:
            resource_type = _resource_type(request.url.path)
            await write_audit(
                actor_id=ctx.user_id,
                actor_type="ATTORNEY",
                action=f"{request.method} {request.url.path}",
                resource_type=resource_type,
                # Collection-level actions are scoped to the firm.
                resource_id=ctx.firm_id,
                firm_id=ctx.firm_id,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                correlation_id=getattr(request.state, "correlation_id", None),
                details={"status_code": response.status_code},
            )
        except Exception:  # noqa: BLE001 — audit must never break the request
            logger.exception("Failed to write audit_log entry")

    return response
