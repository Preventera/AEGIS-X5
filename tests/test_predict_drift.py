"""Tests for aegis.predict.drift — DriftPredictor."""

from __future__ import annotations

import pytest

from aegis.predict.drift import (
    DriftPrediction,
    DriftPredictor,
    DriftSeverity,
    _exponential_smoothing,
    _linear_regression,
    _residual_stderr,
)

# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------

class TestLinearRegression:
    def test_perfect_line(self) -> None:
        slope, intercept = _linear_regression([0, 1, 2, 3], [0, 2, 4, 6])
        assert abs(slope - 2.0) < 1e-6
        assert abs(intercept) < 1e-6

    def test_flat_line(self) -> None:
        slope, intercept = _linear_regression([0, 1, 2], [5, 5, 5])
        assert abs(slope) < 1e-6
        assert abs(intercept - 5.0) < 1e-6

    def test_negative_slope(self) -> None:
        slope, _ = _linear_regression([0, 1, 2, 3], [10, 8, 6, 4])
        assert slope < 0

    def test_single_point(self) -> None:
        slope, intercept = _linear_regression([0], [5])
        assert slope == 0.0
        assert intercept == 5.0

    def test_two_points(self) -> None:
        slope, intercept = _linear_regression([0, 1], [0, 3])
        assert abs(slope - 3.0) < 1e-6
        assert abs(intercept) < 1e-6


class TestExponentialSmoothing:
    def test_constant_series(self) -> None:
        result = _exponential_smoothing([5, 5, 5, 5], alpha=0.3)
        assert all(abs(v - 5.0) < 1e-6 for v in result)

    def test_empty(self) -> None:
        assert _exponential_smoothing([]) == []

    def test_length_preserved(self) -> None:
        result = _exponential_smoothing([1, 2, 3, 4, 5])
        assert len(result) == 5

    def test_first_value_unchanged(self) -> None:
        result = _exponential_smoothing([10, 20, 30], alpha=0.5)
        assert result[0] == 10


class TestResidualStderr:
    def test_perfect_fit(self) -> None:
        xs = [0.0, 1.0, 2.0, 3.0]
        ys = [0.0, 2.0, 4.0, 6.0]
        assert _residual_stderr(xs, ys, 2.0, 0.0) == pytest.approx(0.0, abs=1e-6)

    def test_few_points(self) -> None:
        assert _residual_stderr([0, 1], [0, 1], 1.0, 0.0) == 0.0


# ---------------------------------------------------------------------------
# DriftPredictor
# ---------------------------------------------------------------------------

@pytest.fixture()
def predictor() -> DriftPredictor:
    return DriftPredictor(critical_threshold=0.85, min_points=5)


class TestDriftPredictorBasic:
    def test_insufficient_data(self, predictor: DriftPredictor) -> None:
        predictor.add_point("f", 1000, 0.95)
        pred = predictor.predict("f")
        assert pred.method == "insufficient_data"
        assert pred.severity == DriftSeverity.OK

    def test_stable_metric(self, predictor: DriftPredictor) -> None:
        t0 = 1000.0
        for i in range(10):
            predictor.add_point("f", t0 + i * 3600, 0.95)
        pred = predictor.predict("f", horizon_hours=48)
        assert pred.severity == DriftSeverity.OK
        assert pred.time_to_threshold_hours is None

    def test_degrading_metric(self, predictor: DriftPredictor) -> None:
        t0 = 1000.0
        values = [0.95, 0.94, 0.93, 0.92, 0.91, 0.90, 0.89, 0.88]
        for i, v in enumerate(values):
            predictor.add_point("f", t0 + i * 3600, v)
        pred = predictor.predict("f", horizon_hours=48)
        assert pred.predicted_value < pred.current_value
        assert pred.time_to_threshold_hours is not None

    def test_improving_metric(self, predictor: DriftPredictor) -> None:
        t0 = 1000.0
        values = [0.80, 0.82, 0.84, 0.86, 0.88, 0.90]
        for i, v in enumerate(values):
            predictor.add_point("f", t0 + i * 3600, v)
        pred = predictor.predict("f", horizon_hours=48)
        assert pred.time_to_threshold_hours is None  # improving, won't breach

    def test_already_below_threshold(self, predictor: DriftPredictor) -> None:
        t0 = 1000.0
        values = [0.82, 0.81, 0.80, 0.79, 0.78]
        for i, v in enumerate(values):
            predictor.add_point("f", t0 + i * 3600, v)
        pred = predictor.predict("f", horizon_hours=48)
        # Current value (0.78) is below threshold (0.85)
        assert pred.severity == DriftSeverity.CRITICAL

    def test_nonexistent_metric(self, predictor: DriftPredictor) -> None:
        pred = predictor.predict("nonexistent")
        assert pred.method == "insufficient_data"


class TestDriftPredictorProperties:
    def test_threshold_property(self, predictor: DriftPredictor) -> None:
        assert predictor.threshold == 0.85
        predictor.threshold = 0.90
        assert predictor.threshold == 0.90

    def test_min_points(self, predictor: DriftPredictor) -> None:
        assert predictor.min_points == 5

    def test_series_access(self, predictor: DriftPredictor) -> None:
        predictor.add_point("f", 1000, 0.9)
        assert len(predictor.series("f")) == 1

    def test_add_points_bulk(self, predictor: DriftPredictor) -> None:
        predictor.add_points("f", [(1000, 0.9), (2000, 0.8)])
        assert len(predictor.series("f")) == 2


class TestDriftPredictorClear:
    def test_clear_metric(self, predictor: DriftPredictor) -> None:
        predictor.add_point("f", 1000, 0.9)
        predictor.clear("f")
        assert predictor.series("f") == []

    def test_clear_all(self, predictor: DriftPredictor) -> None:
        predictor.add_point("f", 1000, 0.9)
        predictor.add_point("g", 1000, 0.8)
        predictor.clear()
        assert predictor.series("f") == []
        assert predictor.series("g") == []


class TestDriftSeverity:
    def test_values(self) -> None:
        assert DriftSeverity.OK.value == "ok"
        assert DriftSeverity.CRITICAL.value == "critical"
        assert DriftSeverity.HIGH.value == "high"
        assert DriftSeverity.MEDIUM.value == "medium"
        assert DriftSeverity.LOW.value == "low"


class TestDriftPrediction:
    def test_prediction_fields(self, predictor: DriftPredictor) -> None:
        t0 = 1000.0
        for i in range(6):
            predictor.add_point("f", t0 + i * 3600, 0.95 - i * 0.01)
        pred = predictor.predict("f", horizon_hours=48)
        assert isinstance(pred, DriftPrediction)
        assert pred.metric == "f"
        assert isinstance(pred.confidence_interval, tuple)
        assert len(pred.confidence_interval) == 2
        assert pred.method == "ensemble_lr_es"
        assert len(pred.message) > 0
