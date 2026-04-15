"""Column encryption helpers.

Each user has a data-encryption key (DEK) generated on signup and wrapped by a
master key held in env/KMS. Sensitive columns (profile JSON, custom answers)
are stored as `pgp_sym_encrypt(plaintext, dek)` bytea.

The master key never leaves process memory; the DEK is unwrapped per request
and discarded.
"""
from __future__ import annotations

import os
from base64 import b64decode, b64encode

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import settings


def _master_key() -> bytes:
    raw = getattr(settings, "profile_encryption_master_key", "")
    if not raw:
        raise RuntimeError("PROFILE_ENCRYPTION_MASTER_KEY is not set")
    key = b64decode(raw)
    if len(key) != 32:
        raise RuntimeError("PROFILE_ENCRYPTION_MASTER_KEY must be 32 bytes base64-encoded")
    return key


def generate_dek() -> bytes:
    """Return a fresh 32-byte DEK for a new user."""
    return os.urandom(32)


def wrap_dek(dek: bytes) -> bytes:
    """AES-GCM wrap a DEK with the master key. Returns nonce || ciphertext."""
    nonce = os.urandom(12)
    ct = AESGCM(_master_key()).encrypt(nonce, dek, associated_data=None)
    return nonce + ct


def unwrap_dek(wrapped: bytes) -> bytes:
    nonce, ct = wrapped[:12], wrapped[12:]
    return AESGCM(_master_key()).decrypt(nonce, ct, associated_data=None)


def encrypt_column(db: Session, plaintext: str, dek: bytes) -> bytes:
    """pgp_sym_encrypt via Postgres. Returns bytea."""
    row = db.execute(
        text("SELECT pgp_sym_encrypt(:pt, :key) AS ct"),
        {"pt": plaintext, "key": b64encode(dek).decode()},
    ).one()
    return bytes(row.ct)


def decrypt_column(db: Session, ciphertext: bytes, dek: bytes) -> str:
    row = db.execute(
        text("SELECT pgp_sym_decrypt(:ct, :key) AS pt"),
        {"ct": ciphertext, "key": b64encode(dek).decode()},
    ).one()
    return row.pt
