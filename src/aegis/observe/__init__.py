"""aegis.observe — Module Observe.

Télémétrie temps réel, tracing distribué, extraction de tokens,
calcul de coûts et métriques de latence pour les agents autonomes.
"""

from aegis.observe.cost import CostCalculator, CostResult
from aegis.observe.exporter import OTLPDictExporter, SpanExporter
from aegis.observe.metrics import LatencyStats, SlidingWindowMetrics
from aegis.observe.tokens import TokenUsage, extract_tokens
from aegis.observe.tracer import Tracer

__all__ = [
    "CostCalculator",
    "CostResult",
    "LatencyStats",
    "OTLPDictExporter",
    "SlidingWindowMetrics",
    "SpanExporter",
    "TokenUsage",
    "Tracer",
    "extract_tokens",
]
