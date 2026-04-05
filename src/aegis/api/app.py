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

# Defer FastAPI import to allow running without it installed
try:
    from fastapi import Depends, FastAPI, Header, HTTPException, Request

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

    from aegis.core.trace import Span, SpanStatus
    from aegis.guard.pipeline import GuardPipeline
    from aegis.guard.validators import HallucinationDetector, InjectionDetector, PIIDetector
    from aegis.local.store import LocalStore
    from aegis.predict.engine import PredictionEngine

    # Initialize shared state
    store = LocalStore(db_path=db_path)
    engine = PredictionEngine()

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

    # -----------------------------------------------------------------------
    # Dashboard endpoints
    # -----------------------------------------------------------------------

    @app.get("/api/v1/dashboard/overview")
    async def dashboard_overview(workspace: str | None = None) -> dict:
        """Aggregated KPIs for the dashboard overview."""
        all_traces = store.recent_traces(limit=5000, workspace=workspace)
        stats = store.stats(workspace=workspace)

        # Compute cost and faithfulness from attributes
        total_cost = 0.0
        faith_sum = 0.0
        faith_count = 0
        guard_block_traces = []

        for t in all_traces:
            attrs = t.get("attributes", "{}")
            if isinstance(attrs, str):
                import json as _json

                try:
                    attrs = _json.loads(attrs)
                except Exception:
                    attrs = {}

            cost = attrs.get("cost", attrs.get("aegis.cost", 0))
            total_cost += float(cost) if cost else 0

            faith = attrs.get("faithfulness", 0)
            if faith:
                faith_sum += float(faith)
                faith_count += 1

            if t.get("status") == "error":
                guard_block_traces.append({
                    "message": t.get("error", "Guard block"),
                    "agent": t.get("name", ""),
                    "severity": "critical" if "N4" in str(t.get("error", "")) else "warning",
                    "time": t.get("created_at", 0),
                })

        workspaces = store.workspaces()
        # Count unique agent names
        agent_names = {t["name"].split(":")[0] for t in all_traces}

        avg_faith = (faith_sum / faith_count) if faith_count > 0 else 0.0

        # Health scores for agents
        health_scores = []
        for name in agent_names:
            agent_traces = [t for t in all_traces if t["name"].startswith(name)]
            if agent_traces:
                avg_lat = sum(t["duration_ms"] for t in agent_traces) / len(agent_traces)
                err_count = sum(1 for t in agent_traces if t["status"] == "error")
                err_rate = err_count / len(agent_traces)
                score = max(0, min(100, 100 - err_rate * 200 - max(0, avg_lat - 500) / 50))
                health_scores.append(score)

        avg_health = (sum(health_scores) / len(health_scores)) if health_scores else 100.0

        return {
            "total_traces": stats["total_traces"],
            "active_agents": len(agent_names),
            "avg_health": round(avg_health, 1),
            "total_cost": round(total_cost, 4),
            "guard_blocks": stats["guard_blocks"],
            "avg_faithfulness": round(avg_faith, 4),
            "avg_latency_ms": stats["avg_latency_ms"],
            "alerts": guard_block_traces[:20],
        }

    @app.get("/api/v1/dashboard/agents")
    async def dashboard_agents(workspace: str | None = None) -> dict:
        """List agents with health scores for the dashboard."""
        all_traces = store.recent_traces(limit=5000, workspace=workspace)

        # Group by agent name prefix
        from collections import defaultdict

        by_agent: dict[str, list] = defaultdict(list)
        for t in all_traces:
            agent = t["name"].split(":")[0]
            by_agent[agent].append(t)

        agents = []
        for name, traces in by_agent.items():
            count = len(traces)
            avg_lat = sum(t["duration_ms"] for t in traces) / count
            max_lat = max(t["duration_ms"] for t in traces)
            err_count = sum(1 for t in traces if t["status"] == "error")
            err_rate = err_count / count
            last_seen = max(t["created_at"] for t in traces)

            # Simple health score
            score = max(0, min(100, 100 - err_rate * 200 - max(0, avg_lat - 500) / 50))

            agents.append({
                "name": name,
                "workspace": traces[0]["workspace"],
                "health_score": round(score, 1),
                "total_traces": count,
                "avg_latency_ms": round(avg_lat, 1),
                "max_latency_ms": round(max_lat, 1),
                "error_rate": round(err_rate, 3),
                "guard_blocks": err_count,
                "last_seen": last_seen,
            })

        agents.sort(key=lambda a: a["health_score"])
        return {"agents": agents, "count": len(agents)}

    @app.get("/api/v1/dashboard/guard")
    async def dashboard_guard(workspace: str | None = None) -> dict:
        """Guard event summary for the dashboard."""
        all_traces = store.recent_traces(limit=5000, workspace=workspace)

        events = []
        pii = 0
        injection = 0
        hallucination = 0
        total_blocks = 0

        for t in all_traces:
            if t.get("status") != "error":
                continue
            total_blocks += 1
            error = t.get("error", "")
            name = t.get("name", "")

            # Categorize
            if "pii" in error.lower() or "pii" in name.lower():
                pii += 1
            elif "injection" in error.lower():
                injection += 1
            elif "hallucination" in error.lower() or "faithfulness" in error.lower():
                hallucination += 1

            # Extract level from error message
            level = "N3"
            if "N4" in error:
                level = "N4"
            elif "N2" in error:
                level = "N2"

            rule = ""
            if ":" in error:
                rule = error.split(":")[0].strip()

            events.append({
                "name": name,
                "agent": name.split(":")[0],
                "level": level,
                "rule": rule,
                "message": error,
                "time": t.get("created_at", 0),
            })

        events.sort(key=lambda e: e["time"], reverse=True)

        return {
            "total_blocks": total_blocks,
            "pii_blocks": pii,
            "injection_blocks": injection,
            "hallucination_blocks": hallucination,
            "events": events[:50],
        }

    @app.get("/api/v1/dashboard/predictions")
    async def dashboard_predictions(workspace: str | None = None) -> dict:
        """Prediction data for the dashboard."""
        all_traces = store.recent_traces(limit=5000, workspace=workspace)

        # Group by agent and compute health scores
        from collections import defaultdict

        by_agent: dict[str, list] = defaultdict(list)
        for t in all_traces:
            agent = t["name"].split(":")[0]
            by_agent[agent].append(t)

        health_scores = []
        anomalies = []

        for name, traces in by_agent.items():
            count = len(traces)
            avg_lat = sum(t["duration_ms"] for t in traces) / count
            err_rate = sum(1 for t in traces if t["status"] == "error") / count
            score = max(0, min(100, 100 - err_rate * 200 - max(0, avg_lat - 500) / 50))
            health_scores.append(score)

            # Detect anomalies (simple: latency spikes)
            lats = [t["duration_ms"] for t in traces]
            if len(lats) >= 5:
                import statistics

                mean_lat = statistics.mean(lats)
                stdev_lat = statistics.stdev(lats) if len(lats) >= 2 else 0
                if stdev_lat > 0:
                    for t in traces[-5:]:
                        z = (t["duration_ms"] - mean_lat) / stdev_lat
                        if abs(z) > 3:
                            anomalies.append({
                                "agent": name,
                                "metric": "latency",
                                "direction": "spike" if z > 0 else "drop",
                                "message": f"{name}: latency {t['duration_ms']:.0f}ms (z={z:.1f})",
                            })

        # Health distribution
        dist = {"0-59": 0, "60-79": 0, "80-100": 0}
        for s in health_scores:
            if s >= 80:
                dist["80-100"] += 1
            elif s >= 60:
                dist["60-79"] += 1
            else:
                dist["0-59"] += 1

        # Drift alerts (count agents with degrading health)
        drift_alerts = sum(1 for s in health_scores if s < 70)

        return {
            "avg_health": round(sum(health_scores) / len(health_scores), 1) if health_scores else 0,
            "health_distribution": dist,
            "drift_alerts": drift_alerts,
            "anomaly_count": len(anomalies),
            "anomalies": anomalies[:20],
            "predictions_count": len(engine.pending_predictions()),
        }

    @app.get("/api/v1/dashboard/traces")
    async def dashboard_traces(
        limit: int = 200,
        workspace: str | None = None,
        status: str | None = None,
        name: str | None = None,
    ) -> dict:
        """Paginated traces with filters for the dashboard."""
        traces = store.recent_traces(limit=limit, workspace=workspace)
        if status:
            traces = [t for t in traces if t["status"] == status]
        if name:
            traces = [t for t in traces if name.lower() in t["name"].lower()]
        return {"traces": traces, "count": len(traces)}

    return app


def _load_api_keys() -> list[str]:
    """Load API keys from AEGIS_API_KEYS env var (comma-separated)."""
    raw = os.environ.get("AEGIS_API_KEYS", "")
    if not raw:
        return []
    return [k.strip() for k in raw.split(",") if k.strip()]
