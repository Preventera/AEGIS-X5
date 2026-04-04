"""HealthScore — real-time 0-100 health score per agent.

Combines multiple signals (latency, error rate, cost, faithfulness,
guard blocks, drift, memory usage) into a single actionable score.

Uses only Python stdlib — no PyTorch/sklearn dependency.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HealthStatus(str, Enum):
    """Health classification based on score thresholds."""

    HEALTHY = "healthy"    # 80-100
    WARNING = "warning"    # 60-79
    CRITICAL = "critical"  # 0-59


# ---------------------------------------------------------------------------
# Default weights — each input contributes proportionally
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[str, float] = {
    "latency_p95": 0.15,
    "error_rate": 0.20,
    "cost_per_day": 0.10,
    "faithfulness": 0.20,
    "guard_blocks": 0.15,
    "drift": 0.10,
    "memory_usage": 0.10,
}

# ---------------------------------------------------------------------------
# Normaliser configs: (ideal, worst) — maps raw metric to 0-100 sub-score
# ---------------------------------------------------------------------------

DEFAULT_NORMALISERS: dict[str, tuple[float, float]] = {
    "latency_p95": (200.0, 10000.0),     # 200ms ideal, 10s worst
    "error_rate": (0.0, 0.5),             # 0% ideal, 50% worst
    "cost_per_day": (0.0, 100.0),         # $0 ideal, $100 worst
    "faithfulness": (1.0, 0.0),           # 1.0 ideal, 0.0 worst (inverted)
    "guard_blocks": (0.0, 50.0),          # 0 blocks ideal, 50 worst
    "drift": (0.0, 0.5),                  # 0 drift ideal, 0.5 worst
    "memory_usage": (0.0, 1.0),           # 0% ideal, 100% worst
}


# ---------------------------------------------------------------------------
# Score snapshot
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ScoreSnapshot:
    """A single health score computation at a point in time."""

    agent_id: str
    score: float
    status: HealthStatus
    components: dict[str, float]
    raw_inputs: dict[str, float]
    timestamp: float


# ---------------------------------------------------------------------------
# HealthScore calculator
# ---------------------------------------------------------------------------

class HealthScore:
    """Compute a 0-100 health score for an agent based on weighted metrics.

    Usage::

        hs = HealthScore()
        snap = hs.compute("agent-1", {
            "latency_p95": 350.0,
            "error_rate": 0.02,
            "faithfulness": 0.92,
        })
        print(snap.score, snap.status)  # 87.3, healthy

    Parameters
    ----------
    weights : dict | None
        Custom weights (must sum to ~1.0). Falls back to defaults.
    normalisers : dict | None
        Custom (ideal, worst) ranges per metric.
    """

    def __init__(
        self,
        *,
        weights: dict[str, float] | None = None,
        normalisers: dict[str, tuple[float, float]] | None = None,
    ) -> None:
        self._weights = dict(weights or DEFAULT_WEIGHTS)
        self._normalisers = dict(normalisers or DEFAULT_NORMALISERS)
        self._history: dict[str, list[ScoreSnapshot]] = {}

    @property
    def weights(self) -> dict[str, float]:
        return dict(self._weights)

    @property
    def normalisers(self) -> dict[str, tuple[float, float]]:
        return dict(self._normalisers)

    def compute(self, agent_id: str, metrics: dict[str, float]) -> ScoreSnapshot:
        """Compute health score from raw metrics.

        Missing metrics are ignored — the score is computed from available
        inputs only, re-normalising the weights proportionally.
        """
        components: dict[str, float] = {}
        total_weight = 0.0

        for key, weight in self._weights.items():
            if key not in metrics:
                continue
            raw = metrics[key]
            ideal, worst = self._normalisers.get(key, (0.0, 1.0))
            sub_score = self._normalise(raw, ideal, worst)
            components[key] = round(sub_score, 2)
            total_weight += weight

        # Weighted average (re-normalised for missing inputs)
        if total_weight > 0:
            score = sum(
                components[k] * self._weights[k] / total_weight
                for k in components
            )
        else:
            score = 100.0  # no data → assume healthy

        score = round(max(0.0, min(100.0, score)), 1)
        status = self._classify(score)

        snap = ScoreSnapshot(
            agent_id=agent_id,
            score=score,
            status=status,
            components=components,
            raw_inputs=dict(metrics),
            timestamp=time.time(),
        )

        # Store in history
        self._history.setdefault(agent_id, []).append(snap)
        return snap

    def history(self, agent_id: str) -> list[ScoreSnapshot]:
        """Return score history for an agent."""
        return list(self._history.get(agent_id, []))

    def trend(self, agent_id: str, last_n: int = 10) -> dict[str, Any]:
        """Analyse score trend for an agent.

        Returns direction (improving/stable/degrading) and average delta.
        """
        hist = self._history.get(agent_id, [])
        if len(hist) < 2:
            return {"direction": "stable", "avg_delta": 0.0, "points": len(hist)}

        recent = hist[-last_n:]
        deltas = [recent[i].score - recent[i - 1].score for i in range(1, len(recent))]
        avg_delta = sum(deltas) / len(deltas)

        if avg_delta > 1.0:
            direction = "improving"
        elif avg_delta < -1.0:
            direction = "degrading"
        else:
            direction = "stable"

        return {
            "direction": direction,
            "avg_delta": round(avg_delta, 2),
            "points": len(recent),
            "latest": recent[-1].score,
            "oldest": recent[0].score,
        }

    def clear_history(self, agent_id: str | None = None) -> None:
        """Clear score history for one or all agents."""
        if agent_id:
            self._history.pop(agent_id, None)
        else:
            self._history.clear()

    # -- internal helpers ---------------------------------------------------

    @staticmethod
    def _normalise(value: float, ideal: float, worst: float) -> float:
        """Map a raw value to a 0-100 sub-score given ideal and worst bounds."""
        if ideal == worst:
            return 100.0 if value == ideal else 0.0
        # Linear interpolation: ideal → 100, worst → 0
        ratio = (value - ideal) / (worst - ideal)
        return max(0.0, min(100.0, (1.0 - ratio) * 100.0))

    @staticmethod
    def _classify(score: float) -> HealthStatus:
        if score >= 80.0:
            return HealthStatus.HEALTHY
        elif score >= 60.0:
            return HealthStatus.WARNING
        return HealthStatus.CRITICAL
