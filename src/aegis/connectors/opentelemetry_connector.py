"""OpenTelemetry connector — export AEGIS spans as OTEL-compatible spans.

Provides an interface-only exporter (no opentelemetry dependency required).
Compatible with Jaeger, Zipkin, Datadog when opentelemetry-sdk is installed.

Usage::

    from aegis.connectors.opentelemetry_connector import AegisSpanExporter

    exporter = AegisSpanExporter(aegis)
    # Use with OTEL BatchSpanProcessor or standalone
    exporter.export_span(aegis_span)

    # Convert AEGIS spans to OTEL-compatible dict format
    otel_data = exporter.to_otel_format(aegis_span)
"""

from __future__ import annotations

import time
from typing import Any

from aegis.core.trace import Span, SpanStatus


class AegisSpanExporter:
    """Exports AEGIS spans in OpenTelemetry-compatible format.

    Does NOT require the opentelemetry-sdk package. Instead, it produces
    a standardized dict format that can be:
    - Sent to any OTLP collector via HTTP
    - Consumed by the OTEL SDK's BatchSpanProcessor if available
    - Logged to JSON for offline analysis

    Parameters
    ----------
    aegis : Aegis
        The AEGIS client instance.
    service_name : str
        Service name for OTEL resource attribution.
    endpoint : str | None
        OTLP collector endpoint (for future HTTP export).
    """

    def __init__(
        self,
        aegis: Any,
        *,
        service_name: str = "aegis-x5",
        endpoint: str | None = None,
    ) -> None:
        self._aegis = aegis
        self._service_name = service_name
        self._endpoint = endpoint
        self._exported: list[dict[str, Any]] = []

    @property
    def exported(self) -> list[dict[str, Any]]:
        """All exported spans in OTEL format."""
        return list(self._exported)

    @property
    def service_name(self) -> str:
        return self._service_name

    def to_otel_format(self, span: Span) -> dict[str, Any]:
        """Convert an AEGIS Span to OpenTelemetry-compatible dict.

        Returns a dict following the OTLP JSON encoding specification:
        https://opentelemetry.io/docs/specs/otlp/#json-protobuf-encoding
        """
        status_code = 1 if span.status == SpanStatus.OK else 2  # OK=1, ERROR=2

        otel_span: dict[str, Any] = {
            "traceId": span.span_id.ljust(32, "0"),
            "spanId": span.span_id[:16],
            "parentSpanId": span.parent_id[:16] if span.parent_id else "",
            "name": span.name,
            "kind": 1,  # INTERNAL
            "startTimeUnixNano": int(span.start_time * 1e9) if span.start_time else 0,
            "endTimeUnixNano": int(span.end_time * 1e9) if span.end_time else 0,
            "status": {
                "code": status_code,
                "message": span.error or "",
            },
            "attributes": [
                {"key": k, "value": {"stringValue": str(v)}}
                for k, v in span.attributes.items()
            ],
            "resource": {
                "attributes": [
                    {"key": "service.name", "value": {"stringValue": self._service_name}},
                    {"key": "workspace", "value": {"stringValue": span.workspace}},
                    {"key": "tenant.id", "value": {"stringValue": span.tenant_id}},
                ],
            },
        }

        # Add events
        if span.events:
            otel_span["events"] = [
                {
                    "name": e.get("name", "event"),
                    "timeUnixNano": int(e.get("time", 0) * 1e9),
                    "attributes": [
                        {"key": k, "value": {"stringValue": str(v)}}
                        for k, v in e.items()
                        if k not in ("name", "time")
                    ],
                }
                for e in span.events
            ]

        return otel_span

    def export_span(self, span: Span) -> dict[str, Any]:
        """Convert and store an AEGIS span for export."""
        otel = self.to_otel_format(span)
        self._exported.append(otel)
        return otel

    def export_batch(self, spans: list[Span]) -> list[dict[str, Any]]:
        """Export a batch of spans."""
        return [self.export_span(s) for s in spans]

    def flush(self) -> list[dict[str, Any]]:
        """Return all exported spans and clear the buffer."""
        result = list(self._exported)
        self._exported.clear()
        return result

    def shutdown(self) -> None:
        """Clean up resources."""
        self._exported.clear()
