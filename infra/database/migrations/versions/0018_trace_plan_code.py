"""Add trace_plan_code column to cases table.

Supports billing spec §4: TRACE is billed per canonical activated Matter,
with the selected tier locked on the Matter record at activation time.

Revision ID: 0018
Revises: 0017_phase2_schema
"""

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = '0018'
down_revision: str | None = '0017'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('cases', sa.Column(
        'trace_plan_code', sa.String(length=50), nullable=True,
    ))


def downgrade() -> None:
    op.drop_column('cases', 'trace_plan_code')
