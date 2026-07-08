"""Authenticated request context + FastAPI dependency."""

from __future__ import annotations

from dataclasses import dataclass, field

import jwt
from fastapi import HTTPException, Request, status

from app.auth.clerk import verify_token


@dataclass
class AuthContext:
    """The authenticated caller. ``firm_id`` scopes every data access."""

    user_id: str
    firm_id: str
    role: str | None = None
    mfa: bool = False
    claims: dict = field(default_factory=dict)


def _extract_bearer(request: Request) -> str | None:
    header = request.headers.get("authorization")
    if not header:
        return None
    parts = header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


async def get_current_context(request: Request) -> AuthContext:
    """Verify the bearer token and return the caller context.

    Raises 401 for any missing/invalid credential. On success, stashes the
    context on ``request.state.auth`` for the audit middleware.
    """
    token = _extract_bearer(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    try:
        claims = verify_token(token)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session."
        ) from None
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication could not be verified."
        ) from None

    user_id = claims.get("sub")
    # Platform uses Clerk org_id as the firm/tenant identity; local tokens may use firm_id.
    firm_id = claims.get("org_id") or claims.get("firm_id")
    if not user_id or not firm_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is missing the required firm or user identity.",
        )

    ctx = AuthContext(
        user_id=str(user_id),
        firm_id=str(firm_id),
        role=claims.get("role") or claims.get("org_role"),
        mfa=bool(claims.get("two_factor_enabled") or claims.get("mfa", False)),
        claims=claims,
    )
    request.state.auth = ctx
    return ctx
