"""Signup, login, logout, Google OAuth, extension-connect."""
from __future__ import annotations

import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import (
    CSRF_COOKIE,
    SESSION_COOKIE,
    clear_session_cookie,
    current_user,
    hash_password,
    issue_csrf_token,
    issue_extension_jwt,
    issue_session,
    set_csrf_cookie,
    set_session_cookie,
    verify_csrf,
    verify_password,
)
from ..config import settings
from ..crypto import generate_dek, wrap_dek
from ..db import get_db
from ..models import User

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
OAUTH_STATE_COOKIE = "joblook_oauth_state"


def _new_user(db: Session, *, email: str, password_hash: str | None, google_sub: str | None) -> User:
    user = User(
        email=email.lower().strip(),
        password_hash=password_hash,
        google_sub=google_sub,
        dek_wrapped=wrap_dek(generate_dek()),
    )
    db.add(user)
    db.flush()
    return user


def _establish_session(response, user: User) -> None:
    set_session_cookie(response, issue_session(user.id))
    set_csrf_cookie(response, issue_csrf_token())


# ---------- signup / login ----------

@router.get("/signup", response_class=HTMLResponse)
def signup_form(request: Request):
    return templates.TemplateResponse(request, "auth/signup.html", {"csrf_token": request.cookies.get(CSRF_COOKIE, "")})


@router.post("/signup")
def signup(
    request: Request,
    email: str = Form(...),
    password: str = Form(..., min_length=8),
    db: Session = Depends(get_db),
):
    # Signup is CSRF-exempt only on the first request (no existing session). A signed-in
    # user hitting signup is unusual; still require CSRF if the cookie is set.
    if request.cookies.get(CSRF_COOKIE):
        verify_csrf(request)
    normalized = email.lower().strip()
    existing = db.execute(select(User).where(User.email == normalized)).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Account already exists")
    user = _new_user(db, email=normalized, password_hash=hash_password(password), google_sub=None)
    db.commit()
    resp = RedirectResponse("/app", status_code=status.HTTP_303_SEE_OTHER)
    _establish_session(resp, user)
    return resp


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request, "auth/login.html", {"csrf_token": request.cookies.get(CSRF_COOKIE, "")})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if request.cookies.get(CSRF_COOKIE):
        verify_csrf(request)
    user = db.execute(select(User).where(User.email == email.lower().strip())).scalar_one_or_none()
    if user is None or not user.password_hash or not verify_password(user.password_hash, password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    resp = RedirectResponse("/app", status_code=status.HTTP_303_SEE_OTHER)
    _establish_session(resp, user)
    return resp


@router.post("/logout")
def logout(request: Request):
    verify_csrf(request)
    resp = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    clear_session_cookie(resp)
    resp.delete_cookie(CSRF_COOKIE, path="/")
    return resp


# ---------- Google OAuth ----------

@router.get("/oauth/google/start")
def google_start():
    if not settings.google_oauth_client_id:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Google OAuth not configured")
    state = secrets.token_urlsafe(24)
    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    resp = RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")
    resp.set_cookie(
        OAUTH_STATE_COOKIE, state, max_age=600, httponly=True,
        secure=settings.cookie_secure, samesite="lax", path="/",
    )
    return resp


@router.get("/oauth/google/callback")
def google_callback(request: Request, code: str = "", state: str = "", db: Session = Depends(get_db)):
    expected = request.cookies.get(OAUTH_STATE_COOKIE)
    if not code or not state or not expected or state != expected:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid OAuth state")

    with httpx.Client(timeout=10.0) as client:
        tok = client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": settings.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        tok.raise_for_status()
        access_token = tok.json()["access_token"]
        info = client.get(GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
        info.raise_for_status()
        profile = info.json()

    sub = profile.get("sub")
    email = (profile.get("email") or "").lower().strip()
    if not sub or not email or not profile.get("email_verified", False):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google account email not verified")

    user = db.execute(select(User).where(User.google_sub == sub)).scalar_one_or_none()
    if user is None:
        user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            user = _new_user(db, email=email, password_hash=None, google_sub=sub)
        else:
            user.google_sub = sub
    db.commit()

    resp = RedirectResponse("/app", status_code=status.HTTP_303_SEE_OTHER)
    resp.delete_cookie(OAUTH_STATE_COOKIE, path="/")
    _establish_session(resp, user)
    return resp


# ---------- extension connect ----------

@router.get("/app/connect-extension", response_class=HTMLResponse)
def connect_extension(request: Request, user: User = Depends(current_user)):
    jwt = issue_extension_jwt(user.id)
    return templates.TemplateResponse(request, "auth/connect_extension.html", {"jwt": jwt})
