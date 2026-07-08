"""PHI store service.

Encrypts client PII and persists it to the separate PHI database, returning an
opaque ``client_token``. The operational database never sees plaintext PII.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.crypto import decrypt, encrypt
from app.core.database import phi_session_maker
from app.models.client import Client


async def store_client(
    *, name: str, dob: str, address: str, phone: str, firm_id: uuid.UUID
) -> uuid.UUID:
    """Encrypt and persist client PII. Returns the opaque client_token."""
    client = Client(
        encrypted_name=encrypt(name),
        encrypted_dob=encrypt(dob),
        encrypted_address=encrypt(address),
        encrypted_phone=encrypt(phone),
        firm_id=firm_id,
    )
    async with phi_session_maker() as session:
        session.add(client)
        await session.commit()
        return client.client_token


async def get_client(client_token: uuid.UUID) -> dict | None:
    """Decrypt and return client PII for an attorney-authenticated read."""
    async with phi_session_maker() as session:
        result = await session.execute(
            select(Client).where(Client.client_token == client_token)
        )
        client = result.scalar_one_or_none()
        if client is None:
            return None
        return {
            "client_token": str(client.client_token),
            "name": decrypt(client.encrypted_name),
            "dob": decrypt(client.encrypted_dob),
            "address": decrypt(client.encrypted_address),
            "phone": decrypt(client.encrypted_phone),
            "firm_id": str(client.firm_id),
        }
