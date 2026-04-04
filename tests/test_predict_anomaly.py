"""Tests for aegis.predict.anomaly — AnomalyDetector."""

from __future__ import annotations

import pytest

from aegis.predict.anomaly import AnomalyDetector, AnomalyDirection, AnomalyResult


@pytest.fixture()
def detector() -> AnomalyDetector:
    return AnomalyDetector(window_size=100, z_threshold=3.0, iqr_factor=1.5)


def _seed(detector: AnomalyDetector, metric: str, values: list[float]) -> None:
    detector.add_batch(metric, values)


# ---------------------------------------------------------------------------
# Basic anomaly detection
# ---------------------------------------------------------------------------

class TestAnomalyDetectorBasic:
    def test_insufficient_data(self, detector: AnomalyDetector) -> None:
        detector.add("lat", 100)
        result = detector.check("lat", 200)
        assert result.is_anomaly is False
        assert result.method == "insufficient_data"

    def test_normal_value(self, detector: AnomalyDetector) -> None:
        _seed(detector, "lat", [100, 102, 98, 101, 99, 103, 97, 100, 101, 99])
        result = detector.check("lat", 102)
        assert result.is_anomaly is False
        assert result.direction == AnomalyDirection.NORMAL

    def test_spike_detected(self, detector: AnomalyDetector) -> None:
        _seed(detector, "lat", [100, 102, 98, 101, 99, 103, 97, 100, 102, 98] * 5)
        result = detector.check("lat", 500)
        assert result.is_anomaly is True
        assert result.direction == AnomalyDirection.SPIKE

    def test_drop_detected(self, detector: AnomalyDetector) -> None:
        _seed(detector, "lat", [100, 102, 98, 101, 99, 103, 97, 100, 102, 98] * 5)
        result = detector.check("lat", -300)
        assert result.is_anomaly is True
        assert result.direction == AnomalyDirection.DROP

    def test_result_fields(self, detector: AnomalyDetector) -> None:
        _seed(detector, "lat", [100] * 20)
        result = detector.check("lat", 100)
        assert isinstance(result, AnomalyResult)
        assert result.metric == "lat"
        assert result.value == 100
        assert isinstance(result.score, float)
        assert isinstance(result.context, dict)


# ---------------------------------------------------------------------------
# Z-score method
# ---------------------------------------------------------------------------

class TestZScoreMethod:
    def test_zscore_only(self) -> None:
        d = AnomalyDetector(method="zscore", z_threshold=2.0)
        _seed(d, "m", [10, 11, 9, 10, 12, 8, 10, 11, 9, 10])
        result = d.check("m", 30)
        assert result.method == "zscore"
        assert result.is_anomaly is True

    def test_zscore_context(self) -> None:
        d = AnomalyDetector(method="zscore")
        _seed(d, "m", [10, 11, 9, 10, 12])
        result = d.check("m", 10)
        assert "mean" in result.context
        assert "stdev" in result.context
        assert "z_score" in result.context

    def test_zero_variance(self) -> None:
        d = AnomalyDetector(method="zscore")
        _seed(d, "m", [5, 5, 5, 5, 5])
        result = d.check("m", 5)
        assert result.is_anomaly is False


# ---------------------------------------------------------------------------
# IQR method
# ---------------------------------------------------------------------------

class TestIQRMethod:
    def test_iqr_only(self) -> None:
        d = AnomalyDetector(method="iqr", iqr_factor=1.5)
        _seed(d, "m", list(range(1, 21)))  # 1..20
        result = d.check("m", 100)
        assert result.method == "iqr"
        assert result.is_anomaly is True

    def test_iqr_context(self) -> None:
        d = AnomalyDetector(method="iqr")
        _seed(d, "m", list(range(1, 21)))
        result = d.check("m", 10)
        assert "q1" in result.context
        assert "q3" in result.context
        assert "iqr" in result.context

    def test_iqr_zero_spread(self) -> None:
        d = AnomalyDetector(method="iqr")
        _seed(d, "m", [5, 5, 5, 5, 5])
        result = d.check("m", 5)
        assert result.is_anomaly is False


# ---------------------------------------------------------------------------
# Ensemble method
# ---------------------------------------------------------------------------

class TestEnsembleMethod:
    def test_ensemble_default(self, detector: AnomalyDetector) -> None:
        assert detector.method == "ensemble"

    def test_ensemble_combines(self, detector: AnomalyDetector) -> None:
        _seed(detector, "m", [10, 11, 9, 10, 12, 8, 10, 11, 9, 10] * 5)
        result = detector.check("m", 500)
        assert result.method == "ensemble"
        assert result.is_anomaly is True
        assert "zscore" in result.context
        assert "iqr" in result.context


# ---------------------------------------------------------------------------
# Window management
# ---------------------------------------------------------------------------

class TestWindowManagement:
    def test_window_size_limit(self) -> None:
        d = AnomalyDetector(window_size=5)
        _seed(d, "m", [1, 2, 3, 4, 5, 6, 7, 8])
        # Window should only have last 5
        result = d.check("m", 6)
        assert result.method != "insufficient_data"

    def test_add_does_not_check(self, detector: AnomalyDetector) -> None:
        """add() just stores — check() is separate."""
        detector.add("m", 1000000)  # extreme value
        # No assertion — just verify it doesn't blow up

    def test_clear_metric(self, detector: AnomalyDetector) -> None:
        _seed(detector, "m", [1, 2, 3])
        detector.clear("m")
        result = detector.check("m", 5)
        assert result.method == "insufficient_data"

    def test_clear_all(self, detector: AnomalyDetector) -> None:
        _seed(detector, "m1", [1, 2, 3])
        _seed(detector, "m2", [4, 5, 6])
        detector.clear()
        assert detector.check("m1", 1).method == "insufficient_data"
        assert detector.check("m2", 1).method == "insufficient_data"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_invalid_method(self) -> None:
        with pytest.raises(ValueError, match="method must be"):
            AnomalyDetector(method="invalid")

    def test_properties(self, detector: AnomalyDetector) -> None:
        assert detector.window_size == 100
        assert detector.method == "ensemble"
