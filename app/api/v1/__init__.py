"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.routes import cases, providers, requests, signing, webhooks
from app.api.v1.routes.signing import webhook_router

router = APIRouter()
router.include_router(cases.router)
router.include_router(providers.router)
router.include_router(requests.router)
router.include_router(signing.router)
router.include_router(webhooks.router)
router.include_router(webhook_router)

__all__ = ["router"]
