"""FND-001A: PostgreSQL baseline reconciliation.

Reconciles the three drift roots exposed by the Postgres-only runtime:

    DRIFT-01  audit_log.ip_address — DB is already INET (0001); the ORM now
              uses INET and the writer normalizes invalid addresses to NULL.
              No schema change required for this root.
    DRIFT-02  trace.providers.extraction_confidence VARCHAR(10) -> VARCHAR(32):
              application contract uses values like HIGH_CONFIDENCE (15) and
              NEEDS_CLIENT_CONFIRMATION (25). Existing values preserved.
    DRIFT-03  trace.alembic_version.version_num -> VARCHAR(255): historical
              TRACE revision ids exceed 32 chars; aligns the existing project
              with the fresh-chain behavior of migration 0001. PUBLIC schema
              ledger (other services) is untouched.

Downgrade contracts extraction_confidence only when no truncation would occur;
otherwise it fails safely. The version-column widening is intentionally not
contracted on downgrade.

Revision ID: 0019_baseline_reconcile
Revises: 0018
Create Date: 2026-08-19
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0019_baseline_reconcile"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TRUNCATION_GUARD = """
DO $$
DECLARE c integer;
BEGIN
    SELECT count(*) INTO c FROM trace.providers
    WHERE extraction_confidence IS NOT NULL
      AND char_length(extraction_confidence) > 10;
    IF c > 0 THEN
        RAISE EXCEPTION
            'downgrade would truncate % provider extraction_confidence values', c;
    END IF;
END
$$;
"""


def upgrade() -> None:
    # DRIFT-03: TRACE ledger only — never public.alembic_version.
    op.execute(
        "ALTER TABLE trace.alembic_version ALTER COLUMN version_num TYPE VARCHAR(255);"
    )
    # DRIFT-02: widen to the application contract width.
    op.execute(
        "ALTER TABLE trace.providers "
        "ALTER COLUMN extraction_confidence TYPE VARCHAR(32);"
    )


def downgrade() -> None:
    op.execute(_TRUNCATION_GUARD)
    op.execute(
        "ALTER TABLE trace.providers "
        "ALTER COLUMN extraction_confidence TYPE VARCHAR(10);"
    )
    # trace.alembic_version.version_num widening is intentionally retained.
