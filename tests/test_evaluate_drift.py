"""Tests for aegis.evaluate.drift — DriftDetector."""

from __future__ import annotations

import pytest

from aegis.evaluate.drift import AlertLevel, DriftDetector


class TestDriftDetector:
    def test_no_drift(self):
        d = DriftDetector()
        d.set_baseline({"faithfulness": 0.90, "relevancy": 0.85})
        alerts = d.check({"faithfulness": 0.88, "relevancy": 0.84})
        assert len(alerts) == 0  # within tolerance

    def test_warning(self):
        d = DriftDetector(warning_threshold=0.1, critical_threshold=0.25)
        d.set_baseline({"faithfulness": 0.90})
        alerts = d.check({"faithfulness": 0.78})
        assert len(alerts) == 1
        assert alerts[0].level == AlertLevel.WARNING
        assert alerts[0].metric == "faithfulness"

    def test_critical(self):
        d = DriftDetector(warning_threshold=0.1, critical_threshold=0.25)
        d.set_baseline({"faithfulness": 0.90})
        alerts = d.check({"faithfulness": 0.60})
        assert len(alerts) == 1
        assert alerts[0].level == AlertLevel.CRITICAL

    def test_multiple_metrics(self):
        d = DriftDetector(warning_threshold=0.05, critical_threshold=0.15)
        d.set_baseline({"a": 0.90, "b": 0.80, "c": 0.70})
        alerts = d.check({"a": 0.84, "b": 0.80, "c": 0.50})
        assert len(alerts) == 2  # a=warning, c=critical

    def test_missing_metric_ignored(self):
        d = DriftDetector()
        d.set_baseline({"x": 0.90})
        alerts = d.check({"y": 0.50})
        assert len(alerts) == 0

    def test_improvement_no_alert(self):
        d = DriftDetector()
        d.set_baseline({"x": 0.70})
        alerts = d.check({"x": 0.90})  # improved
        assert len(alerts) == 0

    def test_baseline_property(self):
        d = DriftDetector()
        d.set_baseline({"a": 0.5})
        assert d.baseline == {"a": 0.5}

    def test_alert_message(self):
        d = DriftDetector(warning_threshold=0.05, critical_threshold=0.2)
        d.set_baseline({"m": 0.90})
        alerts = d.check({"m": 0.80})
        assert "0.90" in alerts[0].message
        assert "0.80" in alerts[0].message

    def test_invalid_thresholds(self):
        with pytest.raises(ValueError):
            DriftDetector(warning_threshold=0.3, critical_threshold=0.1)

    def test_zero_threshold(self):
        with pytest.raises(ValueError):
            DriftDetector(warning_threshold=0)

    def test_delta_value(self):
        d = DriftDetector(warning_threshold=0.05, critical_threshold=0.2)
        d.set_baseline({"x": 0.90})
        alerts = d.check({"x": 0.80})
        assert alerts[0].delta == 0.1


class TestAlertLevel:
    def test_values(self):
        assert AlertLevel.OK.value == "ok"
        assert AlertLevel.WARNING.value == "warning"
        assert AlertLevel.CRITICAL.value == "critical"
