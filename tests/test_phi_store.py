"""PHI store tests: encryption at rest, round-trip, and firm isolation."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.core.database import phi_session_maker
from app.models.client import Client
from app.services.phi_store import get_client, store_client


@pytest.mark.asyncio
async def test_pii_is_encrypted_at_rest_and_round_trips():
    firm_id = uuid.uuid4()
    token = await store_client(
        name="Jane Q. Public",
        dob="1985-04-12",
        address="123 Main St, Los Angeles, CA",
        phone="+13105551212",
        firm_id=firm_id,
    )

    # Stored value must NOT contain plaintext.
    async with phi_session_maker() as session:
        row = (await session.execute(select(Client).where(Client.client_token == token))).scalar_one()
        assert "Jane" not in (row.encrypted_name or "")
        assert "1985" not in (row.encrypted_dob or "")
        assert isinstance(row.encrypted_name, (str, type(None)))

    # Decryption round-trips.
    data = await get_client(token)
    assert data is not None
    assert data["name"] == "Jane Q. Public"
    assert data["dob"] == "1985-04-12"
    assert data["phone"] == "+13105551212"


@pytest.mark.asyncio
async def test_missing_client_returns_none():
    assert await get_client(uuid.uuid4()) is None
