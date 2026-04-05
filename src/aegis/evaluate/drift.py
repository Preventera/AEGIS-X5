"""DriftDetector — compare baseline vs current scores, raise alerts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AlertLevel(str, Enum):
    OK = "ok"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class DriftAlert:
    """Alert produced when a metric drifts beyond thresholds."""

    metric: str
    baseline: float
    current: float
    delta: float
    level: AlertLevel
    message: str = ""


class DriftDetector:
    """Compares metric scores against a stored baseline.

    Usage::

        detector = DriftDetector(warning_threshold=0.1, critical_threshold=0.25)
        detector.set_baseline({"faithfulness": 0.90, "relevancy": 0.85})
        alerts = detector.check({"faithfulness": 0.75, "relevancy": 0.83})
    """

    def __init__(
        self,
        *,
        warning_threshold: float = 0.1,
        critical_threshold: float = 0.25,
    ) -> None:
        if warning_threshold <= 0 or critical_threshold <= 0:
            raise ValueError("Thresholds must be positive")
        if critical_threshold <= warning_threshold:
            raise ValueError("critical_threshold must be greater than warning_threshold")
        self._warning = warning_threshold
        self._critical = critical_threshold
        self._baseline: dict[str, float] = {}

    @property
    def baseline(self) -> dict[str, float]:
        return dict(self._baseline)

    def set_baseline(self, scores: dict[str, float]) -> None:
        """Set the reference baseline scores."""
        self._baseline = dict(scores)

    def check(self, current: dict[str, float]) -> list[DriftAlert]:
        """Compare *current* scores against the baseline.

        Returns a list of :class:`DriftAlert` for each metric that has drifted.
        Metrics not in the baseline are silently skipped.
        """
        alerts: list[DriftAlert] = []
        for metric, baseline_score in self._baseline.items():
            current_score = current.get(metric)
            if current_score is None:
                continue
            delta = baseline_score - current_score  # positive = degradation
            if delta >= self._critical:
                level = AlertLevel.CRITICAL
            elif delta >= self._warning:
                level = AlertLevel.WARNING
            else:
                level = AlertLevel.OK

            if level != AlertLevel.OK:
                alerts.append(DriftAlert(
                    metric=metric,
                    baseline=baseline_score,
                    current=current_score,
                    delta=round(delta, 4),
                    level=level,
                    message=f"{metric}: {baseline_score:.2f} → {current_score:.2f} (Δ={delta:+.2f})",
                ))
        return alerts
