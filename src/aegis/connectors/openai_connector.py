"""OpenAI connector — transparent wrapper for the OpenAI SDK.

Usage::

    from openai import OpenAI
    from aegis import Aegis

    aegis = Aegis()
    client = aegis.wrap_openai(OpenAI())

    # All calls are now automatically traced
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}],
    )
"""

from __future__ import annotations

import time
from typing import Any

from aegis.core.trace import SpanContext


class _WrappedCompletions:
    """Wraps ``client.chat.completions`` to intercept ``create()``."""

    def __init__(self, original: Any, aegis: Any) -> None:
        self._original = original
        self._aegis = aegis

    def create(self, **kwargs: Any) -> Any:
        """Traced version of chat.completions.create()."""
        model = kwargs.get("model", "unknown")
        aegis = self._aegis

        with SpanContext(f"openai:{model}") as span:
            span.set_attribute("aegis.module", "observe")
            span.set_attribute("aegis.connector", "openai")
            span.set_attribute("model", model)
            if aegis.tenant:
                span.workspace = aegis.tenant.workspace
                span.tenant_id = aegis.tenant.tenant_id

            response = self._original.create(**kwargs)

            # Extract usage from response
            if hasattr(response, "usage") and response.usage:
                span.set_attribute("input_tokens", response.usage.prompt_tokens or 0)
                span.set_attribute("output_tokens", response.usage.completion_tokens or 0)
                span.set_attribute("tokens", response.usage.total_tokens or 0)

            span.set_attribute("aegis.guard.status", "PASS")

        # Store locally
        if aegis.is_local and aegis.local_store:
            aegis.local_store.store_span(span)

        return response

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


class _WrappedChat:
    """Wraps ``client.chat`` to intercept ``completions``."""

    def __init__(self, original_chat: Any, aegis: Any) -> None:
        self._original = original_chat
        self._aegis = aegis
        self.completions = _WrappedCompletions(original_chat.completions, aegis)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._original, name)


class WrappedOpenAIClient:
    """Transparent wrapper around an OpenAI client instance.

    Intercepts ``client.chat.completions.create()`` for automatic tracing.
    All other attributes are proxied to the original client.
    """

    def __init__(self, client: Any, aegis: Any) -> None:
        self._client = client
        self._aegis = aegis
        self.chat = _WrappedChat(client.chat, aegis)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


def wrap_openai(client: Any, aegis: Any) -> WrappedOpenAIClient:
    """Wrap an OpenAI client for automatic AEGIS tracing.

    Parameters
    ----------
    client : openai.OpenAI
        The OpenAI client instance.
    aegis : Aegis
        The AEGIS client instance.

    Returns
    -------
    WrappedOpenAIClient
        A wrapped client that traces all chat completion calls.
    """
    return WrappedOpenAIClient(client, aegis)
