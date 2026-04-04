"""Tests for aegis.predict.engine — PredictionEngine orchestrator."""

from __future__ import annotations

import time

import pytest

from aegis.predict.engine import CalibrationRecord, PredictionEngine
from aegis.predict.health_score import HealthStatus


@pytest.fixture()
def engine() -> PredictionEngine:
    return PredictionEngine()


# ---------------------------------------------------------------------------
# Calibration tracking
# ---------------------------------------------------------------------------

class TestCalibration:
    def test_register_prediction(self, engine: PredictionEngine) -> None:
        pid = engine.register_prediction("faith", "a1", 0.88, horizon_hours=48)
        assert pid.startswith("pred-")
        assert len(engine.calibration_records) == 1

    def test_resolve_prediction(self, engine: PredictionEngine) -> None:
        pid = engine.register_prediction("faith", "a1", 0.88)
        rec = engine.resolve_prediction(pid, 0.87)
        assert rec is not None
        assert rec.is_resolved
        assert rec.actual_value == 0.87
        assert rec.error == pytest.approx(0.01, abs=1e-6)

    def test_resolve_nonexistent(self, engine: PredictionEngine) -> None:
        assert engine.resolve_prediction("nope", 0.5) is None

    def test_pending_predictions(self, engine: PredictionEngine) -> None:
        engine.register_prediction("f", "a1", 0.9)
        engine.register_prediction("f", "a2", 0.8)
        pid = engine.register_prediction("f", "a3", 0.7)
        engine.resolve_prediction(pid, 0.72)
        assert len(engine.pending_predictions()) == 2


# ---------------------------------------------------------------------------
# Accuracy computation
# ---------------------------------------------------------------------------

class TestAccuracy:
    def test_no_data(self, engine: PredictionEngine) -> None:
        acc = engine.accuracy()
        assert acc["count"] == 0
        assert acc["mae"] is None

    def test_perfect_predictions(self, engine: PredictionEngine) -> None:
        for i in range(5):
            pid = engine.register_prediction("f", "a1", 0.90)
            engine.resolve_prediction(pid, 0.90)
        acc = engine.accuracy()
        assert acc["count"] == 5
        assert acc["mae"] == 0.0
        assert acc["rmse"] == 0.0

    def test_imperfect_predictions(self, engine: PredictionEngine) -> None:
        errors = [0.01, 0.02, 0.03, 0.02, 0.01]
        for e in errors:
            pid = engine.register_prediction("f", "a1", 0.90)
            engine.resolve_prediction(pid, 0.90 + e)
        acc = engine.accuracy()
        assert acc["count"] == 5
        assert acc["mae"] > 0
        assert acc["rmse"] > 0

    def test_per_metric_breakdown(self, engine: PredictionEngine) -> None:
        for m in ["faith", "relev"]:
            pid = engine.register_prediction(m, "a1", 0.90)
            engine.resolve_prediction(pid, 0.88)
        acc = engine.accuracy()
        assert "faith" in acc["metrics"]
        assert "relev" in acc["metrics"]

    def test_filter_by_metric(self, engine: PredictionEngine) -> None:
        pid1 = engine.register_prediction("faith", "a1", 0.90)
        engine.resolve_prediction(pid1, 0.88)
        pid2 = engine.register_prediction("relev", "a1", 0.90)
        engine.resolve_prediction(pid2, 0.50)  # big error
        acc = engine.accuracy(metric="faith")
        assert acc["count"] == 1
        assert acc["mae"] == pytest.approx(0.02, abs=1e-4)


# ---------------------------------------------------------------------------
# CalibrationRecord
# ---------------------------------------------------------------------------

class TestCalibrationRecord:
    def test_error_before_resolve(self) -> None:
        rec = CalibrationRecord(
            prediction_id="p1", metric="f", agent_id="a1",
            predicted_value=0.9, predicted_at=time.time(), horizon_hours=48,
        )
        assert rec.error is None
        assert rec.is_resolved is False

    def test_error_after_resolve(self) -> None:
        rec = CalibrationRecord(
            prediction_id="p1", metric="f", agent_id="a1",
            predicted_value=0.9, predicted_at=time.time(), horizon_hours=48,
            actual_value=0.85,
        )
        assert rec.error == pytest.approx(0.05)
        assert rec.is_resolved is True


# ---------------------------------------------------------------------------
# Full report
# ---------------------------------------------------------------------------

class TestFullReport:
    def test_basic_report(self, engine: PredictionEngine) -> None:
        report = engine.full_report(
            "a1", metrics={"error_rate": 0.02, "latency_p95": 300}
        )
        assert report["agent_id"] == "a1"
        assert "health" in report
        assert report["health"]["score"] > 0

    def test_report_with_drift_data(self, engine: PredictionEngine) -> None:
        t0 = 1000.0
        for i in range(10):
            engine.drift_predictor.add_point("faithfulness", t0 + i * 3600, 0.95 - i * 0.005)
        report = engine.full_report("a1", metrics={"faithfulness": 0.90})
        assert "drift" in report
        assert report["drift"]["current"] == pytest.approx(0.905, abs=0.01)

    def test_report_with_cost_data(self, engine: PredictionEngine) -> None:
        day = 86400.0
        for i in range(5):
            engine.cost_forecaster.add_daily_cost("a1", 1000 + i * day, 15.0)
        report = engine.full_report("a1", metrics={"cost_per_day": 15.0})
        assert "cost" in report
        assert report["cost"]["weekly_total"] > 0

    def test_report_accuracy_section(self, engine: PredictionEngine) -> None:
        report = engine.full_report("a1", metrics={"error_rate": 0.01})
        assert "accuracy" in report


# ---------------------------------------------------------------------------
# Clear
# ---------------------------------------------------------------------------

class TestEngineClear:
    def test_clear_resets_all(self, engine: PredictionEngine) -> None:
        engine.register_prediction("f", "a1", 0.9)
        engine.health_score.compute("a1", {"error_rate": 0.01})
        engine.drift_predictor.add_point("f", 1000, 0.9)
        engine.anomaly_detector.add("lat", 100)

        engine.clear()

        assert engine.calibration_records == []
        assert engine.health_score.history("a1") == []
        assert engine.drift_predictor.series("f") == []


# ---------------------------------------------------------------------------
# Component access
# ---------------------------------------------------------------------------

class TestEngineComponents:
    def test_components_accessible(self, engine: PredictionEngine) -> None:
        assert engine.health_score is not None
        assert engine.drift_predictor is not None
        assert engine.cost_forecaster is not None
        assert engine.anomaly_detector is not None

    def test_custom_components(self) -> None:
        from aegis.predict.health_score import HealthScore
        from aegis.predict.drift import DriftPredictor

        hs = HealthScore(weights={"error_rate": 1.0})
        dp = DriftPredictor(critical_threshold=0.90)
        engine = PredictionEngine(health_score=hs, drift_predictor=dp)
        assert engine.health_score is hs
        assert engine.drift_predictor is dp
