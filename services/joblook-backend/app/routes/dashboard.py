"""Dashboard pages: home, profile editor, resume upload + review."""
from __future__ import annotations

import base64
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ..auth import CSRF_COOKIE, current_user, verify_csrf
from ..db import get_db
from ..models import User
from ..profile_store import load_profile, save_profile
from ..resume_parser import extract_text, parse_resume, record_cost
from ..schemas import Profile

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

MAX_RESUME_BYTES = 5 * 1024 * 1024  # 5 MB


def _ctx(request: Request, user: User, **extra) -> dict:
    return {
        "user": user,
        "csrf_token": request.cookies.get(CSRF_COOKIE, ""),
        **extra,
    }


@router.get("/app", response_class=HTMLResponse)
def home(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = load_profile(db, user)
    return templates.TemplateResponse(request, "dashboard/home.html", _ctx(request, user, profile=profile))


@router.get("/app/profile", response_class=HTMLResponse)
def profile_editor(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = load_profile(db, user)
    return templates.TemplateResponse(
        request, "dashboard/profile.html",
        _ctx(request, user, profile=profile, profile_json=profile.model_dump_json(indent=2)),
    )


@router.post("/app/profile")
def profile_save(
    request: Request,
    profile_json: str = Form(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    verify_csrf(request)
    try:
        profile = Profile.model_validate_json(profile_json)
    except ValidationError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid profile JSON: {e}") from e
    save_profile(db, user, profile)
    db.commit()
    return RedirectResponse("/app/profile", status_code=status.HTTP_303_SEE_OTHER)


# ---------- resume upload → review → confirm ----------

@router.get("/app/resume", response_class=HTMLResponse)
def resume_upload_form(request: Request, user: User = Depends(current_user)):
    return templates.TemplateResponse(request, "dashboard/resume_upload.html", _ctx(request, user))


@router.post("/app/resume", response_class=HTMLResponse)
async def resume_upload(
    request: Request,
    resume: UploadFile = File(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    verify_csrf(request)
    data = await resume.read()
    if len(data) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Empty file")
    if len(data) > MAX_RESUME_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Resume exceeds 5 MB limit")

    try:
        text = extract_text(resume.filename or "", data)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e

    result = parse_resume(text)
    record_cost(db, user, result)
    db.commit()

    return templates.TemplateResponse(
        request, "dashboard/resume_review.html",
        _ctx(
            request, user,
            profile=result.profile,
            profile_json=result.profile.model_dump_json(indent=2),
            cost_cents=result.cost_cents,
        ),
    )


@router.post("/app/resume/confirm")
def resume_confirm(
    request: Request,
    profile_json: str = Form(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    verify_csrf(request)
    try:
        profile = Profile.model_validate_json(profile_json)
    except ValidationError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid profile JSON: {e}") from e
    save_profile(db, user, profile)
    db.commit()
    return RedirectResponse("/app/profile", status_code=status.HTTP_303_SEE_OTHER)
