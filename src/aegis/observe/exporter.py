"""Export — OpenTelemetry-compatible span serialisation.

Provides an abstract SpanExporter interface and a built-in
OTLPDictExporter that converts AEGIS spans to the OTLP JSON structure
without requiring the opentelemetry-sdk dependency.
"""

from __future__ import annotations

import abc
from typing import Any

from aegis.core.trace import Span


class SpanExporter(abc.ABC):
    """Abstract exporter — implement :meth:`export` to ship spans anywhere."""

    @abc.abstractmethod
    def export(self, spans: list[Span]) -> None:
        ...

    def shutdown(self) -> None:
        """Clean up resources (optional override)."""


class OTLPDictExporter(SpanExporter):
    """Converts AEGIS spans to OTLP-compatible dicts (no SDK dependency).

    Collected spans are accessible via :attr:`batches` for testing /
    forwarding to any OTLP-compatible backend.
    """

    def __init__(self) -> None:
        self.batches: list[list[dict[str, Any]]] = []

    def export(self, spans: list[Span]) -> None:
        self.batches.append([_span_to_otlp(s) for s in spans])


def _span_to_otlp(span: Span) -> dict[str, Any]:
    """Map an AEGIS Span to an OTLP-style resource span dict."""
    return {
        "traceId": span.span_id,
        "spanId": span.span_id,
        "parentSpanId": span.parent_id or "",
        "name": span.name,
        "kind": "SPAN_KIND_INTERNAL",
        "startTimeUnixNano": int(span.start_time * 1e9) if span.start_time else 0,
        "endTimeUnixNano": int(span.end_time * 1e9) if span.end_time else 0,
        "status": {
            "code": "STATUS_CODE_OK" if span.status.value == "ok" else "STATUS_CODE_ERROR",
            "message": span.error or "",
        },
        "attributes": [
            {"key": k, "value": _otlp_value(v)} for k, v in span.attributes.items()
        ] + [
            {"key": "aegis.workspace", "value": {"stringValue": span.workspace}},
            {"key": "aegis.tenant_id", "value": {"stringValue": span.tenant_id}},
        ],
        "events": [
            {
                "name": evt.get("name", ""),
                "timeUnixNano": int(evt.get("time", 0) * 1e9),
                "attributes": [
                    {"key": k, "value": _otlp_value(v)}
                    for k, v in evt.items()
                    if k not in ("name", "time")
                ],
            }
            for evt in span.events
        ],
    }


def _otlp_value(value: Any) -> dict[str, Any]:
    """Wrap a Python value in OTLP attribute value format."""
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int):
        return {"intValue": value}
    if isinstance(value, float):
        return {"doubleValue": value}
    return {"stringValue": str(value)}
