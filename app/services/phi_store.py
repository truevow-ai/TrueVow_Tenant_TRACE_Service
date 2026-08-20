"""PHI store service.

Encrypts client PII and persists it to the separate PHI database, returning an
opaque ``client_token``. The operational database never sees plaintext PII.

FND-002/R1 guarantees:
  - all plaintext fields are encrypted BEFORE any session begins, so a key
    failure raises before anything is written — no partial PHI row can exist;
  - a failed commit rolls back the whole row (single-row transaction);
  - read semantics distinguish three states explicitly:
      * no row                    -> None (not found)
      * missing/malformed key     -> PhiKeyError (configuration failure)
      * wrong key / tampered /
        corrupt ciphertext        -> PhiDecryptError (PHI read failure)
    An existing-but-unreadable row is never reported as "not found" and is
    never converted to a misleading success;
  - logs contain only the opaque client_token and a sanitized error category —
    never plaintext, ciphertext, key material, fingerprints, or secret-derived
    values.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.core.crypto import PhiDecryptError, PhiKeyError, decrypt, encrypt
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

    Returns None only when no row exists. An existing row that cannot be
    decrypted raises: PhiKeyError for configuration failures, PhiDecryptError
    for authentication failures. Neither is ever converted to "not found".
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
    except PhiKeyError:
        logger.error(
            "PHI read failed for client_token=%s: key configuration error",
            client_token,
        )
        raise
    except Exception as exc:  # noqa: BLE001 — sanitized category only
        logger.error(
            "PHI read failed for client_token=%s: %s",
            client_token,
            type(exc).__name__,
        )
        raise PhiDecryptError(
            "PHI record exists but could not be authenticated/decrypted."
        ) from exc
