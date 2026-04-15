"""Auth primitives: password hashing, session cookie, extension JWT, current-user dependency."""
from __future__ import annotations

import hmac
import json
import secrets
import uuid
from base64 import urlsafe_b64decode, urlsafe_b64encode
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

SESSION_COOKIE = "joblook_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 days
CSRF_COOKIE = "joblook_csrf"
CSRF_HEADER = "X-CSRF-Token"

_hasher = PasswordHasher()
_serializer = URLSafeTimedSerializer(settings.session_secret, salt="joblook.session")


# ---------- passwords ----------

def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


# ---------- session cookie ----------

def issue_session(user_id: uuid.UUID) -> str:
    return _serializer.dumps({"uid": str(user_id)})


def read_session(token: str) -> uuid.UUID | None:
    try:
        payload = _serializer.loads(token, max_age=SESSION_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None
    try:
        return uuid.UUID(payload["uid"])
    except (KeyError, ValueError, TypeError):
        return None


def set_session_cookie(response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


# ---------- CSRF double-submit ----------

def issue_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response, token: str) -> None:
    response.set_cookie(
        key=CSRF_COOKIE,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=False,  # readable by dashboard JS to echo into header
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def verify_csrf(request: Request) -> None:
    cookie = request.cookies.get(CSRF_COOKIE)
    header = request.headers.get(CSRF_HEADER)
    form_token: str | None = None
    # Also accept hidden form field for non-JS flows; read lazily to avoid consuming body.
    # Callers that use forms should pass the token back via hidden input named "csrf_token".
    if not header:
        form_token = request.headers.get("x-csrf-token-form")
    submitted = header or form_token
    if not cookie or not submitted or not hmac.compare_digest(cookie, submitted):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "CSRF validation failed")


# ---------- extension JWT (HS256, hand-rolled to avoid extra dep) ----------

def _b64url(raw: bytes) -> str:
    return urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return urlsafe_b64decode(s + pad)


def issue_extension_jwt(user_id: uuid.UUID) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "scope": "extension",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=settings.extension_jwt_ttl_days)).timestamp()),
    }
    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}".encode()
    sig = hmac.new(settings.extension_jwt_secret.encode(), signing_input, sha256).digest()
    return f"{h}.{p}.{_b64url(sig)}"


def verify_extension_jwt(token: str) -> uuid.UUID | None:
    try:
        h, p, s = token.split(".")
    except ValueError:
        return None
    signing_input = f"{h}.{p}".encode()
    expected = hmac.new(settings.extension_jwt_secret.encode(), signing_input, sha256).digest()
    if not hmac.compare_digest(expected, _b64url_decode(s)):
        return None
    try:
        payload = json.loads(_b64url_decode(p))
    except (ValueError, json.JSONDecodeError):
        return None
    if payload.get("scope") != "extension":
        return None
    if int(payload.get("exp", 0)) < datetime.now(tz=timezone.utc).timestamp():
        return None
    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        return None


# ---------- FastAPI dependencies ----------

def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Dashboard dependency — requires a valid session cookie."""
    token = request.cookies.get(SESSION_COOKIE)
    uid = read_session(token) if token else None
    if uid is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    user = db.execute(select(User).where(User.id == uid)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not signed in")
    return user


def optional_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get(SESSION_COOKIE)
    uid = read_session(token) if token else None
    if uid is None:
        return None
    return db.execute(select(User).where(User.id == uid)).scalar_one_or_none()


def current_extension_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Extension dependency — requires bearer JWT."""
    authz = request.headers.get("Authorization", "")
    if not authz.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    uid = verify_extension_jwt(authz.split(" ", 1)[1].strip())
    if uid is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    user = db.execute(select(User).where(User.id == uid)).scalar_one_or_none()
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return user
