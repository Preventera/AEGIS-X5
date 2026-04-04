"""Tests for aegis.predict.cost — CostForecaster."""

from __future__ import annotations

import time

import pytest

from aegis.predict.cost import (
    CostForecaster,
    CostForecastResult,
    DailyForecast,
    CostAnomaly,
)


@pytest.fixture()
def forecaster() -> CostForecaster:
    return CostForecaster(daily_budget=50.0, min_history_days=3)


def _make_history(
    forecaster: CostForecaster, agent: str, costs: list[float], start_ts: float = 1000.0
) -> None:
    """Helper: add daily cost history."""
    day = 86400.0
    for i, c in enumerate(costs):
        forecaster.add_daily_cost(agent, start_ts + i * day, c)


# ---------------------------------------------------------------------------
# Basic forecasting
# ---------------------------------------------------------------------------

class TestCostForecasterBasic:
    def test_insufficient_data(self, forecaster: CostForecaster) -> None:
        forecaster.add_daily_cost("a1", 1000, 10.0)
        result = forecaster.forecast("a1")
        assert result.method == "insufficient_data"
        assert result.daily_forecast == []

    def test_stable_costs(self, forecaster: CostForecaster) -> None:
        _make_history(forecaster, "a1", [10, 10, 10, 10, 10])
        result = forecaster.forecast("a1")
        assert len(result.daily_forecast) == 7
        for f in result.daily_forecast:
            assert abs(f.predicted_cost - 10.0) < 5.0  # should be near 10

    def test_increasing_costs(self, forecaster: CostForecaster) -> None:
        _make_history(forecaster, "a1", [10, 15, 20, 25, 30])
        result = forecaster.forecast("a1")
        # Trend should project higher costs
        assert result.daily_forecast[0].predicted_cost > 25

    def test_seven_day_forecast(self, forecaster: CostForecaster) -> None:
        _make_history(forecaster, "a1", [10, 12, 11, 13, 10])
        result = forecaster.forecast("a1", days=7)
        assert len(result.daily_forecast) == 7
        assert all(f.day_offset == i + 1 for i, f in enumerate(result.daily_forecast))

    def test_custom_days(self, forecaster: CostForecaster) -> None:
        _make_history(forecaster, "a1", [10, 12, 11, 13, 10])
        result = forecaster.forecast("a1", days=3)
        assert len(result.daily_forecast) == 3

    def test_weekly_total(self, forecaster: CostForecaster) -> None:
        _make_history(forecaster, "a1", [10, 10, 10, 10, 10])
        result = forecaster.forecast("a1")
        assert result.weekly_total == pytest.approx(
            sum(f.predicted_cost for f in result.daily_forecast), abs=0.1
        )


# ---------------------------------------------------------------------------
# Daily forecast structure
# ---------------------------------------------------------------------------

class TestDailyForecast:
    def test_has_bounds(self, forecaster: CostForecaster) -> None:
        _make_history(forecaster, "a1", [10, 12, 8, 15, 11])
        result = forecaster.forecast("a1")
        for f in result.daily_forecast:
            assert f.lower_bound <= f.predicted_cost <= f.upper_bound

    def test_non_negative(self, forecaster: CostForecaster) -> None:
        _make_history(forecaster, "a1", [1, 1, 1, 1, 1])
        result = forecaster.forecast("a1")
        for f in result.daily_forecast:
            assert f.predicted_cost >= 0
            assert f.lower_bound >= 0


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------

class TestCostAnomalyDetection:
    def test_spike_detected(self) -> None:
        # Lower anomaly threshold for easier detection
        fc = CostForecaster(daily_budget=50.0, anomaly_threshold=2.0, min_history_days=3)
        # 9 normal values, then 1 extreme spike
        _make_history(fc, "a1", [10, 11, 10, 9, 10, 11, 10, 9, 10, 100])
        result = fc.forecast("a1")
        assert len(result.anomalies) >= 1
        assert result.anomalies[0].direction == "spike"

    def test_no_anomaly_stable(self, forecaster: CostForecaster) -> None:
        _make_history(forecaster, "a1", [10, 11, 10, 9, 10])
        result = forecaster.forecast("a1")
        assert result.anomalies == []

    def test_drop_detected(self) -> None:
        fc = CostForecaster(daily_budget=50.0, anomaly_threshold=2.0, min_history_days=3)
        _make_history(fc, "a1", [50, 51, 49, 50, 52, 48, 50, 51, 49, 1])
        result = fc.forecast("a1")
        drops = [a for a in result.anomalies if a.direction == "drop"]
        assert len(drops) >= 1


# ---------------------------------------------------------------------------
# Budget alerts
# ---------------------------------------------------------------------------

class TestBudgetAlerts:
    def test_within_budget(self, forecaster: CostForecaster) -> None:
        _make_history(forecaster, "a1", [5, 5, 5, 5, 5])
        result = forecaster.forecast("a1")
        assert result.budget_alert is None

    def test_over_budget(self) -> None:
        fc = CostForecaster(daily_budget=10.0, min_history_days=3)
        _make_history(fc, "a1", [20, 25, 30, 35, 40])
        result = fc.forecast("a1")
        assert result.budget_alert is not None
        assert "exceeds" in result.budget_alert.lower()


# ---------------------------------------------------------------------------
# Data management
# ---------------------------------------------------------------------------

class TestCostForecasterData:
    def test_add_costs_bulk(self, forecaster: CostForecaster) -> None:
        forecaster.add_costs("a1", [(1000, 10), (2000, 20), (3000, 30)])
        result = forecaster.forecast("a1")
        assert result.method != "insufficient_data"

    def test_clear_agent(self, forecaster: CostForecaster) -> None:
        _make_history(forecaster, "a1", [10, 20, 30])
        forecaster.clear("a1")
        result = forecaster.forecast("a1")
        assert result.method == "insufficient_data"

    def test_clear_all(self, forecaster: CostForecaster) -> None:
        _make_history(forecaster, "a1", [10, 20, 30])
        _make_history(forecaster, "a2", [10, 20, 30])
        forecaster.clear()
        assert forecaster.forecast("a1").method == "insufficient_data"
        assert forecaster.forecast("a2").method == "insufficient_data"

    def test_budget_property(self, forecaster: CostForecaster) -> None:
        assert forecaster.daily_budget == 50.0
        forecaster.daily_budget = 100.0
        assert forecaster.daily_budget == 100.0
