"""aegis.evaluate — Module Evaluate.

Évaluation continue de la qualité, détection de drift, métriques
plug-in et rapports structurés (JSON/Markdown).
"""

from aegis.evaluate.drift import AlertLevel, DriftAlert, DriftDetector
from aegis.evaluate.metrics import (
    ContextPrecision,
    EvalMetric,
    FaithfulnessMetric,
    MetricResult,
    RelevancyMetric,
)
from aegis.evaluate.runner import CaseResult, EvalReport, EvalRunner, TestCase

__all__ = [
    "AlertLevel",
    "CaseResult",
    "ContextPrecision",
    "DriftAlert",
    "DriftDetector",
    "EvalMetric",
    "EvalReport",
    "EvalRunner",
    "FaithfulnessMetric",
    "MetricResult",
    "RelevancyMetric",
    "TestCase",
]
