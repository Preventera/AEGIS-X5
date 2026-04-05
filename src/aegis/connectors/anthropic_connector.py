"""Anthropic connector — transparent wrapper for the Anthropic SDK.

Usage::

    from anthropic import Anthropic
    from aegis import Aegis

    aegis = Aegis()
    client = aegis.wrap_anthropic(Anthropic())

    # All calls are now automatically traced
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Hello"}],
    )
"""

from __future__ import annotations

import time
from typing import Any

from aegis.core.trace import SpanContext


class _WrappedMessages:
    """Wraps ``client.messages`` to intercept ``create()``."""

    def __init__(self, original: Any, aegis: Any) -> None:
        self._original = original
        self._aegis = aegis

    def create(self, **kwargs: Any) -> Any:
        """Traced version of messages.create()."""
        model = kwargs.get("model", "unknown")
        aegis = self._aegis

        with SpanContext(f"anthropic:{model}") as span:
            span.set_attribute("aegis.module", "observe")
            span.set_attribute("aegis.connector", "anthropic")
            span.set_attribute("model", model)
            if aegis.tenant:
                span.workspace = aegis.tenant.workspace
                span.tenant_id = aegis.tenant.tenant_id

            response = self._original.create(**kwargs)

            # Extract usage from response
            if hasattr(response, "usage") and response.usage:
                usage = response.usage
                input_t = getattr(usage, "input_tokens", 0) or 0
                output_t = getattr(usage, "output_tokens", 0) or 0
                span.set_attribute("input_tokens", input_t)
                span.set_attribute("output_tokens", output_t)
                span.set_attribute("tokens", input_t + output_t)

            span.set_attribute("aegis.guard.status", "PASS")

        # Store locally
        if aegis.is_local and aegis.local_store:
            aegis.local_store.store_span(span)

        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


class WrappedAnthropicClient:
    """Transparent wrapper around an Anthropic client instance.

    Intercepts ``client.messages.create()`` for automatic tracing.
    All other attributes are proxied to the original client.
    """

    def __init__(self, client: Any, aegis: Any) -> None:
        self._client = client
        self._aegis = aegis
        self.messages = _WrappedMessages(client.messages, aegis)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


def wrap_anthropic(client: Any, aegis: Any) -> WrappedAnthropicClient:
    """Wrap an Anthropic client for automatic AEGIS tracing.

    Parameters
    ----------
    client : anthropic.Anthropic
        The Anthropic client instance.
    aegis : Aegis
        The AEGIS client instance.

    Returns
    -------
    WrappedAnthropicClient
        A wrapped client that traces all message creation calls.
    """
    return WrappedAnthropicClient(client, aegis)
