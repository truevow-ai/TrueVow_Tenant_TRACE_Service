"""Follow-up scheduler for fax record requests.

ADR-003 §4: configurable schedule — default day 10 follow-up,
day 20 second follow-up, day 25 portal notification,
day 30 escalation flag. Runs as a background job.

All times configurable via env vars with sensible defaults.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.logging import get_logger
from app.models.case import Case
from app.models.provider import Provider
from app.models.record_request import RecordRequest
from app.services.cover_sheet import CoverSheetGenerator
from app.services.fax import create_fax_service

logger = get_logger("trace.followup")

FOLLOWUP_DAY_1 = int(os.getenv("FAX_FOLLOWUP_DAY_1", "10"))
FOLLOWUP_DAY_2 = int(os.getenv("FAX_FOLLOWUP_DAY_2", "20"))
NOTIFY_DAY = int(os.getenv("FAX_NOTIFY_DAY", "25"))
ESCALATE_DAY = int(os.getenv("FAX_ESCALATE_DAY", "30"))


async def run_followup_scheduler() -> dict:
    """Check all cases with outstanding record requests and apply follow-up rules.

    Returns summary of actions taken. Actually sends follow-up faxes.
    """
    today = datetime.now(timezone.utc)
    actions: dict[str, int] = {"followup_1": 0, "followup_2": 0, "notified": 0, "escalated": 0}
    fax = create_fax_service()
    generator = CoverSheetGenerator()

    async with async_session_maker() as session:
        result = await session.execute(
            select(Provider).where(
                Provider.retrieval_status == "REQUESTED",
                Provider.last_request_sent.isnot(None),
            )
        )
        providers = result.scalars().all()

        for provider in providers:
            if provider.last_request_sent is None:
                continue
            days_since_sent = (today - provider.last_request_sent).days

            if days_since_sent >= ESCALATE_DAY:
                provider.retrieval_status = "UNRESPONSIVE"
                actions["escalated"] += 1
                logger.info("Provider %s escalated — %d days since request", provider.provider_id, days_since_sent)
            elif days_since_sent >= NOTIFY_DAY and provider.follow_up_count >= 2:
                actions["notified"] += 1
                logger.info("Provider %s — attorney notification triggered, day %d", provider.provider_id, days_since_sent)
            elif days_since_sent >= FOLLOWUP_DAY_2 and provider.follow_up_count < 2:
                # Resend the follow-up fax
                if provider.fax_number:
                    try:
                        cover = generator.generate(
                            case_ref=str(provider.case_id),
                            provider_name=provider.provider_name,
                            provider_fax=provider.fax_number,
                        )
                        await fax.send(provider.fax_number, cover.getvalue())
                    except Exception as exc:
                        logger.warning("Follow-up fax failed for provider %s: %s", provider.provider_id, exc)
                        continue
                provider.follow_up_count = 2
                provider.last_request_sent = today
                actions["followup_2"] += 1
            elif days_since_sent >= FOLLOWUP_DAY_1 and provider.follow_up_count < 1:
                if provider.fax_number:
                    try:
                        cover = generator.generate(
                            case_ref=str(provider.case_id),
                            provider_name=provider.provider_name,
                            provider_fax=provider.fax_number,
                        )
                        await fax.send(provider.fax_number, cover.getvalue())
                    except Exception as exc:
                        logger.warning("Follow-up fax failed for provider %s: %s", provider.provider_id, exc)
                        continue
                provider.follow_up_count = 1
                provider.last_request_sent = today
                actions["followup_1"] += 1

        await session.commit()

    return actions
