"""IP allowlist middleware for /admin routes."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class AdminIPMiddleware(BaseHTTPMiddleware):
    """Reject any /admin request from a client IP not in ALLOWED_ADMIN_IPS."""

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/admin"):
            return await call_next(request)

        allowed = _get_allowed_ips()
        if not allowed:
            # No IPs configured — block everything as a safety default
            return _forbidden(request, "Admin panel is not configured. Set ALLOWED_ADMIN_IPS to enable.")

        client_ip = _client_ip(request)
        if client_ip not in allowed:
            return _forbidden(request, f"Access denied. Your IP ({client_ip}) is not in the allowlist.")

        return await call_next(request)


def _client_ip(request: Request) -> str:
    """Return the best-effort client IP, checking X-Forwarded-For first."""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    xreal = request.headers.get("x-real-ip", "")
    if xreal:
        return xreal.strip()
    if request.client:
        return request.client.host
    return "unknown"


def _get_allowed_ips() -> set[str]:
    import os
    ips = os.environ.get("ALLOWED_ADMIN_IPS", "").strip()
    if not ips:
        return set()
    return {ip.strip() for ip in ips.split(",") if ip.strip()}


def _forbidden(request: Request, message: str) -> Response:
    if request.url.path.startswith("/admin/api"):
        return JSONResponse({"detail": message}, status_code=403)
    return Response(
        content=f"<html><body><h1>403 Forbidden</h1><p>{message}</p></body></html>",
        status_code=403,
        media_type="text/html",
    )
