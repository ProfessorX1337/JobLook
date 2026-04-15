"""Extension-facing API (JWT-auth, JSON)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..auth import current_extension_user
from ..db import get_db
from ..models import User
from ..profile_store import load_profile

router = APIRouter(prefix="/api/extension")


@router.get("/profile")
def get_profile(user: User = Depends(current_extension_user), db: Session = Depends(get_db)):
    profile = load_profile(db, user)
    # Scrub fields the extension shouldn't need for local standard-field fill.
    scrubbed = profile.model_dump(mode="json")
    scrubbed.pop("custom_answers", None)
    return JSONResponse(scrubbed)
