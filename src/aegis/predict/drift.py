"""DriftPredictor — predicts metric drift 48h before critical threshold.

Uses linear regression + exponential smoothing on a sliding window.
Pure stdlib — no PyTorch/sklearn dependency.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class DriftSeverity(str, Enum):
    OK = "ok"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class DriftPrediction:
    """Result of a drift prediction."""

    metric: str
    current_value: float
    predicted_value: float
    confidence_interval: tuple[float, float]
    time_to_threshold_hours: float | None  # None = won't breach
    severity: DriftSeverity
    method: str
    message: str


@dataclass
class TimeSeriesPoint:
    """A timestamped metric value."""

    timestamp: float
    value: float


# ---------------------------------------------------------------------------
# Math helpers (stdlib only)
# ---------------------------------------------------------------------------

def _linear_regression(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Return (slope, intercept) for simple linear regression.

    Uses the least-squares formula:
        slope = (n * sum(xy) - sum(x) * sum(y)) / (n * sum(x^2) - sum(x)^2)
    """
    n = len(xs)
    if n < 2:
        return 0.0, (ys[0] if ys else 0.0)

    sx = sum(xs)
    sy = sum(ys)
    sxy = sum(x * y for x, y in zip(xs, ys))
    sx2 = sum(x * x for x in xs)

    denom = n * sx2 - sx * sx
    if abs(denom) < 1e-12:
        return 0.0, sy / n

    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return slope, intercept


def _residual_stderr(
    xs: list[float], ys: list[float], slope: float, intercept: float
) -> float:
    """Standard error of residuals."""
    n = len(xs)
    if n < 3:
        return 0.0
    residuals = [y - (slope * x + intercept) for x, y in zip(xs, ys)]
    ss_res = sum(r * r for r in residuals)
    return math.sqrt(ss_res / (n - 2))


def _exponential_smoothing(values: list[float], alpha: float = 0.3) -> list[float]:
    """Simple exponential smoothing. Returns smoothed series."""
    if not values:
        return []
    smoothed = [values[0]]
    for v in values[1:]:
        smoothed.append(alpha * v + (1 - alpha) * smoothed[-1])
    return smoothed


# ---------------------------------------------------------------------------
# DriftPredictor
# ---------------------------------------------------------------------------

class DriftPredictor:
    """Predicts metric drift using linear regression + exponential smoothing.

    Usage::

        pred = DriftPredictor(critical_threshold=0.85)
        pred.add_point("faithfulness", time.time(), 0.95)
        # ... add more points over time ...
        prediction = pred.predict("faithfulness", horizon_hours=48)
        if prediction.time_to_threshold_hours:
            print(f"Will breach in {prediction.time_to_threshold_hours:.0f}h")

    Parameters
    ----------
    critical_threshold : float
        The lower bound below which a metric is considered critical.
    min_points : int
        Minimum data points before prediction is attempted.
    smoothing_alpha : float
        Alpha for exponential smoothing (0-1, higher = more recent weight).
    """

    def __init__(
        self,
        *,
        critical_threshold: float = 0.85,
        min_points: int = 5,
        smoothing_alpha: float = 0.3,
    ) -> None:
        self._threshold = critical_threshold
        self._min_points = max(2, min_points)
        self._alpha = smoothing_alpha
        self._series: dict[str, list[TimeSeriesPoint]] = {}

    @property
    def threshold(self) -> float:
        return self._threshold

    @threshold.setter
    def threshold(self, value: float) -> None:
        self._threshold = value

    @property
    def min_points(self) -> int:
        return self._min_points

    def add_point(self, metric: str, timestamp: float, value: float) -> None:
        """Add a data point to the time series for a metric."""
        self._series.setdefault(metric, []).append(
            TimeSeriesPoint(timestamp=timestamp, value=value)
        )

    def add_points(self, metric: str, points: list[tuple[float, float]]) -> None:
        """Bulk-add (timestamp, value) pairs."""
        for ts, val in points:
            self.add_point(metric, ts, val)

    def series(self, metric: str) -> list[TimeSeriesPoint]:
        """Return the raw time series for a metric."""
        return list(self._series.get(metric, []))

    def clear(self, metric: str | None = None) -> None:
        """Clear series data."""
        if metric:
            self._series.pop(metric, None)
        else:
            self._series.clear()

    def predict(
        self,
        metric: str,
        *,
        horizon_hours: float = 48.0,
    ) -> DriftPrediction:
        """Predict the metric's future value and time-to-threshold.

        Uses ensemble of linear regression and exponential smoothing.
        """
        pts = self._series.get(metric, [])
        if len(pts) < self._min_points:
            return DriftPrediction(
                metric=metric,
                current_value=pts[-1].value if pts else 0.0,
                predicted_value=pts[-1].value if pts else 0.0,
                confidence_interval=(0.0, 0.0),
                time_to_threshold_hours=None,
                severity=DriftSeverity.OK,
                method="insufficient_data",
                message=f"Need {self._min_points} points, have {len(pts)}",
            )

        # Sort by timestamp
        pts = sorted(pts, key=lambda p: p.timestamp)

        # Convert to hours from first point
        t0 = pts[0].timestamp
        xs = [(p.timestamp - t0) / 3600.0 for p in pts]
        ys = [p.value for p in pts]

        # --- Linear regression ---
        slope, intercept = _linear_regression(xs, ys)
        stderr = _residual_stderr(xs, ys, slope, intercept)

        # --- Exponential smoothing forecast ---
        smoothed = _exponential_smoothing(ys, alpha=self._alpha)
        # Smoothed trend: difference of last two smoothed values
        if len(smoothed) >= 2:
            smooth_trend = smoothed[-1] - smoothed[-2]
            time_step = xs[-1] - xs[-2] if len(xs) >= 2 else 1.0
            if abs(time_step) > 1e-9:
                smooth_rate = smooth_trend / time_step
            else:
                smooth_rate = 0.0
        else:
            smooth_rate = 0.0

        # --- Ensemble: average of both methods ---
        current_t = xs[-1]
        target_t = current_t + horizon_hours

        lr_pred = slope * target_t + intercept
        es_pred = smoothed[-1] + smooth_rate * horizon_hours
        predicted = (lr_pred + es_pred) / 2.0

        # Confidence interval (based on linear regression stderr)
        ci_width = 1.96 * stderr * math.sqrt(1 + 1 / len(xs))
        ci = (predicted - ci_width, predicted + ci_width)

        # --- Time to threshold ---
        tth = self._time_to_threshold(
            current_value=ys[-1],
            current_t=current_t,
            slope=slope,
            smooth_rate=smooth_rate,
        )

        # --- Severity ---
        severity = self._assess_severity(ys[-1], predicted, tth)

        # --- Message ---
        if tth is not None and tth <= horizon_hours:
            msg = (
                f"{metric} predicted to breach {self._threshold:.2f} "
                f"in {tth:.0f}h (current: {ys[-1]:.3f} -> {predicted:.3f})"
            )
        else:
            msg = f"{metric}: {ys[-1]:.3f} -> {predicted:.3f} in {horizon_hours:.0f}h (stable)"

        return DriftPrediction(
            metric=metric,
            current_value=round(ys[-1], 4),
            predicted_value=round(predicted, 4),
            confidence_interval=(round(ci[0], 4), round(ci[1], 4)),
            time_to_threshold_hours=round(tth, 1) if tth is not None else None,
            severity=severity,
            method="ensemble_lr_es",
            message=msg,
        )

    def _time_to_threshold(
        self,
        current_value: float,
        current_t: float,
        slope: float,
        smooth_rate: float,
    ) -> float | None:
        """Estimate hours until value crosses the critical threshold.

        Uses the ensemble average rate. Returns None if trending away
        from threshold or rate is negligible.
        """
        avg_rate = (slope + smooth_rate) / 2.0

        # Metric drifting down toward threshold (lower is worse)
        if avg_rate >= 0:
            return None  # improving or flat

        if current_value <= self._threshold:
            return 0.0  # already breached

        distance = current_value - self._threshold
        hours = distance / abs(avg_rate)
        return hours

    def _assess_severity(
        self,
        current: float,
        predicted: float,
        tth: float | None,
    ) -> DriftSeverity:
        if current <= self._threshold:
            return DriftSeverity.CRITICAL
        if tth is not None:
            if tth <= 12:
                return DriftSeverity.CRITICAL
            elif tth <= 24:
                return DriftSeverity.HIGH
            elif tth <= 48:
                return DriftSeverity.MEDIUM
            else:
                return DriftSeverity.LOW
        return DriftSeverity.OK
