"""Tests for aegis.predict.integration — predictive loop integration."""

from __future__ import annotations

import pytest

from aegis.predict.anomaly import AnomalyDetector
from aegis.predict.drift import DriftPredictor
from aegis.predict.health_score import HealthScore
from aegis.predict.integration import (
    AlertType,
    PredictiveAlert,
    PredictiveLoopIntegration,
)


@pytest.fixture()
def integration() -> PredictiveLoopIntegration:
    return PredictiveLoopIntegration()


# ---------------------------------------------------------------------------
# Drift-triggered alerts
# ---------------------------------------------------------------------------

class TestDriftAlerts:
    def test_drift_alert_generated(self) -> None:
        dp = DriftPredictor(critical_threshold=0.85, min_points=5)
        t0 = 1000.0
        # Degrading quickly
        for i in range(8):
            dp.add_point("faithfulness", t0 + i * 3600, 0.95 - i * 0.015)

        integ = PredictiveLoopIntegration(drift_predictor=dp)
        alerts = integ.evaluate("a1", {"faithfulness": 0.83})
        drift_alerts = [a for a in alerts if a.alert_type == AlertType.DRIFT_PREDICTED]
        assert len(drift_alerts) >= 1

    def test_no_drift_alert_when_stable(self, integration: PredictiveLoopIntegration) -> None:
        dp = integration._drift
        t0 = 1000.0
        for i in range(10):
            dp.add_point("faithfulness", t0 + i * 3600, 0.95)
        alerts = integration.evaluate("a1", {"faithfulness": 0.95})
        drift_alerts = [a for a in alerts if a.alert_type == AlertType.DRIFT_PREDICTED]
        assert len(drift_alerts) == 0


# ---------------------------------------------------------------------------
# Cost spike alerts
# ---------------------------------------------------------------------------

class TestCostSpikeAlerts:
    def test_cost_spike_alert(self) -> None:
        ad = AnomalyDetector(z_threshold=2.0)
        ad.add_batch("cost", [10, 11, 9, 10, 12, 8, 10, 11, 9, 10])
        integ = PredictiveLoopIntegration(anomaly_detector=ad)
        alerts = integ.evaluate("a1", {"cost_per_day": 100.0})
        cost_alerts = [a for a in alerts if a.alert_type == AlertType.COST_SPIKE]
        assert len(cost_alerts) == 1
        assert cost_alerts[0].severity in ("medium", "high")

    def test_no_cost_alert_normal(self) -> None:
        ad = AnomalyDetector()
        ad.add_batch("cost", [10, 11, 9, 10, 12, 11, 10])
        integ = PredictiveLoopIntegration(anomaly_detector=ad)
        alerts = integ.evaluate("a1", {"cost_per_day": 10.5})
        cost_alerts = [a for a in alerts if a.alert_type == AlertType.COST_SPIKE]
        assert len(cost_alerts) == 0


# ---------------------------------------------------------------------------
# Health alerts
# ---------------------------------------------------------------------------

class TestHealthAlerts:
    def test_critical_health_alert(self, integration: PredictiveLoopIntegration) -> None:
        alerts = integration.evaluate("a1", {
            "latency_p95": 9000,
            "error_rate": 0.45,
            "faithfulness": 0.1,
            "guard_blocks": 40,
        })
        health_alerts = [a for a in alerts if a.alert_type == AlertType.HEALTH_CRITICAL]
        assert len(health_alerts) == 1

    def test_warning_health_alert(self, integration: PredictiveLoopIntegration) -> None:
        alerts = integration.evaluate("a1", {
            "latency_p95": 4000,
            "error_rate": 0.12,
            "faithfulness": 0.65,
        })
        health_alerts = [
            a for a in alerts
            if a.alert_type in (AlertType.HEALTH_WARNING, AlertType.HEALTH_CRITICAL)
        ]
        assert len(health_alerts) >= 1

    def test_healthy_no_alert(self, integration: PredictiveLoopIntegration) -> None:
        alerts = integration.evaluate("a1", {
            "latency_p95": 200,
            "error_rate": 0.01,
            "faithfulness": 0.98,
        })
        health_alerts = [
            a for a in alerts
            if a.alert_type in (AlertType.HEALTH_WARNING, AlertType.HEALTH_CRITICAL)
        ]
        assert len(health_alerts) == 0


# ---------------------------------------------------------------------------
# Latency spike alerts
# ---------------------------------------------------------------------------

class TestLatencySpikeAlerts:
    def test_latency_spike(self) -> None:
        ad = AnomalyDetector(z_threshold=2.0)
        ad.add_batch("latency", [100, 102, 98, 101, 99, 103, 97, 100])
        integ = PredictiveLoopIntegration(anomaly_detector=ad)
        alerts = integ.evaluate("a1", {"latency_p95": 1000})
        lat_alerts = [a for a in alerts if a.alert_type == AlertType.LATENCY_SPIKE]
        assert len(lat_alerts) == 1


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

class TestCallbacks:
    def test_alert_callback(self, integration: PredictiveLoopIntegration) -> None:
        received: list[PredictiveAlert] = []
        integration.on_alert(lambda a: received.append(a))

        # Force a critical health alert
        integration.evaluate("a1", {
            "latency_p95": 9000, "error_rate": 0.45,
            "faithfulness": 0.1, "guard_blocks": 45,
        })
        assert len(received) >= 1

    def test_drift_action_callback(self) -> None:
        dp = DriftPredictor(critical_threshold=0.85, min_points=5)
        for i in range(8):
            dp.add_point("faithfulness", 1000 + i * 3600, 0.95 - i * 0.015)

        action_calls: list = []
        integ = PredictiveLoopIntegration(drift_predictor=dp)
        integ.on_drift_action(lambda a: action_calls.append(a.alert_type) or {"retrained": True})

        integ.evaluate("a1", {"faithfulness": 0.83})
        assert len(action_calls) >= 1

    def test_health_action_callback(self) -> None:
        actions: list = []
        integ = PredictiveLoopIntegration()
        integ.on_health_action(lambda a: actions.append(a) or {"corrected": True})
        integ.evaluate("a1", {
            "latency_p95": 9500, "error_rate": 0.45,
            "faithfulness": 0.05, "guard_blocks": 50,
        })
        assert len(actions) >= 1

    def test_cost_action_callback(self) -> None:
        ad = AnomalyDetector(z_threshold=2.0)
        ad.add_batch("cost", [10, 11, 9, 10, 12, 8, 10, 11, 9, 10])
        actions: list = []
        integ = PredictiveLoopIntegration(anomaly_detector=ad)
        integ.on_cost_action(lambda a: actions.append(a) or {"throttled": True})
        integ.evaluate("a1", {"cost_per_day": 200})
        assert len(actions) >= 1


# ---------------------------------------------------------------------------
# Alert history
# ---------------------------------------------------------------------------

class TestAlertHistory:
    def test_history_accumulates(self, integration: PredictiveLoopIntegration) -> None:
        integration.evaluate("a1", {"error_rate": 0.45, "faithfulness": 0.1})
        integration.evaluate("a2", {"error_rate": 0.45, "faithfulness": 0.1})
        assert len(integration.alerts_history) >= 2

    def test_history_is_copy(self, integration: PredictiveLoopIntegration) -> None:
        h1 = integration.alerts_history
        h2 = integration.alerts_history
        assert h1 is not h2


# ---------------------------------------------------------------------------
# AlertType enum
# ---------------------------------------------------------------------------

class TestAlertType:
    def test_values(self) -> None:
        assert AlertType.DRIFT_PREDICTED.value == "drift_predicted"
        assert AlertType.COST_SPIKE.value == "cost_spike"
        assert AlertType.HEALTH_CRITICAL.value == "health_critical"
        assert AlertType.HEALTH_WARNING.value == "health_warning"
        assert AlertType.LATENCY_SPIKE.value == "latency_spike"


# ---------------------------------------------------------------------------
# PredictiveAlert
# ---------------------------------------------------------------------------

class TestPredictiveAlert:
    def test_frozen(self) -> None:
        alert = PredictiveAlert(
            alert_type=AlertType.HEALTH_WARNING,
            agent_id="a1",
            message="test",
            severity="warning",
            details={},
            timestamp=1000.0,
        )
        assert alert.alert_type == AlertType.HEALTH_WARNING
        assert alert.action_taken == ""
