"""ClientAccessProjection — TRACE-local projection of Shared Platform's access grant.

CRITICAL: The canonical Client Portal access grant is owned by the Shared
Platform, not TRACE. This table is a read-only projection that TRACE caches
locally for fast client access verification. The Shared Platform is the
authoritative source.

When the Shared Platform API is available, TRACE will query it directly
rather than relying on this projection. Until then, matter.activated triggers
a local projection write so client portal endpoints can verify access.

Portal access lifecycle (correct ownership model):
    RETAINER local projection:
        ENGAGEMENT_ONLY → ENGAGEMENT_HISTORY (after activation)

    Shared Platform canonical grant:
        ENGAGEMENT permissions → adds ACTIVE_MATTER after matter.activated

    TRACE: never grants MATTER_* scopes independently.
           This projection is a temporary local convenience.

Relationship scopes:
    ENGAGEMENT_ONLY        — before engagement is signed (RETAINER)
    ENGAGEMENT_HISTORY     — after matter.activated, read-only RETAINER access
    ACTIVE_MATTER          — after matter.activated, full TRACE matter access (Shared Platform)
    REPRESENTATIVE_ACCESS  — guardian/personal representative
    SETTLEMENT_PARTICIPANT — during settlement workflow
    READ_ONLY_HISTORY      — post-closure archive access
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

RELATIONSHIP_SCOPES = (
    "ENGAGEMENT_ONLY",
    "ENGAGEMENT_HISTORY",
    "ACTIVE_MATTER",
    "REPRESENTATIVE_ACCESS",
    "SETTLEMENT_PARTICIPANT",
    "READ_ONLY_HISTORY",
)

GRANT_STATUSES = ("PENDING", "ACTIVE", "REVOKED", "EXPIRED")

CLIENT_PERMISSIONS = (
    "ENGAGEMENT_VIEW", "ENGAGEMENT_QUESTION", "ENGAGEMENT_SIGN",
    "COMPLETED_COPY_DOWNLOAD",
    "MATTER_VIEW", "MATTER_MESSAGE", "MATTER_UPLOAD",
    "REQUEST_RESPOND", "DOCUMENT_DOWNLOAD",
    "SETTLEMENT_VIEW", "SETTLEMENT_DECIDE",
)


class ClientAccessProjection(Base):
    """TRACE-local projection of Shared Platform's ClientPortalAccessGrant.

    This is NOT the canonical access grant. The canonical record lives in
    the Shared Platform's client_portal_access_grants table. TRACE stores
    a projection for local verification performance. When the Shared
    Platform API is deployed, TRACE will call it directly.
    """
    __tablename__ = "trace_client_access_projections"

    projection_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    client_identity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    party_role_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    matter_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("cases.case_id"), nullable=True)
    engagement_workflow_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    canonical_grant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    relationship_scope: Mapped[str] = mapped_column(String(40), nullable=False, default="ENGAGEMENT_ONLY")
    permissions: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")

    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    source_event_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    projected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
