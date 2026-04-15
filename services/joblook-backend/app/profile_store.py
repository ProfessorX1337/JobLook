"""Encrypted profile read/write helpers."""
from __future__ import annotations

from sqlalchemy.orm import Session

from .crypto import decrypt_column, encrypt_column, unwrap_dek
from .models import Profile as ProfileRow, User
from .schemas import Profile


def load_profile(db: Session, user: User) -> Profile:
    row = db.get(ProfileRow, user.id)
    if row is None:
        return Profile()
    dek = unwrap_dek(user.dek_wrapped)
    plaintext = decrypt_column(db, row.data_encrypted, dek)
    return Profile.model_validate_json(plaintext)


def save_profile(db: Session, user: User, profile: Profile) -> None:
    dek = unwrap_dek(user.dek_wrapped)
    ct = encrypt_column(db, profile.model_dump_json(), dek)
    row = db.get(ProfileRow, user.id)
    if row is None:
        db.add(ProfileRow(user_id=user.id, data_encrypted=ct))
    else:
        row.data_encrypted = ct
