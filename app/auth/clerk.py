"""Token verification.

Mirrors the platform convention (INTAKE ``app/middleware/auth.py``):

* ``AUTH_MODE=clerk`` — production/staging. Verifies a Clerk JWT via JWKS (RS256).
* ``AUTH_MODE=local`` — dev/test only. Verifies a local HS256 JWT.

Production must run in ``clerk`` mode; ``app.main`` enforces that at startup.
"""

from __future__ import annotations

import threading
import time

import jwt
from jwt import PyJWKClient

from app.core.config import settings


class _JWKSCache:
    """Thread-safe, TTL-cached PyJWKClient for the Clerk JWKS endpoint."""

    def __init__(self) -> None:
        self._client: PyJWKClient | None = None
        self._fetched_at: float = 0.0
        self._lock = threading.Lock()

    def client(self) -> PyJWKClient:
        with self._lock:
            now = time.time()
            if self._client is None or (now - self._fetched_at) > settings.clerk_jwks_cache_ttl:
                if not settings.clerk_jwks_url:
                    raise ValueError("CLERK_JWKS_URL is not configured for clerk auth mode.")
                self._client = PyJWKClient(settings.clerk_jwks_url)
                self._fetched_at = now
            return self._client


_jwks_cache = _JWKSCache()


def verify_token(token: str) -> dict:
    """Verify a bearer token and return its claims. Raises jwt.PyJWTError on failure."""
    if settings.auth_mode == "clerk":
        signing_key = _jwks_cache.client().get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.clerk_audience or None,
            issuer=settings.clerk_issuer or None,
            options={"verify_aud": bool(settings.clerk_audience)},
        )

    # local mode (dev/test)
    return jwt.decode(
        token,
        settings.local_jwt_secret,
        algorithms=[settings.local_jwt_algorithm],
        options={"verify_aud": False},
    )
