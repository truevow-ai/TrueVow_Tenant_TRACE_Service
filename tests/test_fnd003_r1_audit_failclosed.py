"""FND-003-R1 T08 — audit writer persists under real RLS (unit slice).

The guarded-lane behavioral proof (INSERT succeeds as runtime login,
SELECT/UPDATE/DELETE denied) runs in tests/test_fnd003_runtime_role.py.
This module proves the fail-closed construction contract without a DB.
"""

from __future__ import annotations

import pytest

from app.core.audit import write_audit
from app.core.database import BlockedInternalTenantContext


@pytest.mark.asyncio
async def test_audit_write_fails_closed_without_firm():
    with pytest.raises(BlockedInternalTenantContext):
        await write_audit(
            actor_id=None,
            actor_type="SYSTEM",
            action="probe.no-firm",
            resource_type="probe",
            firm_id=None,
        )
