"""Tests for aegis.observe.exporter — OTLP-compatible span export."""

from __future__ import annotations

from aegis.core.trace import Span, SpanStatus
from aegis.observe.exporter import OTLPDictExporter, _otlp_value


class TestOTLPDictExporter:
    def test_export_single_span(self):
        exporter = OTLPDictExporter()
        span = Span(
            name="test-op",
            span_id="abc123",
            workspace="ws",
            tenant_id="tid",
            start_time=1000.0,
            end_time=1001.5,
        )
        span.set_attribute("model", "claude")
        exporter.export([span])

        assert len(exporter.batches) == 1
        batch = exporter.batches[0]
        assert len(batch) == 1
        otlp = batch[0]
        assert otlp["name"] == "test-op"
        assert otlp["spanId"] == "abc123"
        assert otlp["kind"] == "SPAN_KIND_INTERNAL"
        assert otlp["status"]["code"] == "STATUS_CODE_OK"
        assert otlp["startTimeUnixNano"] == 1_000_000_000_000
        assert otlp["endTimeUnixNano"] == 1_001_500_000_000

    def test_error_status(self):
        exporter = OTLPDictExporter()
        span = Span(name="err", status=SpanStatus.ERROR, error="fail")
        exporter.export([span])
        otlp = exporter.batches[0][0]
        assert otlp["status"]["code"] == "STATUS_CODE_ERROR"
        assert otlp["status"]["message"] == "fail"

    def test_attributes_include_workspace(self):
        exporter = OTLPDictExporter()
        span = Span(name="x", workspace="acme", tenant_id="t1")
        exporter.export([span])
        otlp = exporter.batches[0][0]
        attr_keys = [a["key"] for a in otlp["attributes"]]
        assert "aegis.workspace" in attr_keys
        assert "aegis.tenant_id" in attr_keys

    def test_events_exported(self):
        exporter = OTLPDictExporter()
        span = Span(name="x")
        span.add_event("token_count", count=42)
        exporter.export([span])
        events = exporter.batches[0][0]["events"]
        assert len(events) == 1
        assert events[0]["name"] == "token_count"

    def test_multiple_batches(self):
        exporter = OTLPDictExporter()
        exporter.export([Span(name="a")])
        exporter.export([Span(name="b"), Span(name="c")])
        assert len(exporter.batches) == 2
        assert len(exporter.batches[1]) == 2

    def test_parent_span_id(self):
        exporter = OTLPDictExporter()
        span = Span(name="child", parent_id="parent123")
        exporter.export([span])
        assert exporter.batches[0][0]["parentSpanId"] == "parent123"

    def test_no_parent(self):
        exporter = OTLPDictExporter()
        span = Span(name="root")
        exporter.export([span])
        assert exporter.batches[0][0]["parentSpanId"] == ""


class TestOTLPValue:
    def test_string(self):
        assert _otlp_value("hello") == {"stringValue": "hello"}

    def test_int(self):
        assert _otlp_value(42) == {"intValue": 42}

    def test_float(self):
        assert _otlp_value(3.14) == {"doubleValue": 3.14}

    def test_bool(self):
        assert _otlp_value(True) == {"boolValue": True}
        assert _otlp_value(False) == {"boolValue": False}

    def test_other_as_string(self):
        assert _otlp_value(None) == {"stringValue": "None"}
