"""AnomalyDetector — detects abnormal agent behaviour using Z-score and IQR.

Applicable to latency, tokens, costs, error rates.
Pure stdlib — no external ML dependencies.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AnomalyDirection(str, Enum):
    SPIKE = "spike"
    DROP = "drop"
    NORMAL = "normal"


@dataclass(frozen=True)
class AnomalyResult:
    """Result of an anomaly check on a single value."""

    metric: str
    value: float
    is_anomaly: bool
    score: float          # anomaly score (Z-score or IQR ratio)
    direction: AnomalyDirection
    method: str
    context: dict[str, Any]


class AnomalyDetector:
    """Detects abnormal values in agent metrics using statistical methods.

    Usage::

        detector = AnomalyDetector(window_size=100)
        detector.add("latency", 150.0)
        detector.add("latency", 160.0)
        # ... add more values ...
        result = detector.check("latency", 950.0)
        if result.is_anomaly:
            print(f"Anomaly! {result.direction} (z={result.score:.1f})")

    Parameters
    ----------
    window_size : int
        Sliding window size for computing baselines.
    z_threshold : float
        Z-score threshold for anomaly detection.
    iqr_factor : float
        IQR multiplier for outlier fences (default 1.5 = standard).
    method : str
        Detection method: "zscore", "iqr", or "ensemble" (both).
    """

    def __init__(
        self,
        *,
        window_size: int = 100,
        z_threshold: float = 3.0,
        iqr_factor: float = 1.5,
        method: str = "ensemble",
    ) -> None:
        if method not in ("zscore", "iqr", "ensemble"):
            raise ValueError(f"method must be zscore, iqr, or ensemble, got {method!r}")
        self._window_size = window_size
        self._z_threshold = z_threshold
        self._iqr_factor = iqr_factor
        self._method = method
        self._data: dict[str, list[float]] = {}

    @property
    def window_size(self) -> int:
        return self._window_size

    @property
    def method(self) -> str:
        return self._method

    def add(self, metric: str, value: float) -> None:
        """Add a value to the sliding window for a metric."""
        window = self._data.setdefault(metric, [])
        window.append(value)
        # Trim to window size
        if len(window) > self._window_size:
            self._data[metric] = window[-self._window_size:]

    def add_batch(self, metric: str, values: list[float]) -> None:
        """Add multiple values at once."""
        for v in values:
            self.add(metric, v)

    def clear(self, metric: str | None = None) -> None:
        if metric:
            self._data.pop(metric, None)
        else:
            self._data.clear()

    def check(self, metric: str, value: float) -> AnomalyResult:
        """Check if a value is anomalous relative to the sliding window.

        The value is NOT automatically added to the window — call :meth:`add`
        separately if you want to include it in future baseline calculations.
        """
        window = self._data.get(metric, [])

        if len(window) < 3:
            return AnomalyResult(
                metric=metric,
                value=value,
                is_anomaly=False,
                score=0.0,
                direction=AnomalyDirection.NORMAL,
                method="insufficient_data",
                context={"window_size": len(window)},
            )

        if self._method == "zscore":
            return self._check_zscore(metric, value, window)
        elif self._method == "iqr":
            return self._check_iqr(metric, value, window)
        else:
            return self._check_ensemble(metric, value, window)

    def _check_zscore(
        self, metric: str, value: float, window: list[float]
    ) -> AnomalyResult:
        mean = statistics.mean(window)
        stdev = statistics.stdev(window)
        if stdev < 1e-12:
            return AnomalyResult(
                metric=metric, value=value, is_anomaly=False, score=0.0,
                direction=AnomalyDirection.NORMAL, method="zscore",
                context={"mean": mean, "stdev": 0.0},
            )

        z = (value - mean) / stdev
        is_anomaly = abs(z) >= self._z_threshold
        direction = (
            AnomalyDirection.SPIKE if z > 0
            else AnomalyDirection.DROP if z < 0
            else AnomalyDirection.NORMAL
        )

        return AnomalyResult(
            metric=metric,
            value=value,
            is_anomaly=is_anomaly,
            score=round(abs(z), 3),
            direction=direction if is_anomaly else AnomalyDirection.NORMAL,
            method="zscore",
            context={"mean": round(mean, 4), "stdev": round(stdev, 4), "z_score": round(z, 3)},
        )

    def _check_iqr(
        self, metric: str, value: float, window: list[float]
    ) -> AnomalyResult:
        sorted_w = sorted(window)
        n = len(sorted_w)

        q1 = sorted_w[n // 4]
        q3 = sorted_w[(3 * n) // 4]
        iqr = q3 - q1

        if iqr < 1e-12:
            return AnomalyResult(
                metric=metric, value=value, is_anomaly=False, score=0.0,
                direction=AnomalyDirection.NORMAL, method="iqr",
                context={"q1": q1, "q3": q3, "iqr": 0.0},
            )

        lower_fence = q1 - self._iqr_factor * iqr
        upper_fence = q3 + self._iqr_factor * iqr

        is_anomaly = value < lower_fence or value > upper_fence

        # Score: distance from nearest fence in IQR units
        if value > upper_fence:
            score = (value - upper_fence) / iqr
            direction = AnomalyDirection.SPIKE
        elif value < lower_fence:
            score = (lower_fence - value) / iqr
            direction = AnomalyDirection.DROP
        else:
            score = 0.0
            direction = AnomalyDirection.NORMAL

        return AnomalyResult(
            metric=metric,
            value=value,
            is_anomaly=is_anomaly,
            score=round(score, 3),
            direction=direction if is_anomaly else AnomalyDirection.NORMAL,
            method="iqr",
            context={
                "q1": round(q1, 4), "q3": round(q3, 4),
                "iqr": round(iqr, 4),
                "lower_fence": round(lower_fence, 4),
                "upper_fence": round(upper_fence, 4),
            },
        )

    def _check_ensemble(
        self, metric: str, value: float, window: list[float]
    ) -> AnomalyResult:
        """Ensemble: anomaly if either Z-score OR IQR flags it."""
        z_result = self._check_zscore(metric, value, window)
        iqr_result = self._check_iqr(metric, value, window)

        is_anomaly = z_result.is_anomaly or iqr_result.is_anomaly
        # Use the higher anomaly score
        if z_result.score >= iqr_result.score:
            primary = z_result
        else:
            primary = iqr_result

        return AnomalyResult(
            metric=metric,
            value=value,
            is_anomaly=is_anomaly,
            score=max(z_result.score, iqr_result.score),
            direction=primary.direction if is_anomaly else AnomalyDirection.NORMAL,
            method="ensemble",
            context={
                "zscore": z_result.context,
                "iqr": iqr_result.context,
                "zscore_anomaly": z_result.is_anomaly,
                "iqr_anomaly": iqr_result.is_anomaly,
            },
        )
