"""Tests for aegis.core.trace — spans, context manager, collector."""

from __future__ import annotations

import time

import pytest

from aegis.core.tenant import Tenant, TenantContext
from aegis.core.trace import Span, SpanContext, SpanStatus, get_active_span, get_collector


@pytest.fixture(autouse=True)
def _clear_collector():
    """Clear collected spans before each test."""
    get_collector().clear()
    yield
    get_collector().clear()


class TestSpan:
    def test_defaults(self):
        s = Span(name="test")
        assert s.name == "test"
        assert s.status == SpanStatus.OK
        assert s.duration_ms == 0.0
        assert len(s.span_id) == 16

    def test_set_attribute(self):
        s = Span(name="x")
        s.set_attribute("model", "claude")
        assert s.attributes["model"] == "claude"

    def test_add_event(self):
        s = Span(name="x")
        s.add_event("token_count", count=42)
        assert len(s.events) == 1
        assert s.events[0]["name"] == "token_count"
        assert s.events[0]["count"] == 42

    def test_duration(self):
        s = Span(name="x", start_time=1.0, end_time=1.05)
        assert abs(s.duration_ms - 50.0) < 0.01

    def test_to_dict(self):
        s = Span(name="op", workspace="ws", tenant_id="tid")
        d = s.to_dict()
        assert d["name"] == "op"
        assert d["workspace"] == "ws"
        assert d["tenant_id"] == "tid"
        assert d["status"] == "ok"


class TestSpanContext:
    def test_basic_trace(self):
        with SpanContext("my-op") as span:
            assert span.name == "my-op"
            assert span.start_time > 0
        assert span.end_time >= span.start_time
        assert span.status == SpanStatus.OK

    def test_collects_span(self):
        with SpanContext("collected"):
            pass
        spans = get_collector().spans
        assert len(spans) == 1
        assert spans[0].name == "collected"

    def test_error_status_on_exception(self):
        with pytest.raises(ValueError):
            with SpanContext("fail") as span:
                raise ValueError("bad input")
        assert span.status == SpanStatus.ERROR
        assert span.error == "bad input"

    def test_tenant_propagation(self):
        tenant = Tenant(workspace="acme", tenant_id="t123")
        with TenantContext(tenant):
            with SpanContext("tenant-op") as span:
                pass
        assert span.workspace == "acme"
        assert span.tenant_id == "t123"

    def test_nested_spans_parent_id(self):
        with SpanContext("parent") as parent:
            with SpanContext("child") as child:
                pass
        assert child.parent_id == parent.span_id
        assert parent.parent_id is None

    def test_active_span_inside_context(self):
        assert get_active_span() is None
        with SpanContext("active") as span:
            assert get_active_span() is span
        assert get_active_span() is None

    def test_attributes_passed_at_creation(self):
        with SpanContext("attr-op", model="gpt-4") as span:
            pass
        assert span.attributes["model"] == "gpt-4"


class TestTraceCollector:
    def test_clear(self):
        with SpanContext("a"):
            pass
        assert len(get_collector().spans) == 1
        get_collector().clear()
        assert len(get_collector().spans) == 0

    def test_multiple_spans(self):
        for i in range(5):
            with SpanContext(f"op-{i}"):
                pass
        assert len(get_collector().spans) == 5
