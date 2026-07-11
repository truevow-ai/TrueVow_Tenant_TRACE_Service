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


@app.get("/run-spike", tags=["test"])
async def run_spike():
    """Run Mistral OCR spike against 30 prescription images from GitHub."""
    import base64, io, json, os, urllib.request
    from collections import Counter
    from datetime import datetime, timezone

    import pandas as pd
    from mistralai.client import Mistral

    api_key = os.environ.get("MISTRAL_API_KEY", "")
    if not api_key:
        return {"status": "error", "reason": "MISTRAL_API_KEY not set"}

    BASE = "https://raw.githubusercontent.com/truevow-ai/TrueVow_Tenant_TRACE_Service/main/tests/spike_output/real_hw"

    def download(path):
        with urllib.request.urlopen(f"{BASE}/{path}") as resp:
            return resp.read()

    def wer(gt, ocr):
        gt_w = gt.lower().split()
        ocr_w = ocr.lower().split()
        if not gt_w:
            return 1.0
        m = sum((Counter(gt_w) & Counter(ocr_w)).values())
        return 1.0 - (m / len(gt_w))

    try:
        parquet_bytes = download("train.parquet")
        df = pd.read_parquet(io.BytesIO(parquet_bytes))
    except Exception as exc:
        return {"status": "error", "reason": f"Parquet download: {exc}"}

    client = Mistral(api_key=api_key)
    results = []

    for i in range(min(30, len(df))):
        row = df.iloc[i]
        gt = str(row.get("medicines", "")) if pd.notna(row.get("medicines")) else ""
        if not gt.strip():
            continue

        try:
            img_bytes = download(f"hw_{i:03d}.png")
            b = base64.b64encode(img_bytes).decode()
            r = client.ocr.process(
                model="mistral-ocr-latest",
                document={"type": "image_url", "image_url": f"data:image/png;base64,{b}"},
                include_image_base64=False,
            )
            text = r.pages[0].markdown.strip() if r.pages else ""
            cs = r.pages[0].confidence_scores
            conf = cs.average_page_confidence_score if cs else 0.95
        except Exception as exc:
            text = f"[{type(exc).__name__}]"
            conf = 0.0

        w = wer(gt, text)
        results.append({"id": f"hw_{i:03d}", "gt": gt[:100], "ocr": text[:100], "wer": round(w, 4), "conf": round(conf, 4)})

    wers = [r["wer"] for r in results]
    mean_w = sum(wers) / len(wers) if wers else 1.0
    median_w = sorted(wers)[len(wers) // 2] if wers else 1.0

    if mean_w <= 0.20:
        decision, reason = "none", "Above 80% accuracy"
    elif mean_w <= 0.35:
        decision, reason = "mistral_local", "65-79% accuracy"
    else:
        decision, reason = "mistral_local", "Below 65% accuracy"

    return {
        "status": "ok",
        "engine": "Mistral-OCR-4",
        "total": len(results),
        "mean_wer": round(mean_w, 4),
        "median_wer": round(median_w, 4),
        "accuracy": f"{1 - mean_w:.1%}",
        "decision": decision,
        "reason": reason,
        "results": results[:5],
    }
