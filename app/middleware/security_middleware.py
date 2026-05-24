from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Enable XSS filter in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS (only if HTTPS is configured)
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Cache control for sensitive pages
        path = request.url.path
        if path.startswith("/my-projects") or path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

        return response
