"""Fact Review Service — attorney review workflow with versioned audit trail.

Every modification to a fact creates an immutable FactVersion record,
producing a complete deposition-ready audit trail. Attorneys can:
- Confirm a fact (accept it as-is)
- Dispute a fact (flag it as unreliable)
- Exclude a fact (remove from chronology, keep in audit)
- Edit a fact (correct date, refine text — creates new version)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import select

from app.core.database import internal_tenant_session
from app.core.logging import get_logger
from app.models.evidence_fact import EvidenceFact
from app.models.fact_version import FactVersion

logger = get_logger("trace.fact_review")


@dataclass
class ReviewResult:
    fact_id: uuid.UUID
    previous_status: str
    new_status: str
    version_created: bool = False
    version_id: uuid.UUID | None = None
    error: str | None = None


@dataclass
class EditFactRequest:
    fact_id: uuid.UUID
    fact_text: str | None = None
    fact_date: date | None = None
    fact_type: str | None = None
    provider_id: uuid.UUID | None = None
    changed_by: uuid.UUID | None = None
    change_reason: str | None = None


class FactReviewService:
    """Attorney fact review with immutable versioning."""

    VALID_REVIEW_STATUSES = {"CONFIRMED", "DISPUTED", "EXCLUDED"}

    async def set_review_status(
        self,
        firm_id: uuid.UUID,
        fact_id: uuid.UUID,
        new_status: str,
        reviewer_id: uuid.UUID | None = None,
        review_note: str | None = None,
    ) -> ReviewResult:
        if new_status not in self.VALID_REVIEW_STATUSES:
            return ReviewResult(
                fact_id=fact_id,
                previous_status="",
                new_status=new_status,
                error=f"Invalid review status. Must be one of: {', '.join(sorted(self.VALID_REVIEW_STATUSES))}",
            )

        async with internal_tenant_session(tenant_id=firm_id) as session:
            result = await session.execute(
                select(EvidenceFact).where(EvidenceFact.fact_id == fact_id)
            )
            fact = result.scalar_one_or_none()

            if fact is None:
                return ReviewResult(
                    fact_id=fact_id,
                    previous_status="",
                    new_status=new_status,
                    error="Fact not found.",
                )

            previous_status = fact.review_status

            snapshot = FactVersion(
                fact_id=fact.fact_id,
                version_number=fact.version,
                previous_fact_text=fact.fact_text,
                previous_fact_date=fact.fact_date,
                previous_fact_type=fact.fact_type,
                previous_review_status=fact.review_status,
                previous_provider_id=fact.provider_id,
                changed_by=reviewer_id,
                change_reason=f"Review status changed: {previous_status} -> {new_status}",
            )
            session.add(snapshot)
            await session.flush()

            fact.review_status = new_status
            fact.reviewed_by = reviewer_id
            fact.reviewed_at = datetime.now(timezone.utc)
            fact.review_note = review_note
            fact.version += 1
            fact.previous_version_id = snapshot.version_id

            await session.commit()

            return ReviewResult(
                fact_id=fact.fact_id,
                previous_status=previous_status,
                new_status=new_status,
                version_created=True,
                version_id=snapshot.version_id,
            )

    async def edit_fact(
        self,
        firm_id: uuid.UUID,
        request: EditFactRequest,
    ) -> ReviewResult:
        """Edit fact fields. Creates a version snapshot before applying changes."""

        async with internal_tenant_session(tenant_id=firm_id) as session:
            result = await session.execute(
                select(EvidenceFact).where(EvidenceFact.fact_id == request.fact_id)
            )
            fact = result.scalar_one_or_none()

            if fact is None:
                return ReviewResult(
                    fact_id=request.fact_id,
                    previous_status="",
                    new_status="",
                    error="Fact not found.",
                )

            change_parts: list[str] = []
            if request.fact_text is not None and request.fact_text != fact.fact_text:
                change_parts.append("text updated")
            if request.fact_date is not None and request.fact_date != fact.fact_date:
                change_parts.append("date updated")
            if request.fact_type is not None and request.fact_type != fact.fact_type:
                change_parts.append("type updated")
            if request.provider_id is not None and request.provider_id != fact.provider_id:
                change_parts.append("provider updated")

            if not change_parts:
                return ReviewResult(
                    fact_id=fact.fact_id,
                    previous_status=fact.review_status,
                    new_status=fact.review_status,
                    error="No changes detected.",
                )

            snapshot = FactVersion(
                fact_id=fact.fact_id,
                version_number=fact.version,
                previous_fact_text=fact.fact_text,
                previous_fact_date=fact.fact_date,
                previous_fact_type=fact.fact_type,
                previous_review_status=fact.review_status,
                previous_provider_id=fact.provider_id,
                changed_by=request.changed_by,
                change_reason=request.change_reason or ", ".join(change_parts),
            )
            session.add(snapshot)
            await session.flush()

            if request.fact_text is not None:
                fact.fact_text = request.fact_text
            if request.fact_date is not None:
                fact.fact_date = request.fact_date
            if request.fact_type is not None:
                fact.fact_type = request.fact_type
            if request.provider_id is not None:
                fact.provider_id = request.provider_id

            fact.version += 1
            fact.previous_version_id = snapshot.version_id
            fact.reviewed_by = request.changed_by
            fact.reviewed_at = datetime.now(timezone.utc)

            await session.commit()

            return ReviewResult(
                fact_id=fact.fact_id,
                previous_status=fact.review_status,
                new_status=fact.review_status,
                version_created=True,
                version_id=snapshot.version_id,
            )

    async def get_fact_history(
        self,
        firm_id: uuid.UUID,
        fact_id: uuid.UUID,
    ) -> list[dict]:
        """Get the full version history of a fact."""
        async with internal_tenant_session(tenant_id=firm_id) as session:
            result = await session.execute(
                select(FactVersion)
                .where(FactVersion.fact_id == fact_id)
                .order_by(FactVersion.version_number)
            )
            versions = result.scalars().all()

            return [
                {
                    "version_id": str(v.version_id),
                    "version_number": v.version_number,
                    "previous_fact_text": v.previous_fact_text,
                    "previous_fact_date": v.previous_fact_date.isoformat() if v.previous_fact_date else None,
                    "previous_fact_type": v.previous_fact_type,
                    "previous_review_status": v.previous_review_status,
                    "previous_provider_id": str(v.previous_provider_id) if v.previous_provider_id else None,
                    "changed_by": str(v.changed_by) if v.changed_by else None,
                    "changed_at": v.changed_at.isoformat() if v.changed_at else None,
                    "change_reason": v.change_reason,
                }
                for v in versions
            ]

    async def resolve_contradiction(
        self,
        firm_id: uuid.UUID,
        contradiction_id: uuid.UUID,
        resolution_status: str,
        resolved_by: uuid.UUID | None = None,
        attorney_note: str | None = None,
    ) -> dict:
        """Resolve a contradiction pair."""
        valid = {"RESOLVED_IN_FAVOR_OF_A", "RESOLVED_IN_FAVOR_OF_B", "BOTH_VALID", "DISMISSED"}
        if resolution_status not in valid:
            raise ValueError(f"Invalid resolution status: {resolution_status}")

        async with internal_tenant_session(tenant_id=firm_id) as session:
            from app.models.contradiction import ContradictionPair

            result = await session.execute(
                select(ContradictionPair).where(
                    ContradictionPair.contradiction_id == contradiction_id
                )
            )
            pair = result.scalar_one_or_none()
            if pair is None:
                raise ValueError("Contradiction not found")

            pair.resolution_status = resolution_status
            pair.resolved_by = resolved_by
            pair.resolved_at = datetime.now(timezone.utc)
            pair.attorney_note = attorney_note

            await session.commit()

            return {
                "contradiction_id": str(pair.contradiction_id),
                "resolution_status": pair.resolution_status,
                "resolved_at": pair.resolved_at.isoformat() if pair.resolved_at else None,
            }

    async def dismiss_missing_evidence(
        self,
        firm_id: uuid.UUID,
        signal_id: uuid.UUID,
        resolved_by: uuid.UUID | None = None,
        note: str | None = None,
    ) -> dict:
        """Mark a missing-evidence signal as resolved."""
        async with internal_tenant_session(tenant_id=firm_id) as session:
            from app.models.missing_evidence import MissingEvidenceSignal

            result = await session.execute(
                select(MissingEvidenceSignal).where(
                    MissingEvidenceSignal.signal_id == signal_id
                )
            )
            signal = result.scalar_one_or_none()
            if signal is None:
                raise ValueError("Missing-evidence signal not found")

            signal.resolved = True
            signal.resolved_by = resolved_by
            signal.resolved_at = datetime.now(timezone.utc)
            signal.resolution_note = note

            await session.commit()

            return {
                "signal_id": str(signal.signal_id),
                "resolved": signal.resolved,
            }


_fact_review_service: FactReviewService | None = None


def get_fact_review_service() -> FactReviewService:
    global _fact_review_service
    if _fact_review_service is None:
        _fact_review_service = FactReviewService()
    return _fact_review_service
