"""Append-only audit writer.

Writes one ``audit_log`` row per audited action using its own short-lived
session (so it is independent of the request's transaction). Entries carry only
opaque identifiers — never PII.
"""

from __future__ import annotations

import ipaddress
import uuid
from typing import Any

from app.core.database import async_session_maker
from app.core.logging import get_logger
from app.models.audit import AuditLog

logger = get_logger("trace.audit")


def _to_uuid(value: Any) -> uuid.UUID | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


def normalize_ip(value: Any) -> str | None:
    """Normalize a client address to canonical INET text; invalid -> NULL.

    The audit_log.ip_address column is PostgreSQL INET (DRIFT-01). Anything
    that is not a valid IPv4/IPv6 address must never reach the column — it
    becomes NULL, preserving the append-only audit write.
    """
    if value is None:
        return None
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        logger.warning("Discarding non-IP client address from audit entry")
        return None


async def write_audit(
    *,
    actor_id: Any,
    actor_type: str,
    action: str,
    resource_type: str,
    resource_id: Any = None,
    case_id: Any = None,
    firm_id: Any = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    correlation_id: str | None = None,
    details: dict | None = None,
) -> None:
    entry = AuditLog(
        actor_id=_to_uuid(actor_id),
        actor_type=actor_type,
        action=action,
        resource_type=resource_type,
        resource_id=_to_uuid(resource_id),
        case_id=_to_uuid(case_id),
        firm_id=_to_uuid(firm_id),
        ip_address=normalize_ip(ip_address),
        user_agent=(user_agent or "")[:1024] or None,
        correlation_id=correlation_id,
        details=details,
    )
    async with async_session_maker() as session:
        session.add(entry)
        await session.commit()
