"""NexusBridge API application entrypoint.

This is the assembly point for the FastAPI application: it wires the
database initialisation, mounts every API router, exposes a health endpoint
and (if a ``frontend/`` directory exists next to the project root) serves
the static web workspace so the whole product runs from one process.

Run locally (from ``backend/``):

    uvicorn app.main:app --reload

Or with the ASGI server helper: ``python -m app.main``
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__
from .config import settings
from .database import init_db
from .routers import connectors, dashboard, jobs, mappings, preview, webhooks

# Ensure schema + seed data exist before any request can hit the API.
init_db()

app = FastAPI(
    title="NexusBridge API",
    version=__version__,
    description=(
        "NexusBridge: a connector-first data-integration and AI-copilot workspace "
        "that unifies Microsoft 365, Dynamics 365, SharePoint and internal "
        "databases behind one governed, permission-aware API."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/openapi.json",
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(connectors.router)   # /api/connectors
app.include_router(mappings.router)     # /api/mappings
app.include_router(jobs.router)         # /api/jobs
app.include_router(webhooks.router)     # /api/webhooks
app.include_router(preview.router)      # /api/preview
app.include_router(dashboard.router)    # /api/dashboard


# ---------------------------------------------------------------------------
# Health & metadata
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    """Public health payload returned by ``GET /api/health``."""

    status: str = "ok"
    service: str = "nexusbridge"
    version: str = __version__


@app.get("/api/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Liveness probe. Returns 200 with service metadata when the app boots."""
    return HealthResponse()


# ---------------------------------------------------------------------------
# Static frontend (web workspace)
# ---------------------------------------------------------------------------
# The SPA loads assets from the root URL, so we mount the workspace at "/" –
# registered LAST so the /api/* routers, /docs and /health all keep precedence.
_frontend_dist = settings.frontend_dir
if _frontend_dist.is_dir():
    app.mount(
        "/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend"
    )


@app.get("/favicon.ico", include_in_schema=False)
def _favicon() -> FileResponse:
    favicon = settings.frontend_dir / "favicon.ico"
    if favicon.exists():
        return FileResponse(str(favicon))
    # No favicon bundled — return an empty 204 so browsers do not error.
    from fastapi.responses import Response

    return Response(status_code=204)


# ---------------------------------------------------------------------------
# CLI convenience: python -m app.main
# ---------------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )