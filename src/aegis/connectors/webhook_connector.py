"""Webhook connector — receive traces via HTTP POST from any language.

Provides a standardized endpoint for non-Python clients (Node.js, Go, etc.)
to send traces to AEGIS-X5.

Usage::

    from aegis import Aegis

    aegis = Aegis()
    router = aegis.webhook_endpoint()
    # Mount on your FastAPI app: app.include_router(router)

Payload format::

    POST /webhook/trace
    {
        "agent": "my-agent",
        "input": "user prompt",
        "output": "agent response",
        "model": "gpt-4o",
        "tokens": 1250,
        "metadata": {"custom": "data"}
    }
"""

from __future__ import annotations

import time
from typing import Any

from aegis.core.trace import Span, SpanStatus


def create_webhook_router(aegis: Any) -> Any:
    """Create a FastAPI APIRouter for receiving webhook traces.

    Parameters
    ----------
    aegis : Aegis
        The AEGIS client instance.

    Returns
    -------
    fastapi.APIRouter
        Router with /webhook/trace and /webhook/validate endpoints.
    """
    try:
        from fastapi import APIRouter, Body, HTTPException
    except ImportError as exc:
        raise ImportError("FastAPI required for webhook: pip install aegis-x5[dashboard]") from exc

    router = APIRouter(prefix="/webhook", tags=["webhook"])

    @router.post("/trace")
    async def receive_trace(body: dict = Body(...)) -> dict:
        """Receive and store a trace from an external agent."""
        # Validate required field
        agent = body.get("agent", "")
        if not agent:
            raise HTTPException(status_code=422, detail="'agent' field is required")

        # Build span from payload
        span = Span(
            name=f"webhook:{agent}",
            workspace=body.get("workspace", aegis.workspace),
            tenant_id=body.get("tenant_id", aegis.tenant_id if aegis.tenant else ""),
        )

        now = time.time()
        latency = body.get("latency_ms", 0)
        span.start_time = now - (latency / 1000.0) if latency else now
        span.end_time = now

        # Set attributes
        span.set_attribute("aegis.module", "observe")
        span.set_attribute("aegis.connector", "webhook")
        span.set_attribute("agent", agent)

        if body.get("model"):
            span.set_attribute("model", body["model"])
        if body.get("tokens"):
            span.set_attribute("tokens", body["tokens"])
        if body.get("input_tokens"):
            span.set_attribute("input_tokens", body["input_tokens"])
        if body.get("output_tokens"):
            span.set_attribute("output_tokens", body["output_tokens"])
        if body.get("cost"):
            span.set_attribute("cost", body["cost"])

        # Metadata
        for k, v in body.get("metadata", {}).items():
            span.set_attribute(f"meta.{k}", v)

        # Error handling
        if body.get("error"):
            span.status = SpanStatus.ERROR
            span.error = str(body["error"])

        span.set_attribute("aegis.guard.status", "PASS")

        # Store
        summary = None
        if aegis.is_local and aegis.local_store:
            summary = aegis.local_store.store_span(span)

        return {
            "status": "ok",
            "span_id": span.span_id,
            "agent": agent,
            "duration_ms": span.duration_ms,
        }

    @router.post("/validate")
    async def validate_output(body: dict = Body(...)) -> dict:
        """Validate agent output through the guard pipeline."""
        content = body.get("output", body.get("content", ""))
        if not content:
            raise HTTPException(status_code=422, detail="'output' or 'content' field required")

        from aegis.guard.pipeline import GuardPipeline
        from aegis.guard.validators import PIIDetector, InjectionDetector

        pipeline = GuardPipeline()
        pipeline.add(PIIDetector()).add(InjectionDetector())
        result = pipeline.run(content, context=body.get("context"))

        return {
            "passed": result.passed,
            "blocked_by": result.blocked_by.rule if result.blocked_by else None,
            "results": [
                {"rule": r.rule, "passed": r.passed, "level": r.level.name}
                for r in result.results
            ],
        }

    return router
