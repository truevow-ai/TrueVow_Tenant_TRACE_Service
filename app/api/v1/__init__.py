"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.routes import cases, client_links, documents, jobs, liens, providers, qa, requests, signing, webhooks
from app.api.v1.routes.client_links import public_router
from app.api.v1.routes.signing import webhook_router

router = APIRouter()
router.include_router(cases.router)
router.include_router(client_links.router)
router.include_router(documents.router)
router.include_router(jobs.router)
router.include_router(liens.router)
router.include_router(providers.router)
router.include_router(qa.router)
router.include_router(requests.router)
router.include_router(signing.router)
router.include_router(webhooks.router)
router.include_router(webhook_router)
router.include_router(public_router)

__all__ = ["router"]
