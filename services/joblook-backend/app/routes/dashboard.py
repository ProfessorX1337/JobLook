"""Dashboard pages: home, profile editor, resume upload + review."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ..auth import CSRF_COOKIE, current_user, verify_csrf
from ..db import get_db
from ..models import LlmCostLog, User
from ..profile_store import load_profile, save_profile
from ..resume_parser import extract_text, parse_resume, record_cost
from ..schemas import (
    CustomAnswer,
    Demographics,
    Education,
    Experience,
    Identity,
    Preferences,
    Profile,
    Skill,
    WorkAuthorization,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

MAX_RESUME_BYTES = 5 * 1024 * 1024  # 5 MB


def _ctx(request: Request, user: User, **extra) -> dict:
    return {
        "user": user,
        "csrf_token": request.cookies.get(CSRF_COOKIE, ""),
        **extra,
    }


def _build_profile_from_form(
    identity_json: str,
    work_auth_json: str,
    experience_json: str,
    education_json: str,
    skills_raw: str,
    preferences_json: str,
    summary: str,
) -> Profile:
    """Reconstruct a Profile from the structured form field JSON blobs."""
    identity = Identity.model_validate_json(identity_json)
    work_auth = WorkAuthorization.model_validate_json(work_auth_json)
    experience = [Experience.model_validate_json(e) for e in json.loads(experience_json)]
    education = [Education.model_validate_json(e) for e in json.loads(education_json)]
    skill_names = [s.strip() for s in skills_raw.split(",") if s.strip()]
    skills = [Skill(name=n) for n in skill_names]
    prefs = Preferences.model_validate_json(preferences_json)
    demographics = Demographics()
    return Profile(
        identity=identity,
        work_authorization=work_auth,
        experience=experience,
        education=education,
        skills=skills,
        preferences=prefs,
        demographics=demographics,
        summary=summary,
        custom_answers=[],
    )


@router.get("/app", response_class=HTMLResponse)
def home(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = load_profile(db, user)

    # Load usage stats
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)

    autofill_today = (
        db.query(LlmCostLog)
        .filter(LlmCostLog.user_id == user.id, LlmCostLog.created_at >= today_start)
        .count()
    )
    llm_calls_month = (
        db.query(LlmCostLog)
        .filter(LlmCostLog.user_id == user.id, LlmCostLog.created_at >= month_start)
        .count()
    )
    total_cost_month = (
        db.query(LlmCostLog)
        .filter(LlmCostLog.user_id == user.id, LlmCostLog.created_at >= month_start)
        .with_entities(LlmCostLog.cost_cents)
        .all()
    )
    total_cost_month_cents = sum(r[0] for r in total_cost_month) if total_cost_month else 0

    subscription = getattr(user, "subscription", None)
    tier = user.tier or "free"

    return templates.TemplateResponse(
        request,
        "dashboard/home.html",
        _ctx(
            request,
            user,
            profile=profile,
            tier=tier,
            subscription=subscription,
            autofill_today=autofill_today,
            llm_calls_month=llm_calls_month,
            total_cost_month_cents=total_cost_month_cents,
        ),
    )


@router.get("/app/profile", response_class=HTMLResponse)
def profile_editor(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = load_profile(db, user)
    return templates.TemplateResponse(
        request, "dashboard/profile.html",
        _ctx(request, user, profile=profile),
    )


@router.post("/app/profile")
def profile_save(
    request: Request,
    profile_json: str = Form(...),
    identity_json: str = Form("{}"),
    work_auth_json: str = Form("{}"),
    experience_json: str = Form("[]"),
    education_json: str = Form("[]"),
    skills_raw: str = Form(""),
    preferences_json: str = Form("{}"),
    summary: str = Form(""),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    verify_csrf(request)
    try:
        if profile_json and profile_json != "{}":
            # Fallback to full JSON if provided (resume review flow)
            try:
                profile = Profile.model_validate_json(profile_json)
            except ValidationError:
                # Build from structured fields
                profile = _build_profile_from_form(
                    identity_json, work_auth_json, experience_json,
                    education_json, skills_raw, preferences_json, summary,
                )
        else:
            profile = _build_profile_from_form(
                identity_json, work_auth_json, experience_json,
                education_json, skills_raw, preferences_json, summary,
            )
    except ValidationError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid profile data: {e}") from e
    save_profile(db, user, profile)
    db.commit()
    return RedirectResponse("/app/profile?saved=1", status_code=status.HTTP_303_SEE_OTHER)


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


# ---------- account: data export + delete ----------

@router.get("/app/account", response_class=HTMLResponse)
def account_page(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    llm_calls_month = (
        db.query(LlmCostLog)
        .filter(LlmCostLog.user_id == user.id, LlmCostLog.created_at >= month_start)
        .count()
    )
    total_cost_month = (
        db.query(LlmCostLog)
        .filter(LlmCostLog.user_id == user.id, LlmCostLog.created_at >= month_start)
        .with_entities(LlmCostLog.cost_cents)
        .all()
    )
    total_cost_month_cents = sum(r[0] for r in total_cost_month) if total_cost_month else 0
    return templates.TemplateResponse(
        request, "dashboard/account.html",
        _ctx(request, user, llm_calls_month=llm_calls_month, total_cost_month_cents=total_cost_month_cents),
    )


@router.get("/app/account/export")
def export_data(request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = load_profile(db, user)
    export = {
        "user_id": str(user.id),
        "email": user.email,
        "tier": user.tier,
        "profile": profile.model_dump(),
    }
    from fastapi.responses import Response
    import json as _json
    return Response(
        content=_json.dumps(export, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=joblook-export-{user.id}.json"},
    )


@router.post("/app/account/delete")
def delete_account(
    request: Request,
    confirm_email: str = Form(...),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    verify_csrf(request)
    if confirm_email != user.email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email confirmation does not match.")
    db.delete(user)
    db.commit()
    from fastapi.security import OAuth2PasswordBearer
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("session", path="/")
    return response
