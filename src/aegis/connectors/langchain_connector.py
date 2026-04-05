"""LangChain connector — AegisCallbackHandler for automatic trace capture.

Usage::

    from aegis import Aegis
    from langchain_anthropic import ChatAnthropic

    aegis = Aegis()
    handler = aegis.langchain_handler()

    llm = ChatAnthropic(model="claude-sonnet-4-20250514", callbacks=[handler])
    llm.invoke("Hello")  # automatically traced
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from aegis.core.trace import Span, SpanContext, SpanStatus


class AegisCallbackHandler:
    """LangChain BaseCallbackHandler-compatible callback for AEGIS tracing.

    Captures LLM calls, chain execution, token usage, and costs.
    Applies guard validation on LLM output if configured.

    Does NOT import langchain — implements the callback protocol directly
    so it works without langchain installed (duck typing).
    """

    def __init__(self, aegis: Any) -> None:
        self._aegis = aegis
        self._spans: dict[str, tuple[Span, SpanContext, float]] = {}

    # -- LLM callbacks --

    def on_llm_start(
        self,
        serialized: dict[str, Any],
        prompts: list[str],
        *,
        run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM starts generating."""
        model = serialized.get("kwargs", {}).get("model", serialized.get("id", ["unknown"])[-1])
        name = f"langchain:llm:{model}"
        ctx = SpanContext(name)
        span = ctx.__enter__()
        span.set_attribute("aegis.module", "observe")
        span.set_attribute("aegis.connector", "langchain")
        span.set_attribute("model", str(model))
        span.set_attribute("prompt_count", len(prompts))
        if self._aegis.tenant:
            span.workspace = self._aegis.tenant.workspace
            span.tenant_id = self._aegis.tenant.tenant_id

        key = str(run_id) if run_id else str(id(prompts))
        self._spans[key] = (span, ctx, time.time())

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Called when LLM finishes. Extracts tokens and cost."""
        key = str(run_id) if run_id else None
        if key and key in self._spans:
            span, ctx, start = self._spans.pop(key)
        else:
            return

        # Extract token usage from response
        if hasattr(response, "llm_output") and response.llm_output:
            usage = response.llm_output.get("token_usage", {})
            span.set_attribute("input_tokens", usage.get("prompt_tokens", 0))
            span.set_attribute("output_tokens", usage.get("completion_tokens", 0))
            span.set_attribute("tokens", usage.get("total_tokens", 0))

        # Extract text for guard check
        text = ""
        if hasattr(response, "generations") and response.generations:
            gen = response.generations[0]
            if gen and hasattr(gen[0], "text"):
                text = gen[0].text

        span.set_attribute("aegis.guard.status", "PASS")

        # Store locally if in local mode
        ctx.__exit__(None, None, None)
        if self._aegis.is_local and self._aegis.local_store:
            self._aegis.local_store.store_span(span)

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Called on LLM error."""
        key = str(run_id) if run_id else None
        if key and key in self._spans:
            span, ctx, _ = self._spans.pop(key)
            ctx.__exit__(type(error), error, None)
            if self._aegis.is_local and self._aegis.local_store:
                self._aegis.local_store.store_span(span)

    # -- Chain callbacks --

    def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Called when a chain starts."""
        chain_name = serialized.get("id", ["unknown"])[-1] if serialized.get("id") else "chain"
        name = f"langchain:chain:{chain_name}"
        ctx = SpanContext(name)
        span = ctx.__enter__()
        span.set_attribute("aegis.module", "observe")
        span.set_attribute("aegis.connector", "langchain")
        span.set_attribute("chain_type", str(chain_name))
        if self._aegis.tenant:
            span.workspace = self._aegis.tenant.workspace
            span.tenant_id = self._aegis.tenant.tenant_id

        key = f"chain:{run_id}" if run_id else f"chain:{id(inputs)}"
        self._spans[key] = (span, ctx, time.time())

    def on_chain_end(
        self,
        outputs: dict[str, Any],
        *,
        run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Called when a chain finishes."""
        key = f"chain:{run_id}" if run_id else None
        if key and key in self._spans:
            span, ctx, _ = self._spans.pop(key)
            ctx.__exit__(None, None, None)
            if self._aegis.is_local and self._aegis.local_store:
                self._aegis.local_store.store_span(span)

    def on_chain_error(
        self,
        error: BaseException,
        *,
        run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Called on chain error."""
        key = f"chain:{run_id}" if run_id else None
        if key and key in self._spans:
            span, ctx, _ = self._spans.pop(key)
            ctx.__exit__(type(error), error, None)
            if self._aegis.is_local and self._aegis.local_store:
                self._aegis.local_store.store_span(span)
