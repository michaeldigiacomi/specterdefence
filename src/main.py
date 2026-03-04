import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from src.api import router
from src.config import settings
from src.database import init_db


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS Protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HSTS (only in production)
        if not settings.DEBUG:
            response.headers[
                "Strict-Transport-Security"
            ] = "max-age=31536000; includeSubDomains; preload"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "speaker=()"
        )

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup - initialize database
    await init_db()
    yield
    # Shutdown


app = FastAPI(
    title="SpecterDefence API",
    description="Microsoft 365 security posture monitoring and management",
    version="0.1.0",
    lifespan=lifespan,
)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware - only if origins are configured
if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
    )

# Trusted host middleware in production (skip in testing)
if not settings.DEBUG and os.getenv("TESTING") != "true":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "specterdefence.digitaladrenalin.net",
            "*.digitaladrenalin.net",
            "localhost",
            "127.0.0.1",
            "*",  # Allow internal cluster traffic for health probes
        ],
    )

# Include API routers BEFORE static file mounting
app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/ready")
async def ready_check():
    """Readiness check endpoint."""
    return {"status": "ready"}


# Mount static files from frontend dist directory
static_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")

if os.path.exists(static_dir):
    # Serve static assets directly
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # Serve other static files (icons, manifest, etc.)
    @app.get("/logo.svg")
    async def serve_logo():
        return FileResponse(os.path.join(static_dir, "logo.svg"))

    @app.get("/manifest.json")
    async def serve_manifest():
        return FileResponse(os.path.join(static_dir, "manifest.json"))

    @app.get("/service-worker.js")
    async def serve_service_worker():
        return FileResponse(os.path.join(static_dir, "service-worker.js"))

    # Serve icons
    @app.get("/icons/{icon_name}")
    async def serve_icon(icon_name: str):
        icon_path = os.path.join(static_dir, "icons", icon_name)
        if os.path.exists(icon_path):
            return FileResponse(icon_path)
        raise HTTPException(status_code=404, detail="Icon not found")

    # Root path serves index.html
    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(static_dir, "index.html"))

    # All other non-API paths serve index.html for SPA routing
    # This must be registered AFTER all other routes
    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """
        Serve index.html for all non-API routes to support client-side routing.
        This is a catch-all that must be registered last.
        """
        # Skip API routes - they should have been handled above
        if path.startswith("api/") or path == "docs" or path == "openapi.json" or path == "health":
            raise HTTPException(status_code=404, detail="Not found")

        # Check if it's a static file request
        file_path = os.path.join(static_dir, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)

        # Otherwise serve index.html for SPA routing
        return FileResponse(os.path.join(static_dir, "index.html"))

else:
    # No built frontend - serve API-only root endpoint
    @app.get("/")
    async def root():
        """Root endpoint with API info."""
        return {
            "name": "SpecterDefence API",
            "version": "0.1.0",
            "docs": "/docs",
        }
