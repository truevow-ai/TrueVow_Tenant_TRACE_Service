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


@app.get("/run-pipeline", tags=["test"])
async def run_pipeline_test():
    import json, uuid
    from datetime import date, datetime, timezone

    CASE_ID = uuid.UUID("d379ee9b-19f7-4871-a86e-9684c69a11c3")
    clinical_text = (
        "PATIENT: Maria Rodriguez DOB: 04/12/1985\n"
        "DATE OF SERVICE: 03/15/2024\n"
        "MRI 03/20/2024: C4-C5 disc herniation, C5-C6 bulging disc.\n"
        "TREATMENT: PT 2x/week. Cyclobenzaprine 10mg, Ibuprofen 800mg.\n"
        "REFERRAL: Dr. James Wilson, Orthopedic Surgery.\n"
        "DISCHARGE: Released from Cedars-Sinai ER."
    )

    from app.services.chronology import build_chronology
    from app.services.export import ChronologyExporter

    redacted = [{"redacted_text": clinical_text, "page_number": 1, "document_id": str(uuid.uuid4())}]
    chron = await build_chronology(CASE_ID, redacted)
    
    # Try flags, handle gracefully
    flags = []
    flag_error = None
    try:
        from app.services.flags import run_all_tier1_flags
        entries = [{"event_date": e.event_date, "clinical_description": e.clinical_description,
                    "event_type": e.event_type.value, "facility_name": e.facility_name or "Cedars-Sinai"}
                   for e in chron.entries]
        flags = run_all_tier1_flags(CASE_ID, date(2024, 3, 15), entries)
    except Exception as exc:
        flag_error = str(exc)[:100]

    exporter = ChronologyExporter()
    export_json = exporter.export_json("SYN-001", "2024-03-15", "2026-03-15", "v1", True,
        [{"event_date": e.event_date.isoformat(), "event_type": e.event_type.value,
          "description": e.clinical_description, "provider": "Cedars-Sinai"}
         for e in chron.entries])

    return {
        "status": "ok",
        "chronology_entries": chron.total_entries,
        "flags": len(flags),
        "flag_error": flag_error,
        "export_bytes": len(export_json),
    }
async def test_llm():
    import os
    from app.services.llm import create_llm_service

    service = create_llm_service()
    result = await service.complete("Reply with just the word WORKING.")
    await service.close()
    return {"status": "ok", "provider": os.environ.get("LLM_SERVICE_PROVIDER", ""), "response": result.content[:200]}
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
            text = ""
            conf = 0.0

        text_lower = text.lower()
        gt_tokens = [t.strip().rstrip(",") for t in gt.lower().split() if len(t.strip()) > 1]
        ocr_tokens = text_lower.split()
        matches = sum(1 for t in gt_tokens if any(t in o for o in ocr_tokens))
        presence = matches / len(gt_tokens) if gt_tokens else 0.0

        results.append({
            "id": f"hw_{i:03d}",
            "gt": gt[:100],
            "ocr_preview": text[:100],
            "gt_tokens": len(gt_tokens),
            "matched": matches,
            "medicine_presence": round(presence, 3),
        })

    presences = [r["medicine_presence"] for r in results]
    mean_presence = sum(presences) / len(presences) if presences else 0.0

    if mean_presence >= 0.80:
        decision, reason = "none", f"Above 80% medicine presence ({mean_presence:.1%})"
    elif mean_presence >= 0.65:
        decision, reason = "mistral_local", f"65-79% medicine presence ({mean_presence:.1%})"
    else:
        decision, reason = "mistral_local", f"Below 65% medicine presence ({mean_presence:.1%})"

    return {
        "status": "ok",
        "engine": "Mistral-OCR-4",
        "total": len(results),
        "mean_medicine_presence": round(mean_presence, 3),
        "decision": decision,
        "reason": reason,
        "samples": results[:5],
    }
