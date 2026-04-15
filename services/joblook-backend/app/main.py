"""FastAPI app entrypoint."""
from __future__ import annotations

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .auth import CSRF_COOKIE, issue_csrf_token, optional_current_user, set_csrf_cookie
from .models import User
from .routes import auth as auth_routes
from .routes import dashboard as dashboard_routes
from .routes import extension as extension_routes

app = FastAPI(title="JobLook")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"chrome-extension://.*",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(auth_routes.router)
app.include_router(dashboard_routes.router)
app.include_router(extension_routes.router)


@app.middleware("http")
async def ensure_csrf_cookie(request: Request, call_next):
    """Issue a CSRF cookie on first contact so forms can echo it back."""
    response = await call_next(request)
    if not request.cookies.get(CSRF_COOKIE):
        set_csrf_cookie(response, issue_csrf_token())
    return response


@app.get("/", response_class=HTMLResponse)
def landing(request: Request, user: User | None = Depends(optional_current_user)):
    if user is not None:
        return RedirectResponse("/app", status_code=303)
    return templates.TemplateResponse(
        request, "marketing.html",
        {"user": None, "csrf_token": request.cookies.get(CSRF_COOKIE, "")},
    )


@app.get("/healthz")
def healthz():
    return {"ok": True}
