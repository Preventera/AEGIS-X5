"""aegis.loops — Boucles fermées autonomes.

Auto-correct, auto-retrain et auto-scale : boucles de contrôle
qui permettent au système de se gouverner de manière autonome.
"""

from aegis.loops.base import ClosedLoop, LoopResult, LoopStatus
from aegis.loops.drift_correct import DriftAutoCorrect
from aegis.loops.guard_tune import GuardAutoTune
from aegis.loops.latency_scale import LatencyAutoScale
from aegis.loops.orchestrator import AutonomyLevel, LoopOrchestrator

__all__ = [
    "AutonomyLevel",
    "ClosedLoop",
    "DriftAutoCorrect",
    "GuardAutoTune",
    "LatencyAutoScale",
    "LoopOrchestrator",
    "LoopResult",
    "LoopStatus",
]
