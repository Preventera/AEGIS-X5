"""Tracing — spans, context manager, and in-memory trace collection."""

from __future__ import annotations

import contextvars
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from aegis.core.tenant import get_current_tenant

# ---------------------------------------------------------------------------
# Span status
# ---------------------------------------------------------------------------


class SpanStatus(str, Enum):
    OK = "ok"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Span — single unit of traced work
# ---------------------------------------------------------------------------


@dataclass
class Span:
    """A single traced operation.

    Carries tenant context (workspace / tenant_id) captured at creation time.
    """

    name: str
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    parent_id: str | None = None
    workspace: str = ""
    tenant_id: str = ""
    status: SpanStatus = SpanStatus.OK
    start_time: float = 0.0
    end_time: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    @property
    def duration_ms(self) -> float:
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, **attrs: Any) -> None:
        self.events.append({"name": name, "time": time.time(), **attrs})

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "workspace": self.workspace,
            "tenant_id": self.tenant_id,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": self.events,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Active span context — propagates parent automatically
# ---------------------------------------------------------------------------

_active_span: contextvars.ContextVar[Span | None] = contextvars.ContextVar(
    "aegis_active_span", default=None
)


def get_active_span() -> Span | None:
    return _active_span.get()


# ---------------------------------------------------------------------------
# SpanContext — context manager returned by aegis.trace()
# ---------------------------------------------------------------------------


class SpanContext:
    """Context manager that creates, activates, and finalises a :class:`Span`.

    Usage::

        with SpanContext("my-operation") as span:
            span.set_attribute("input_tokens", 150)
    """

    def __init__(self, name: str, **attributes: Any) -> None:
        tenant = get_current_tenant()
        parent = _active_span.get()

        self._span = Span(
            name=name,
            parent_id=parent.span_id if parent else None,
            workspace=tenant.workspace if tenant else "",
            tenant_id=tenant.tenant_id if tenant else "",
            attributes=dict(attributes),
        )
        self._token: contextvars.Token[Span | None] | None = None

    def __enter__(self) -> Span:
        self._span.start_time = time.time()
        self._token = _active_span.set(self._span)
        return self._span

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None, *_: object) -> None:
        self._span.end_time = time.time()
        if exc_val is not None:
            self._span.status = SpanStatus.ERROR
            self._span.error = str(exc_val)
        # Collect the finished span
        _collector.collect(self._span)
        # Restore parent span
        if self._token is not None:
            _active_span.reset(self._token)


# ---------------------------------------------------------------------------
# In-memory trace collector (replaced by Observe module later)
# ---------------------------------------------------------------------------


class TraceCollector:
    """Simple in-memory span sink — production implementations swap this out."""

    def __init__(self) -> None:
        self._spans: list[Span] = []

    def collect(self, span: Span) -> None:
        self._spans.append(span)

    @property
    def spans(self) -> list[Span]:
        return list(self._spans)

    def clear(self) -> None:
        self._spans.clear()


_collector = TraceCollector()


def get_collector() -> TraceCollector:
    """Return the global trace collector."""
    return _collector
