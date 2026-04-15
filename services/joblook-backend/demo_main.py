"""Simplified FastAPI app for demo purposes without database dependencies."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="JobLook Demo")

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return templates.TemplateResponse(
        request, "marketing.html",
        {"csrf_token": "demo_token"},
    )

@app.get("/product", response_class=HTMLResponse)
def product_page(request: Request):
    return templates.TemplateResponse(
        request, "product.html",
        {"csrf_token": "demo_token"},
    )

@app.get("/pricing", response_class=HTMLResponse)
def pricing_page(request: Request):
    return templates.TemplateResponse(
        request, "pricing.html",
        {"csrf_token": "demo_token"},
    )

@app.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    return templates.TemplateResponse(
        request, "about.html",
        {"csrf_token": "demo_token"},
    )

@app.get("/contact", response_class=HTMLResponse)
def contact_page(request: Request):
    return templates.TemplateResponse(
        request, "contact.html",
        {"csrf_token": "demo_token"},
    )

@app.post("/contact", response_class=HTMLResponse)
def contact_form_submit(request: Request):
    # Simple redirect for demo
    return RedirectResponse("/contact?success=1", status_code=303)

@app.get("/blog", response_class=HTMLResponse)
def blog_page(request: Request):
    # Simple blog page with empty posts for demo
    return templates.TemplateResponse(
        request, "blog.html",
        {"posts": [], "current_page": 1, "total_pages": 1, "prev_page": None, "next_page": None, "csrf_token": "demo_token"},
    )

@app.get("/healthz")
def healthz():
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)