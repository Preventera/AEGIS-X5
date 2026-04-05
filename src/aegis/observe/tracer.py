"""Tracer universel — sync + async, auto-detect, with token/cost/metrics enrichment."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from typing import Any

from aegis.core.tenant import Tenant, get_current_tenant
from aegis.core.trace import Span, SpanContext
from aegis.observe.cost import CostCalculator
from aegis.observe.metrics import SlidingWindowMetrics
from aegis.observe.tokens import TokenUsage, extract_tokens


class Tracer:
    """Universal tracer — wraps sync and async callables transparently.

    Features:
      - Auto-detects sync vs async functions
      - Extracts tokens from LLM responses (multi-format)
      - Computes costs via a configurable :class:`CostCalculator`
      - Records latency into a :class:`SlidingWindowMetrics` window
    """

    def __init__(
        self,
        *,
        tenant: Tenant | None = None,
        cost_calculator: CostCalculator | None = None,
        metrics: SlidingWindowMetrics | None = None,
    ) -> None:
        self._tenant = tenant
        self._cost = cost_calculator or CostCalculator()
        self._metrics = metrics or SlidingWindowMetrics()

    @property
    def cost_calculator(self) -> CostCalculator:
        return self._cost

    @property
    def metrics(self) -> SlidingWindowMetrics:
        return self._metrics

    def trace(
        self,
        name: str | None = None,
        *,
        model: str = "",
        **attributes: Any,
    ) -> Callable:
        """Decorator: auto-detect sync/async, trace the call, enrich span.

        Usage::

            tracer = Tracer()

            @tracer.trace("llm-call", model="claude-sonnet")
            def call_llm(prompt: str) -> dict:
                ...

            @tracer.trace("embed", model="text-embedding-3")
            async def embed(texts: list[str]) -> dict:
                ...
        """

        def decorator(func: Callable) -> Callable:
            span_name = name or func.__qualname__

            if inspect.iscoroutinefunction(func):

                @functools.wraps(func)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    with SpanContext(span_name, **attributes) as span:
                        self._enrich_start(span, model)
                        result = await func(*args, **kwargs)
                        self._enrich_end(span, result, model)
                        return result

                return async_wrapper
            else:

                @functools.wraps(func)
                def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                    with SpanContext(span_name, **attributes) as span:
                        self._enrich_start(span, model)
                        result = func(*args, **kwargs)
                        self._enrich_end(span, result, model)
                        return result

                return sync_wrapper

        return decorator

    def _enrich_start(self, span: Span, model: str) -> None:
        """Set tenant and model info at span start."""
        tenant = self._tenant or get_current_tenant()
        if tenant:
            span.workspace = tenant.workspace
            span.tenant_id = tenant.tenant_id
        span.set_attribute("aegis.module", "observe")
        if model:
            span.set_attribute("aegis.model", model)

    def _enrich_end(self, span: Span, result: Any, model: str) -> None:
        """Extract tokens, compute cost, record latency after call completes."""
        # Token extraction
        usage = extract_tokens(result) if result is not None else TokenUsage()
        if usage.total_tokens:
            span.set_attribute("aegis.tokens.input", usage.input_tokens)
            span.set_attribute("aegis.tokens.output", usage.output_tokens)
            span.set_attribute("aegis.tokens.total", usage.total_tokens)

        # Cost
        if model and usage.total_tokens:
            cost = self._cost.compute(usage, model=model)
            span.set_attribute("aegis.cost.total", cost.total_cost)
            span.set_attribute("aegis.cost.currency", cost.currency)

        # Latency metric (always record, even if 0ms)
        self._metrics.record(span.duration_ms)
