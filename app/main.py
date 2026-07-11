"""TRACE FastAPI application.

Wires middleware (correlation id + audit), Clerk-based auth, plain-English error
handling, a public ``/health`` probe, and the firm-scoped v1 API under
``/api/v1/trace``. Production must run in Clerk auth mode — enforced at startup.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import router as v1_router
from app.core.config import settings
from app.core.errors import install_error_handlers
from app.core.logging import get_logger
from app.core.middleware import audit_middleware, correlation_id_middleware

logger = get_logger("trace.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # HIPAA safeguard: never run production without Clerk-verified auth.
    if settings.is_production and settings.auth_mode != "clerk":
        raise RuntimeError(
            "AUTH_MODE=local is forbidden in production. Set AUTH_MODE=clerk and CLERK_JWKS_URL."
        )
    logger.info(
        "TRACE starting: env=%s auth_mode=%s db=%s",
        settings.environment,
        settings.auth_mode,
        "postgres" if (settings.trace_database_url) else "sqlite(fallback)",
    )
    yield
    logger.info("TRACE shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

# Middleware: correlation_id is added last so it runs outermost (sets the id
# before audit_middleware records it).
app.middleware("http")(audit_middleware)
app.middleware("http")(correlation_id_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_allow_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

install_error_handlers(app)
app.include_router(v1_router, prefix="/api/v1/trace")


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {
        "status": "healthy",
        "service": "trace",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/test-mistral-ocr", tags=["test"])
async def test_mistral_ocr():
    import base64, os
    from mistralai.client import Mistral

    api_key = os.environ.get("MISTRAL_API_KEY", "")
    if not api_key:
        return {"status": "error", "reason": "MISTRAL_API_KEY not set"}

    try:
        from PIL import Image
        import io

        img = Image.new("RGB", (300, 80), "white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        b = base64.b64encode(buf.getvalue()).decode()

        client = Mistral(api_key=api_key)
        r = client.ocr.process(
            model="mistral-ocr-latest",
            document={"type": "image_url", "image_url": f"data:image/png;base64,{b}"},
            include_image_base64=False,
        )
        return {
            "status": "ok",
            "pages": len(r.pages),
            "markdown_preview": r.pages[0].markdown[:200] if r.pages else "",
        }
    except Exception as exc:
        return {"status": "error", "reason": str(exc)}
