"""DriftAutoCorrect — closed loop that detects and corrects metric drift."""

from __future__ import annotations

from typing import Any, Callable

from aegis.evaluate.drift import AlertLevel, DriftDetector
from aegis.loops.base import ClosedLoop, LoopResult
from aegis.remember.provenance import ActivityType, ProvenanceTracker


class DriftAutoCorrect(ClosedLoop):
    """Detects faithfulness/quality drift and triggers retraining.

    Parameters
    ----------
    detector : DriftDetector
        Pre-configured drift detector with baseline scores.
    retrain_fn : callable
        ``(diagnosis) -> dict`` — triggers a RAG retraining pipeline.
        Returns metadata about what was retrained.
    score_fn : callable
        ``() -> dict[str, float]`` — returns current metric scores
        (called after correction to validate improvement).
    tracker : ProvenanceTracker | None
        Audit trail for corrections.
    target_metric : str
        Which metric to monitor (default ``"faithfulness"``).
    """

    def __init__(
        self,
        *,
        detector: DriftDetector,
        retrain_fn: Callable[..., dict[str, Any]],
        score_fn: Callable[[], dict[str, float]],
        tracker: ProvenanceTracker | None = None,
        target_metric: str = "faithfulness",
    ) -> None:
        super().__init__(name="drift-auto-correct")
        self._detector = detector
        self._retrain_fn = retrain_fn
        self._score_fn = score_fn
        self._tracker = tracker or ProvenanceTracker()
        self._target = target_metric

    @property
    def tracker(self) -> ProvenanceTracker:
        return self._tracker

    @property
    def detector(self) -> DriftDetector:
        return self._detector

    def detect(self, **context: Any) -> dict[str, Any] | None:
        scores = context.get("scores") or self._score_fn()
        alerts = self._detector.check(scores)
        # Filter for target metric
        relevant = [a for a in alerts if a.metric == self._target]
        if not relevant:
            return None
        alert = relevant[0]
        return {
            "metric": alert.metric,
            "baseline": alert.baseline,
            "current": alert.current,
            "delta": alert.delta,
            "level": alert.level.value,
        }

    def correct(self, diagnosis: dict[str, Any], **context: Any) -> dict[str, Any]:
        result = self._retrain_fn(diagnosis)
        self._tracker.record(
            ActivityType.UPDATE,
            f"loop:{self.name}",
            action="retrain",
            metric=diagnosis["metric"],
            delta=diagnosis["delta"],
        )
        return result

    def validate(self, correction: dict[str, Any], **context: Any) -> bool:
        new_scores = self._score_fn()
        new_alerts = self._detector.check(new_scores)
        # Passes if no more alerts for our target metric
        return not any(a.metric == self._target for a in new_alerts)

    def learn(self, result: LoopResult, **context: Any) -> dict[str, Any]:
        if result.validated:
            # Update baseline to new (improved) scores
            new_scores = self._score_fn()
            target_score = new_scores.get(self._target)
            if target_score is not None:
                baseline = self._detector.baseline
                baseline[self._target] = target_score
                self._detector.set_baseline(baseline)
            self._tracker.record(
                ActivityType.UPDATE,
                f"loop:{self.name}",
                action="baseline_updated",
                new_baseline=target_score,
            )
            return {"baseline_updated": True, "new_score": target_score}
        return {"baseline_updated": False}
