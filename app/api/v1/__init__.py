"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.routes import cases, providers, requests, webhooks

router = APIRouter()
router.include_router(cases.router)
router.include_router(providers.router)
router.include_router(requests.router)
router.include_router(webhooks.router)

__all__ = ["router"]
