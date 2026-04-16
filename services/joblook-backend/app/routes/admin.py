"""Super admin API routes at /admin."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..auth import CSRF_COOKIE, current_user, verify_csrf
from ..db import get_db
from ..models import LlmCostLog, Subscription, User
from ..profile_store import load_profile

router = APIRouter()


def _ctx(request: Request, **extra) -> dict:
    return {
        "user": None,
        "csrf_token": request.cookies.get(CSRF_COOKIE, ""),
        **extra,
    }


def _admin_home_ctx(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    total_users = db.execute(select(func.count(User.id))).scalar_one() or 0
    signups_today = (
        db.execute(select(func.count(User.id)).where(User.created_at >= today_start)).scalar_one() or 0
    )
    signups_week = (
        db.execute(select(func.count(User.id)).where(User.created_at >= week_start)).scalar_one() or 0
    )
    signups_month = (
        db.execute(select(func.count(User.id)).where(User.created_at >= month_start)).scalar_one() or 0
    )
    pro_users = (
        db.execute(select(func.count(User.id)).where(User.tier == "pro")).scalar_one() or 0
    )
    llm_spend = (
        db.execute(
            select(func.sum(LlmCostLog.cost_cents))
            .where(LlmCostLog.created_at >= month_start)
        ).scalar_one() or 0
    )
    revenue = pro_users * 1900  # cents

    return {
        "total_users": total_users,
        "signups_today": signups_today,
        "signups_week": signups_week,
        "signups_month": signups_month,
        "pro_users": pro_users,
        "llm_spend_cents": llm_spend,
        "revenue_cents": revenue,
    }


@router.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request, db: Session = Depends(get_db)):
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="app/templates")
    ctx = _ctx(request, **_admin_home_ctx(db))
    return templates.TemplateResponse("admin/dashboard.html", ctx)


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users(
    request: Request,
    db: Session = Depends(get_db),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
):
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="app/templates")

    per_page = 50
    offset = (page - 1) * per_page

    base_q = select(User).order_by(User.created_at.desc())
    if q:
        base_q = base_q.where(User.email.ilike(f"%{q}%"))

    total = db.execute(select(func.count()).select_from(base_q.subquery())).scalar_one() or 0
    users = db.execute(base_q.offset(offset).limit(per_page)).scalars().all()

    return templates.TemplateResponse(
        "admin/users.html",
        _ctx(request, users=users, q=q or "", page=page, total=total, per_page=per_page),
    )


@router.get("/admin/users/{user_id}", response_class=HTMLResponse)
def admin_user_detail(request: Request, user_id: str, db: Session = Depends(get_db)):
    from uuid import UUID
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="app/templates")

    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid user ID")

    user = db.execute(select(User).where(User.id == uid)).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    profile = load_profile(db, user)
    sub = db.execute(select(Subscription).where(Subscription.user_id == uid)).scalar_one_or_none()

    cost_rows = (
        db.execute(
            select(LlmCostLog)
            .where(LlmCostLog.user_id == uid)
            .order_by(LlmCostLog.created_at.desc())
            .limit(100)
        ).scalars().all()
    )
    total_cost = sum(r.cost_cents for r in cost_rows)

    return templates.TemplateResponse(
        "admin/user_detail.html",
        _ctx(request, user=user, profile=profile, subscription=sub,
             cost_rows=cost_rows, total_cost_cents=total_cost),
    )


@router.post("/admin/tier-override")
def admin_tier_override(
    request: Request,
    user_id: str = Form(...),
    new_tier: str = Form(...),
    reason: str = Form(""),
    db: Session = Depends(get_db),
):
    from uuid import UUID

    verify_csrf(request)
    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid user ID")
    if new_tier not in ("free", "pro"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tier must be 'free' or 'pro'")
    if not reason.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A reason is required for audit purposes")

    user = db.execute(select(User).where(User.id == uid)).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")

    old_tier = user.tier
    user.tier = new_tier
    db.commit()
    return {"ok": True, "old_tier": old_tier, "new_tier": new_tier, "reason": reason}


@router.post("/admin/users/{user_id}/disable")
def admin_disable_user(request: Request, user_id: str, db: Session = Depends(get_db)):
    from uuid import UUID

    verify_csrf(request)
    try:
        uid = UUID(user_id)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid user ID")
    user = db.execute(select(User).where(User.id == uid)).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    db.delete(user)
    db.commit()
    return RedirectResponse("/admin/users", status_code=303)
