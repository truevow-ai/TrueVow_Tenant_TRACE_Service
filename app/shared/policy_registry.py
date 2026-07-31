"""Shared Foundation: Policy Registry.

Stores each firm's approved rules and jurisdiction configuration. Every
FIRM_POLICY action must reference an approved, effective policy version.
Policies are immutable once approved — changes create new versions.

This is the source of truth for:
- Jurisdiction profiles (which rules apply per state)
- Communication policies (SMS, email, call rules)
- Document retention policies
- Escalation rules
- Automation permissions
- Signature requirements

Designed for extraction to a shared TrueVow foundation package.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.core.database import async_session_maker
from app.core.logging import get_logger

logger = get_logger("trace.policy_registry")


@dataclass
class PolicyReference:
    """A reference to an approved policy version for audit purposes."""
    policy_id: uuid.UUID
    name: str
    version: int
    category: str
    jurisdiction: str | None = None


class PolicyRegistry:
    """Versioned tenant policy store.

    Policies are immutable once approved. Every change creates a new version
    and supersedes the previous one. At execution time, the exact policy
    version is captured for audit.
    """

    async def create_policy(
        self,
        tenant_id: uuid.UUID,
        name: str,
        category: str,
        content: dict[str, Any] | None = None,
        jurisdiction: str | None = None,
        description: str | None = None,
        approved_by: uuid.UUID | None = None,
    ) -> PolicyReference:
        """Create and approve a new policy version."""
        async with async_session_maker() as session:
            from app.models.policy import PolicyRecord

            record = PolicyRecord(
                tenant_id=tenant_id,
                category=category,
                name=name,
                description=description,
                version=1,
                jurisdiction=jurisdiction,
                effective_date=datetime.now(timezone.utc),
                is_active=True,
                approved_by=approved_by,
                approved_at=datetime.now(timezone.utc),
                policy_content=content,
            )
            session.add(record)
            await session.commit()

            return PolicyReference(
                policy_id=record.policy_id,
                name=record.name,
                version=record.version,
                category=record.category,
                jurisdiction=record.jurisdiction,
            )

    async def update_policy(
        self,
        policy_id: uuid.UUID,
        content: dict[str, Any] | None = None,
        description: str | None = None,
        approved_by: uuid.UUID | None = None,
    ) -> PolicyReference:
        """Create a new version of an existing policy, superseding the previous."""
        async with async_session_maker() as session:
            from app.models.policy import PolicyRecord

            existing = (
                await session.execute(
                    select(PolicyRecord).where(PolicyRecord.policy_id == policy_id)
                )
            ).scalar_one_or_none()

            if existing is None:
                raise ValueError(f"Policy {policy_id} not found")

            existing.is_active = False

            new_record = PolicyRecord(
                tenant_id=existing.tenant_id,
                category=existing.category,
                name=existing.name,
                description=description or existing.description,
                version=existing.version + 1,
                previous_version_id=existing.policy_id,
                jurisdiction=existing.jurisdiction,
                effective_date=datetime.now(timezone.utc),
                is_active=True,
                approved_by=approved_by,
                approved_at=datetime.now(timezone.utc),
                policy_content=content or existing.policy_content,
            )
            session.add(new_record)
            await session.commit()

            return PolicyReference(
                policy_id=new_record.policy_id,
                name=new_record.name,
                version=new_record.version,
                category=new_record.category,
                jurisdiction=new_record.jurisdiction,
            )

    async def get_active_policy(
        self,
        tenant_id: uuid.UUID,
        category: str | None = None,
    ) -> PolicyReference | None:
        """Get the latest active policy for a tenant, optionally filtered by category."""
        async with async_session_maker() as session:
            from app.models.policy import PolicyRecord

            query = select(PolicyRecord).where(
                PolicyRecord.tenant_id == tenant_id,
                PolicyRecord.is_active == True,  # noqa: E712
            ).order_by(PolicyRecord.version.desc())

            if category:
                query = query.where(PolicyRecord.category == category)

            result = (await session.execute(query.limit(1))).scalar_one_or_none()
            if result is None:
                return None
            return self._to_reference(result)

    async def get_policy_by_id(
        self,
        policy_id: uuid.UUID,
    ) -> PolicyReference | None:
        """Get a specific policy version by ID."""
        async with async_session_maker() as session:
            from app.models.policy import PolicyRecord

            result = (
                await session.execute(
                    select(PolicyRecord).where(PolicyRecord.policy_id == policy_id)
                )
            ).scalar_one_or_none()

            if result is None:
                return None
            return self._to_reference(result)

    async def list_policies(
        self,
        tenant_id: uuid.UUID,
        category: str | None = None,
    ) -> list[PolicyReference]:
        """List all active policies for a tenant."""
        async with async_session_maker() as session:
            from app.models.policy import PolicyRecord

            query = select(PolicyRecord).where(PolicyRecord.tenant_id == tenant_id)
            if category:
                query = query.where(PolicyRecord.category == category)
            query = query.order_by(PolicyRecord.name, PolicyRecord.version.desc())

            results = (await session.execute(query)).scalars().all()
            return [self._to_reference(r) for r in results]

    async def get_policy_content(
        self,
        policy_id: uuid.UUID,
    ) -> dict[str, Any] | None:
        """Get the full content of a specific policy version."""
        async with async_session_maker() as session:
            from app.models.policy import PolicyRecord

            result = (
                await session.execute(
                    select(PolicyRecord).where(PolicyRecord.policy_id == policy_id)
                )
            ).scalar_one_or_none()

            return result.policy_content if result else None

    async def get_jurisdiction_profile(
        self,
        tenant_id: uuid.UUID,
        jurisdiction: str,
    ) -> PolicyReference | None:
        """Get the active jurisdiction profile for a tenant and jurisdiction."""
        async with async_session_maker() as session:
            from app.models.policy import PolicyRecord

            result = (
                await session.execute(
                    select(PolicyRecord)
                    .where(
                        PolicyRecord.tenant_id == tenant_id,
                        PolicyRecord.category == "JURISDICTION",
                        PolicyRecord.jurisdiction == jurisdiction,
                        PolicyRecord.is_active == True,  # noqa: E712
                    )
                    .order_by(PolicyRecord.version.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

            if result is None:
                return None
            return self._to_reference(result)

    async def is_jurisdiction_supported(
        self,
        tenant_id: uuid.UUID,
        jurisdiction: str,
    ) -> bool:
        """Check if a tenant has an approved jurisdiction profile."""
        profile = await self.get_jurisdiction_profile(tenant_id, jurisdiction)
        return profile is not None

    @staticmethod
    def _to_reference(record) -> PolicyReference:
        return PolicyReference(
            policy_id=record.policy_id,
            name=record.name,
            version=record.version,
            category=record.category,
            jurisdiction=record.jurisdiction,
        )


_policy_registry: PolicyRegistry | None = None


def get_policy_registry() -> PolicyRegistry:
    global _policy_registry
    if _policy_registry is None:
        _policy_registry = PolicyRegistry()
    return _policy_registry
