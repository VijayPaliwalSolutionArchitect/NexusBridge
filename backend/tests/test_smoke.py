"""Smoke tests: every module imports and the app boots.

This is the minimal guarantee that the application is runnable — if importing
`:mod:`app.main` succeeds and the health endpoint responds, the whole stack
(fastapi, uvicorn, pydantic, routers, database, engine) is wired correctly.
"""

from __future__ import annotations

import importlib

# Every backend module must import cleanly.  This deliberately pulls each
# router plus the core modules so a broken file is caught here, not at runtime.
MODULES = [
    "app.config",
    "app.database",
    "app.engine",
    "app.models",
    "app.main",
    "app.routers.connectors",
    "app.routers.dashboard",
    "app.routers.jobs",
    "app.routers.mappings",
    "app.routers.preview",
    "app.routers.webhooks",
]


def test_all_modules_import() -> None:
    for name in MODULES:
        importlib.import_module(name)


def test_health_endpoint(client) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "nexusbridge"


def test_openapi_schema_is_generated(client) -> None:
    resp = client.get("/api/openapi.json")
    assert resp.status_code == 200
    paths = resp.json()["paths"]
    assert "/api/connectors" in paths
    assert "/api/jobs" in paths
    assert "/api/mappings" in paths
    assert "/api/dashboard" in paths
    assert "/api/webhooks" in paths


def test_docs_page_served(client) -> None:
    assert client.get("/docs").status_code == 200