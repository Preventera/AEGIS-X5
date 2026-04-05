"""AEGIS-X5 Dashboard — full multi-view server with embedded HTML.

Runs on port 4005 by default. Serves the full dashboard with 5 views:
Overview, Agents, Guard, Predictions, Traces.
No React, no npm — single HTML page with inline JS.
"""

from __future__ import annotations

import json
from typing import Any

from aegis.dashboard.html import DASHBOARD_HTML
from aegis.local.store import LocalStore

# ---------------------------------------------------------------------------
# Try FastAPI first, fall back to raw starlette, then http.server
# ---------------------------------------------------------------------------

_HAS_FASTAPI = False
_HAS_STARLETTE = False

try:
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse, JSONResponse

    _HAS_FASTAPI = True
except ImportError:
    try:
        from starlette.applications import Starlette
        from starlette.responses import HTMLResponse, JSONResponse
        from starlette.routing import Route

        _HAS_STARLETTE = True
    except ImportError:
        pass


# Legacy alias for backward compatibility
_DASHBOARD_HTML = DASHBOARD_HTML


def render_dashboard_html(store: LocalStore | None = None) -> str:
    """Return the dashboard HTML string."""
    return DASHBOARD_HTML


def create_app(db_path: str | None = None) -> Any:
    """Create and return a FastAPI/Starlette app serving the full dashboard."""
    store = LocalStore(db_path=db_path)

    if _HAS_FASTAPI:
        # Use the full API factory which includes dashboard endpoints
        from aegis.api.app import create_api

        app = create_api(db_path=db_path, api_keys=[])

        @app.get("/", response_class=HTMLResponse)
        async def index() -> str:
            return DASHBOARD_HTML

        @app.get("/dashboard", response_class=HTMLResponse)
        async def dashboard() -> str:
            return DASHBOARD_HTML

        # Legacy endpoints for backward compatibility
        @app.get("/api/stats")
        async def api_stats_legacy(workspace: str | None = None) -> dict:
            return store.stats(workspace=workspace)

        @app.get("/api/traces")
        async def api_traces_legacy(limit: int = 100, workspace: str | None = None) -> list:
            return store.recent_traces(limit=limit, workspace=workspace)

        return app

    if _HAS_STARLETTE:

        async def index(request: Any) -> Any:
            return HTMLResponse(DASHBOARD_HTML)

        async def api_stats(request: Any) -> Any:
            ws = request.query_params.get("workspace")
            return JSONResponse(store.stats(workspace=ws))

        async def api_traces(request: Any) -> Any:
            ws = request.query_params.get("workspace")
            limit = int(request.query_params.get("limit", 100))
            return JSONResponse(store.recent_traces(limit=limit, workspace=ws))

        app = Starlette(
            routes=[
                Route("/", index),
                Route("/dashboard", index),
                Route("/api/stats", api_stats),
                Route("/api/traces", api_traces),
            ]
        )
        return app

    return None
