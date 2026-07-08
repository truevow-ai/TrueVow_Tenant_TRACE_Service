"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.routes import cases

router = APIRouter()
router.include_router(cases.router)

__all__ = ["router"]
