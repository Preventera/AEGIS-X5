"""AEGIS-X5 REST API — FastAPI application factory.

Endpoints:
    POST /api/v1/trace          Record a trace
    POST /api/v1/guard/validate Validate output through guard pipeline
    GET  /api/v1/health         Health check
    GET  /api/v1/agents         List agents with health scores
    GET  /api/v1/predictions    Active predictions
"""

from __future__ import annotations

import os
import time
from typing import Any

from aegis.api.auth import require_api_key

# Defer FastAPI import to allow running without it installed
try:
    from fastapi import Depends, FastAPI, Header, HTTPException, Request
    from fastapi.responses import JSONResponse

    _HAS_FASTAPI = True
except ImportError:
    _HAS_FASTAPI = False


def create_api(
    *,
    db_path: str | None = None,
    api_keys: list[str] | None = None,
) -> Any:
    """Create the AEGIS-X5 REST API application.

    Parameters
    ----------
    db_path : str | None
        Path to local SQLite DB (for local/dev mode).
    api_keys : list[str] | None
        Valid API keys. Defaults to AEGIS_API_KEYS env var (comma-separated).
    """
    if not _HAS_FASTAPI:
        raise ImportError("FastAPI required: pip install aegis-x5[dashboard]")

    from aegis.local.store import LocalStore
    from aegis.predict.engine import PredictionEngine
    from aegis.predict.health_score import HealthScore
    from aegis.guard.pipeline import GuardPipeline
    from aegis.guard.validators import PIIDetector, InjectionDetector, HallucinationDetector
    from aegis.core.trace import Span, SpanStatus

    # Initialize shared state
    store = LocalStore(db_path=db_path)
    engine = PredictionEngine()
    health = engine.health_score

    # Default guard pipeline
    pipeline = GuardPipeline()
    pipeline.add(PIIDetector()).add(InjectionDetector()).add(HallucinationDetector())

    # API key list
    valid_keys = api_keys or _load_api_keys()

    app = FastAPI(
        title="AEGIS-X5 API",
        version="0.3.0",
        description="Autonomous Agent Governance — REST API",
        docs_url="/api/docs",
        redoc_url=None,
    )

    # --- Auth dependency ---

    async def verify_key(x_api_key: str = Header(default="", alias="X-API-Key")) -> str:
        if not valid_keys:
            return "anonymous"  # no keys configured → open access
        if x_api_key not in valid_keys:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return x_api_key

    # --- POST /api/v1/trace ---

    @app.post("/api/v1/trace")
    async def record_trace(request: Request, key: str = Depends(verify_key)) -> dict:
        """Record a trace span."""
        body = await request.json()
        span = Span(
            name=body.get("name", "api-trace"),
            workspace=body.get("workspace", "api"),
            tenant_id=body.get("tenant_id", ""),
            attributes=body.get("attributes", {}),
        )
        span.start_time = body.get("start_time", time.time())
        span.end_time = body.get("end_time", time.time())
        if body.get("status") == "error":
            span.status = SpanStatus.ERROR
            span.error = body.get("error", "")
        summary = store.store_span(span)
        return {
            "status": "ok",
            "span_id": span.span_id,
            "duration_ms": summary.duration_ms,
        }

    # --- POST /api/v1/guard/validate ---

    @app.post("/api/v1/guard/validate")
    async def guard_validate(request: Request, key: str = Depends(verify_key)) -> dict:
        """Validate content through the guard pipeline."""
        body = await request.json()
        content = body.get("content", "")
        context = body.get("context")
        result = pipeline.run(content, context=context)
        return {
            "passed": result.passed,
            "needs_approval": result.needs_approval,
            "blocked_by": result.blocked_by.rule if result.blocked_by else None,
            "results": [
                {
                    "rule": r.rule,
                    "passed": r.passed,
                    "level": r.level.name,
                    "message": r.message,
                }
                for r in result.results
            ],
        }

    # --- GET /api/v1/health ---

    @app.get("/api/v1/health")
    async def health_check() -> dict:
        """Health check endpoint (no auth required)."""
        stats = store.stats()
        return {
            "status": "ok",
            "version": "0.3.0",
            "total_traces": stats["total_traces"],
            "uptime": "running",
        }

    # --- GET /api/v1/agents ---

    @app.get("/api/v1/agents")
    async def list_agents(key: str = Depends(verify_key)) -> dict:
        """List agents with their latest health scores."""
        workspaces = store.workspaces()
        agents = []
        for ws in workspaces:
            ws_stats = store.stats(workspace=ws)
            recent = store.recent_traces(limit=1, workspace=ws)
            last_seen = recent[0]["created_at"] if recent else None
            agents.append({
                "workspace": ws,
                "total_traces": ws_stats["total_traces"],
                "avg_latency_ms": ws_stats["avg_latency_ms"],
                "guard_blocks": ws_stats["guard_blocks"],
                "last_seen": last_seen,
            })
        return {"agents": agents, "count": len(agents)}

    # --- GET /api/v1/predictions ---

    @app.get("/api/v1/predictions")
    async def list_predictions(key: str = Depends(verify_key)) -> dict:
        """List active predictions and accuracy metrics."""
        pending = engine.pending_predictions()
        accuracy = engine.accuracy()
        return {
            "pending": [
                {
                    "id": p.prediction_id,
                    "metric": p.metric,
                    "agent_id": p.agent_id,
                    "predicted_value": p.predicted_value,
                    "horizon_hours": p.horizon_hours,
                }
                for p in pending
            ],
            "accuracy": accuracy,
            "pending_count": len(pending),
        }

    # --- GET /api/v1/stats ---

    @app.get("/api/v1/stats")
    async def get_stats(
        workspace: str | None = None, key: str = Depends(verify_key)
    ) -> dict:
        """Aggregate trace statistics."""
        return store.stats(workspace=workspace)

    # --- GET /api/v1/traces ---

    @app.get("/api/v1/traces")
    async def get_traces(
        limit: int = 50,
        workspace: str | None = None,
        key: str = Depends(verify_key),
    ) -> dict:
        """Recent traces."""
        traces = store.recent_traces(limit=limit, workspace=workspace)
        return {"traces": traces, "count": len(traces)}

    return app


def _load_api_keys() -> list[str]:
    """Load API keys from AEGIS_API_KEYS env var (comma-separated)."""
    raw = os.environ.get("AEGIS_API_KEYS", "")
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]
