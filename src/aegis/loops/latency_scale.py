"""LatencyAutoScale — closed loop that detects high latency and applies throttle/fallback."""

from __future__ import annotations

import time
from typing import Any, Callable

from aegis.observe.metrics import SlidingWindowMetrics
from aegis.loops.base import ClosedLoop, LoopResult
from aegis.remember.provenance import ActivityType, ProvenanceTracker


class LatencyAutoScale(ClosedLoop):
    """Detects p95 latency above threshold and applies fallback strategies.

    Parameters
    ----------
    metrics : SlidingWindowMetrics
        The latency metrics source.
    p95_threshold_ms : float
        Threshold above which a correction is triggered.
    fallback_fn : callable
        ``(diagnosis) -> dict`` — applies throttle or model fallback.
        Returns metadata about the action taken.
    tracker : ProvenanceTracker | None
        Audit trail.
    cooldown_seconds : float
        Minimum time between corrections to avoid flapping.
    """

    def __init__(
        self,
        *,
        metrics: SlidingWindowMetrics,
        p95_threshold_ms: float = 5000.0,
        fallback_fn: Callable[..., dict[str, Any]],
        tracker: ProvenanceTracker | None = None,
        cooldown_seconds: float = 60.0,
    ) -> None:
        super().__init__(name="latency-auto-scale")
        self._metrics = metrics
        self._threshold = p95_threshold_ms
        self._fallback_fn = fallback_fn
        self._tracker = tracker or ProvenanceTracker()
        self._cooldown = cooldown_seconds
        self._last_correction: float = 0.0
        # Load pattern tracking
        self._load_patterns: list[dict[str, Any]] = []

    @property
    def tracker(self) -> ProvenanceTracker:
        return self._tracker

    @property
    def threshold(self) -> float:
        return self._threshold

    @property
    def load_patterns(self) -> list[dict[str, Any]]:
        return list(self._load_patterns)

    def detect(self, **context: Any) -> dict[str, Any] | None:
        now = context.get("now", time.time())
        # Cooldown check
        if (now - self._last_correction) < self._cooldown:
            return None

        stats = self._metrics.stats()
        if stats.count == 0:
            return None

        if stats.p95 > self._threshold:
            return {
                "p95": stats.p95,
                "p99": stats.p99,
                "mean": stats.mean,
                "count": stats.count,
                "threshold": self._threshold,
            }
        return None

    def correct(self, diagnosis: dict[str, Any], **context: Any) -> dict[str, Any]:
        result = self._fallback_fn(diagnosis)
        self._last_correction = time.time()
        self._tracker.record(
            ActivityType.UPDATE,
            f"loop:{self.name}",
            action="fallback",
            p95=diagnosis["p95"],
            threshold=diagnosis["threshold"],
        )
        return result

    def validate(self, correction: dict[str, Any], **context: Any) -> bool:
        stats = self._metrics.stats()
        return stats.count == 0 or stats.p95 <= self._threshold

    def learn(self, result: LoopResult, **context: Any) -> dict[str, Any]:
        pattern = {
            "timestamp": time.time(),
            "p95_before": result.detected.get("p95", 0),
            "correction": result.correction,
            "validated": result.validated,
        }
        self._load_patterns.append(pattern)

        if result.validated:
            self._tracker.record(
                ActivityType.UPDATE,
                f"loop:{self.name}",
                action="scale_validated",
                p95_before=result.detected.get("p95", 0),
            )
        return pattern
