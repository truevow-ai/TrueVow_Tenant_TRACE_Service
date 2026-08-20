"""PHI store service.

Encrypts client PII and persists it to the separate PHI database, returning an
opaque ``client_token``. The operational database never sees plaintext PII.

FND-002 guarantees:
  - all plaintext fields are encrypted BEFORE any session begins, so a key
    failure raises before anything is written — no partial PHI row can exist;
  - a failed commit rolls back the whole row (single-row transaction);
  - decryption/authentication failure is controlled: it returns ``None``
    (unreadable) and logs a sanitized error — never plaintext, ciphertext, or
    a misleading success;
  - plaintext never reaches logs or the operational database.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.crypto import decrypt, encrypt
from app.core.database import phi_session_maker
from app.core.logging import get_logger
from app.models.client import Client

logger = get_logger("trace.phi_store")


async def store_client(
    *, name: str, dob: str, address: str, phone: str, firm_id: uuid.UUID
) -> uuid.UUID:
    """Encrypt and persist client PII. Returns the opaque client_token.

    Encryption happens fully before the database session opens: if the PHI
    key is missing/malformed the call fails closed and no row is created.
    """
    encrypted_name = encrypt(name)
    encrypted_dob = encrypt(dob)
    encrypted_address = encrypt(address)
    encrypted_phone = encrypt(phone)

    client = Client(
        encrypted_name=encrypted_name,
        encrypted_dob=encrypted_dob,
        encrypted_address=encrypted_address,
        encrypted_phone=encrypted_phone,
        firm_id=firm_id,
    )
    async with phi_session_maker() as session:
        session.add(client)
        await session.commit()
        return client.client_token


async def get_client(client_token: uuid.UUID) -> dict | None:
    """Decrypt and return client PII for an attorney-authenticated read.

    A decryption/authentication failure (wrong key, tampered ciphertext)
    returns None — the record exists but is unreadable — and is logged
    without any secret or plaintext material.
    """
    async with phi_session_maker() as session:
        result = await session.execute(
            select(Client).where(Client.client_token == client_token)
        )
        client = result.scalar_one_or_none()
        if client is None:
            return None

    try:
        return {
            "client_token": str(client.client_token),
            "name": decrypt(client.encrypted_name) if client.encrypted_name else "",
            "dob": decrypt(client.encrypted_dob) if client.encrypted_dob else "",
            "address": decrypt(client.encrypted_address) if client.encrypted_address else "",
            "phone": decrypt(client.encrypted_phone) if client.encrypted_phone else "",
            "firm_id": str(client.firm_id),
        }
    except Exception as exc:  # noqa: BLE001 — sanitized failure, never success
        logger.error(
            "PHI decryption failed for client_token=%s: %s",
            client_token,
            type(exc).__name__,
        )
        return None
