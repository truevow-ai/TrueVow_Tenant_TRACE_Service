"""Shared Foundation: Consent Ledger.

Records independently verifiable evidence of consent events: communication
consent, recording consent, electronic-delivery consent, electronic-signature
consent, disclosure acknowledgment, revocations, and consent versioning.

Consent must not be represented by a single mutable Boolean field. Every
grant, refusal, revocation, expiration, and supersession is an append-only
event. The ledger is immutable — records are created, never modified or deleted.

Ontology alignment:
    ENT-024 Consent Record — versioned, attributable grant or revocation
    INV-012 Consent history preserved — append-only events
    Lifecycle: NOT_REQUESTED -> REQUESTED -> GRANTED/DECLINED -> REVOKED/EXPIRED/SUPERSEDED
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.logging import get_logger

logger = get_logger("trace.consent_ledger")


class ConsentType(str, Enum):
    COMMUNICATION = "COMMUNICATION"
    SMS = "SMS"
    RECORDING = "RECORDING"
    ELECTRONIC_DELIVERY = "ELECTRONIC_DELIVERY"
    ELECTRONIC_SIGNATURE = "ELECTRONIC_SIGNATURE"
    DISCLOSURE_ACKNOWLEDGMENT = "DISCLOSURE_ACKNOWLEDGMENT"
    DATA_SHARING = "DATA_SHARING"
    HIPAA_AUTHORIZATION = "HIPAA_AUTHORIZATION"


class ConsentState(str, Enum):
    NOT_REQUESTED = "NOT_REQUESTED"
    REQUESTED = "REQUESTED"
    GRANTED = "GRANTED"
    DECLINED = "DECLINED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"


@dataclass
class ConsentEvent:
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    person_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    matter_id: uuid.UUID | None = None
    consent_type: str = ""
    state: str = ConsentState.NOT_REQUESTED.value
    version: int = 0
    previous_version_id: uuid.UUID | None = None
    granted_by: str = ""
    granted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: str | None = None
    user_agent: str | None = None
    disclosure_version: str | None = None
    expiration_date: datetime | None = None
    metadata: dict = field(default_factory=dict)


class ConsentLedger:
    """Append-only consent event store.

    Each consent change is recorded as an immutable event. The current state
    is derived from the most recent event for each (person_id, consent_type)
    combination. Events are never modified or deleted.
    """

    async def record_consent_granted(
        self,
        person_id: uuid.UUID,
        consent_type: ConsentType,
        granted_by: str = "",
        tenant_id: uuid.UUID | None = None,
        matter_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        disclosure_version: str | None = None,
        expiration_date: datetime | None = None,
        metadata: dict | None = None,
    ) -> ConsentEvent:
        """Record a consent grant event."""
        return await self._record_event(
            person_id=person_id,
            consent_type=consent_type,
            state=ConsentState.GRANTED,
            granted_by=granted_by,
            tenant_id=tenant_id,
            matter_id=matter_id,
            ip_address=ip_address,
            user_agent=user_agent,
            disclosure_version=disclosure_version,
            expiration_date=expiration_date,
            metadata=metadata or {},
        )

    async def record_consent_declined(
        self,
        person_id: uuid.UUID,
        consent_type: ConsentType,
        tenant_id: uuid.UUID | None = None,
        matter_id: uuid.UUID | None = None,
        metadata: dict | None = None,
    ) -> ConsentEvent:
        """Record a consent decline event."""
        return await self._record_event(
            person_id=person_id,
            consent_type=consent_type,
            state=ConsentState.DECLINED,
            tenant_id=tenant_id,
            matter_id=matter_id,
            metadata=metadata or {},
        )

    async def record_consent_revoked(
        self,
        person_id: uuid.UUID,
        consent_type: ConsentType,
        revoked_by: str = "",
        tenant_id: uuid.UUID | None = None,
        matter_id: uuid.UUID | None = None,
        reason: str | None = None,
    ) -> ConsentEvent:
        """Record a consent revocation event."""
        return await self._record_event(
            person_id=person_id,
            consent_type=consent_type,
            state=ConsentState.REVOKED,
            granted_by=revoked_by,
            tenant_id=tenant_id,
            matter_id=matter_id,
            metadata={"reason": reason} if reason else {},
        )

    async def _record_event(
        self,
        person_id: uuid.UUID,
        consent_type: ConsentType,
        state: ConsentState,
        granted_by: str = "",
        tenant_id: uuid.UUID | None = None,
        matter_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        disclosure_version: str | None = None,
        expiration_date: datetime | None = None,
        metadata: dict | None = None,
    ) -> ConsentEvent:
        """Create an append-only consent event."""
        async with async_session_maker() as session:
            from app.models.consent import ConsentRecord

            previous = await self._get_current_consent(
                session, person_id, consent_type
            )

            event = ConsentEvent(
                person_id=person_id,
                tenant_id=tenant_id,
                matter_id=matter_id,
                consent_type=consent_type.value,
                state=state.value,
                version=(previous.version + 1) if previous else 1,
                previous_version_id=previous.event_id if previous else None,
                granted_by=granted_by,
                ip_address=ip_address,
                user_agent=user_agent,
                disclosure_version=disclosure_version,
                expiration_date=expiration_date,
                metadata=metadata or {},
            )

            record = ConsentRecord(
                consent_id=event.event_id,
                person_id=person_id,
                tenant_id=tenant_id,
                matter_id=matter_id,
                consent_type=event.consent_type,
                state=event.state,
                version=event.version,
                previous_version_id=event.previous_version_id,
                granted_by=event.granted_by,
                granted_at=event.granted_at,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                disclosure_version=event.disclosure_version,
                expiration_date=event.expiration_date,
                event_metadata=event.metadata,
            )
            session.add(record)
            await session.commit()

            return event

    async def get_consent_status(
        self,
        person_id: uuid.UUID,
        consent_type: ConsentType,
    ) -> ConsentEvent | None:
        """Get the current consent status for a person and type."""
        async with async_session_maker() as session:
            return await self._get_current_consent(session, person_id, consent_type)

    async def has_valid_consent(
        self,
        person_id: uuid.UUID,
        consent_type: ConsentType,
    ) -> bool:
        """Check if a person has valid GRANTED consent that hasn't expired."""
        status = await self.get_consent_status(person_id, consent_type)
        if status is None:
            return False
        if status.state != ConsentState.GRANTED.value:
            return False
        if status.expiration_date and status.expiration_date < datetime.now(timezone.utc):
            return False
        return True

    async def get_consent_history(
        self,
        person_id: uuid.UUID,
        consent_type: ConsentType | None = None,
    ) -> list[ConsentEvent]:
        """Get the full consent history for a person, optionally filtered by type."""
        async with async_session_maker() as session:
            from app.models.consent import ConsentRecord
            from sqlalchemy import select

            query = select(ConsentRecord).where(ConsentRecord.person_id == person_id)
            if consent_type:
                query = query.where(ConsentRecord.consent_type == consent_type.value)
            query = query.order_by(ConsentRecord.granted_at)

            result = await session.execute(query)
            records = result.scalars().all()

            return [
                ConsentEvent(
                    event_id=r.consent_id,
                    person_id=r.person_id,
                    tenant_id=r.tenant_id,
                    matter_id=r.matter_id,
                    consent_type=r.consent_type,
                    state=r.state,
                    version=r.version,
                    previous_version_id=r.previous_version_id,
                    granted_by=r.granted_by or "",
                    granted_at=r.granted_at,
                    ip_address=r.ip_address,
                    user_agent=r.user_agent,
                    disclosure_version=r.disclosure_version,
                    expiration_date=r.expiration_date,
                    metadata=r.event_metadata or {},
                )
                for r in records
            ]

    @staticmethod
    async def _get_current_consent(
        session: AsyncSession,
        person_id: uuid.UUID,
        consent_type: ConsentType,
    ) -> ConsentEvent | None:
        """Get the most recent consent event for a person and type."""
        from app.models.consent import ConsentRecord
        from sqlalchemy import desc

        result = await session.execute(
            select(ConsentRecord)
            .where(
                ConsentRecord.person_id == person_id,
                ConsentRecord.consent_type == consent_type.value,
            )
            .order_by(desc(ConsentRecord.version))
            .limit(1)
        )
        record = result.scalar_one_or_none()

        if record is None:
            return None

        return ConsentEvent(
            event_id=record.consent_id,
            person_id=record.person_id,
            tenant_id=record.tenant_id,
            matter_id=record.matter_id,
            consent_type=record.consent_type,
            state=record.state,
            version=record.version,
            previous_version_id=record.previous_version_id,
            granted_by=record.granted_by or "",
            granted_at=record.granted_at,
            ip_address=record.ip_address,
            user_agent=record.user_agent,
            disclosure_version=record.disclosure_version,
            expiration_date=record.expiration_date,
            metadata=record.event_metadata or {},
        )


_consent_ledger: ConsentLedger | None = None


def get_consent_ledger() -> ConsentLedger:
    global _consent_ledger
    if _consent_ledger is None:
        _consent_ledger = ConsentLedger()
    return _consent_ledger
