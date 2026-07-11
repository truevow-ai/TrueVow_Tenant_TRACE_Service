"""Background job triggers — follow-up scheduler, dedup, reminders.

Exposed as admin endpoints for cron/external scheduler invocation.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.auth.deps import AuthContext, get_current_context
from app.core.logging import get_logger
from app.services.followup import run_followup_scheduler

logger = get_logger("trace.jobs")

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/followup-scheduler")
async def trigger_followup_scheduler(
    request: Request,
    ctx: AuthContext = Depends(get_current_context),
) -> dict:
    """Run the fax follow-up scheduler. Triggered by cron or external scheduler."""
    actions = await run_followup_scheduler()
    logger.info("Follow-up scheduler completed: %s", actions)
    return {"status": "completed", "actions": actions}
