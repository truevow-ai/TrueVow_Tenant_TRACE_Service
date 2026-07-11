"""PHI encryption round-trip test against real Supabase PostgreSQL.

Not run as part of the SQLite test suite. Run manually:
  python tests/run_phi_roundtrip_pg.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(".env.local", override=True)

from sqlalchemy import text


async def test_phi_encryption_round_trip_postgres():
    from app.core.crypto import encrypt, decrypt
    from app.core.database import phi_session_maker
    from app.models.client import Client
    from app.services.phi_store import get_client, store_client

    original = "Maria Rodriguez"
    dob = "1985-04-12"
    firm_id = uuid.uuid4()

    token = await store_client(
        name=original,
        dob=dob,
        address="789 Ocean Ave, Santa Monica, CA 90401",
        phone="+13105559876",
        firm_id=firm_id,
    )

    retrieved = await get_client(token)
    assert retrieved is not None, "PHI retrieval returned None"
    assert retrieved["name"] == original
    assert retrieved["dob"] == dob

    async with phi_session_maker() as session:
        row = (
            await session.execute(
                text(
                    "SELECT encrypted_name FROM trace_phi.clients "
                    "WHERE client_token = :token"
                ),
                {"token": str(token)},
            )
        ).fetchone()

        assert row is not None, "Row not found in trace_phi.clients"

        stored = row[0] or ""
        assert original not in stored, (
            f"PHI stored as plaintext in database: {stored[:80]}..."
        )
        assert len(stored) > 50, (
            f"Encrypted value too short ({len(stored)} chars)"
        )

        print(f"  Encrypted column length: {len(stored)} chars")
        print(f"  First 40 chars of ciphertext: {stored[:40]}...")

    cipher = encrypt(original)
    round_tripped = decrypt(cipher)
    assert round_tripped == original

    print(f"\n  Round-trip: {original!r} -> {cipher[:30]}... -> {round_tripped!r}")
    print(f"  PHI encryption round-trip verified against real Supabase")

    async with phi_session_maker() as session:
        await session.execute(
            text("DELETE FROM trace_phi.clients WHERE client_token = :token"),
            {"token": str(token)},
        )
        await session.commit()

    print(f"  Test row cleaned up")
    return token


async def test_not_plaintext():
    from app.core.crypto import encrypt

    plaintext = "Jane Q. Public"
    cipher = encrypt(plaintext)

    assert plaintext not in cipher
    assert len(cipher) > 50
    assert isinstance(cipher, str)

    for ch in cipher.rstrip("="):
        assert ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="

    print(f"\n  Encrypt returns valid base64 str, no plaintext leaked")
    return True


if __name__ == "__main__":
    asyncio.run(test_not_plaintext())
    token = asyncio.run(test_phi_encryption_round_trip_postgres())
    print(f"\n  All checks passed. Client token: {token}")
