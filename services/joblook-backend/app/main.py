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
from .routes import blog as blog_routes
from .routes import dashboard as dashboard_routes
from .routes import extension as extension_routes
from .routes import admin as admin_routes

from .middleware.admin import AdminIPMiddleware

app = FastAPI(title="JobLook")
app.add_middleware(AdminIPMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"chrome-extension://.*",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(admin_routes.router)
app.include_router(auth_routes.router)
app.include_router(blog_routes.router)
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


@app.get("/product", response_class=HTMLResponse)
def product_page(request: Request):
    return templates.TemplateResponse(
        request, "product.html",
        {"csrf_token": request.cookies.get(CSRF_COOKIE, "")},
    )


@app.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request):
    return templates.TemplateResponse(
        request, "pricing.html",
        {"csrf_token": request.cookies.get(CSRF_COOKIE, "")},
    )


@app.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    return templates.TemplateResponse(
        request, "about.html",
        {"csrf_token": request.cookies.get(CSRF_COOKIE, "")},
    )


@app.get("/contact", response_class=HTMLResponse)
def contact_page(request: Request):
    return templates.TemplateResponse(
        request, "contact.html",
        {"csrf_token": request.cookies.get(CSRF_COOKIE, "")},
    )


@app.post("/contact", response_class=HTMLResponse)
def contact_form_submit(request: Request):
    # This would handle the contact form submission
    # For now, just redirect back to contact page with a success message
    return RedirectResponse("/contact?success=1", status_code=303)


@app.get("/healthz")
def healthz():
    return {"ok": True}
