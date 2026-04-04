"""aegis.guard — Module Guard.

Framework de validation avec pipeline séquentiel, niveaux N1–N4,
détecteurs intégrés (PII, injection, hallucination) et gate HITL.
"""

from aegis.guard.pipeline import GuardPipeline, PipelineResult
from aegis.guard.validators import (
    BaseValidator,
    HallucinationDetector,
    InjectionDetector,
    PIIDetector,
)

__all__ = [
    "BaseValidator",
    "GuardPipeline",
    "HallucinationDetector",
    "InjectionDetector",
    "PIIDetector",
    "PipelineResult",
]
