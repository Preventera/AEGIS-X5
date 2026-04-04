"""CostForecaster — predicts LLM costs over 7 days with anomaly detection.

Pure stdlib implementation — no external ML dependencies.
"""

from __future__ import annotations

import math
import statistics
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DailyForecast:
    """Predicted cost for a single day."""

    day_offset: int  # 1 = tomorrow, 7 = next week
    predicted_cost: float
    lower_bound: float
    upper_bound: float


@dataclass(frozen=True)
class CostAnomaly:
    """A detected cost anomaly."""

    timestamp: float
    agent_id: str
    actual_cost: float
    expected_cost: float
    deviation: float  # how many stddevs above/below
    direction: str    # "spike" or "drop"


@dataclass(frozen=True)
class CostForecastResult:
    """Full cost forecast output."""

    agent_id: str
    daily_forecast: list[DailyForecast]
    weekly_total: float
    anomalies: list[CostAnomaly]
    budget_alert: str | None  # None = within budget
    method: str


@dataclass
class CostDataPoint:
    """A daily cost observation."""

    timestamp: float
    cost: float
    agent_id: str = ""


class CostForecaster:
    """Predicts LLM costs and detects anomalies.

    Usage::

        forecaster = CostForecaster(daily_budget=50.0)
        forecaster.add_daily_cost("agent-1", day_timestamp, 12.50)
        # ... add history ...
        result = forecaster.forecast("agent-1")
        print(result.weekly_total, result.anomalies)

    Parameters
    ----------
    daily_budget : float
        Budget threshold per agent per day (triggers alert).
    anomaly_threshold : float
        Z-score threshold for spike/drop detection.
    min_history_days : int
        Minimum days of history before forecasting.
    """

    def __init__(
        self,
        *,
        daily_budget: float = 50.0,
        anomaly_threshold: float = 2.5,
        min_history_days: int = 3,
    ) -> None:
        self._budget = daily_budget
        self._anomaly_threshold = anomaly_threshold
        self._min_days = min_history_days
        self._data: dict[str, list[CostDataPoint]] = {}

    @property
    def daily_budget(self) -> float:
        return self._budget

    @daily_budget.setter
    def daily_budget(self, value: float) -> None:
        self._budget = value

    def add_daily_cost(self, agent_id: str, timestamp: float, cost: float) -> None:
        """Record a daily cost observation."""
        self._data.setdefault(agent_id, []).append(
            CostDataPoint(timestamp=timestamp, cost=cost, agent_id=agent_id)
        )

    def add_costs(self, agent_id: str, costs: list[tuple[float, float]]) -> None:
        """Bulk-add (timestamp, cost) pairs."""
        for ts, c in costs:
            self.add_daily_cost(agent_id, ts, c)

    def clear(self, agent_id: str | None = None) -> None:
        if agent_id:
            self._data.pop(agent_id, None)
        else:
            self._data.clear()

    def forecast(self, agent_id: str, days: int = 7) -> CostForecastResult:
        """Generate a cost forecast for the next N days."""
        points = sorted(self._data.get(agent_id, []), key=lambda p: p.timestamp)
        costs = [p.cost for p in points]

        if len(costs) < self._min_days:
            return CostForecastResult(
                agent_id=agent_id,
                daily_forecast=[],
                weekly_total=0.0,
                anomalies=[],
                budget_alert=None,
                method="insufficient_data",
            )

        # --- Detect anomalies in historical data ---
        anomalies = self._detect_anomalies(points)

        # --- Forecast using weighted moving average + trend ---
        mean_cost = statistics.mean(costs)
        stdev = statistics.stdev(costs) if len(costs) >= 2 else 0.0

        # Weighted recent average (last 7 days weigh more)
        recent = costs[-7:] if len(costs) >= 7 else costs
        weights = list(range(1, len(recent) + 1))  # linear increasing
        w_sum = sum(w * c for w, c in zip(weights, recent))
        w_total = sum(weights)
        weighted_avg = w_sum / w_total

        # Trend: linear slope over all data
        n = len(costs)
        xs = list(range(n))
        sx = sum(xs)
        sy = sum(costs)
        sxy = sum(x * y for x, y in zip(xs, costs))
        sx2 = sum(x * x for x in xs)
        denom = n * sx2 - sx * sx
        slope = (n * sxy - sx * sy) / denom if abs(denom) > 1e-12 else 0.0

        # Generate daily forecasts
        daily: list[DailyForecast] = []
        for d in range(1, days + 1):
            pred = weighted_avg + slope * d
            pred = max(0.0, pred)  # cost can't be negative
            ci = 1.96 * stdev * math.sqrt(1 + d / n) if stdev > 0 else 0.0
            daily.append(DailyForecast(
                day_offset=d,
                predicted_cost=round(pred, 2),
                lower_bound=round(max(0.0, pred - ci), 2),
                upper_bound=round(pred + ci, 2),
            ))

        weekly_total = round(sum(f.predicted_cost for f in daily), 2)

        # Budget alert
        budget_alert = None
        weekly_budget = self._budget * days
        if weekly_total > weekly_budget:
            overage = weekly_total - weekly_budget
            budget_alert = (
                f"Projected cost ${weekly_total:.2f} exceeds "
                f"budget ${weekly_budget:.2f} by ${overage:.2f}"
            )
        # Also check if any single day exceeds daily budget
        for f in daily:
            if f.predicted_cost > self._budget:
                budget_alert = budget_alert or (
                    f"Day {f.day_offset}: projected ${f.predicted_cost:.2f} "
                    f"exceeds daily budget ${self._budget:.2f}"
                )
                break

        return CostForecastResult(
            agent_id=agent_id,
            daily_forecast=daily,
            weekly_total=weekly_total,
            anomalies=anomalies,
            budget_alert=budget_alert,
            method="weighted_moving_average_trend",
        )

    def _detect_anomalies(self, points: list[CostDataPoint]) -> list[CostAnomaly]:
        """Detect cost spikes/drops using Z-score method."""
        costs = [p.cost for p in points]
        if len(costs) < 3:
            return []

        mean = statistics.mean(costs)
        stdev = statistics.stdev(costs)
        if stdev < 1e-9:
            return []

        anomalies: list[CostAnomaly] = []
        for p in points:
            z = (p.cost - mean) / stdev
            if abs(z) >= self._anomaly_threshold:
                anomalies.append(CostAnomaly(
                    timestamp=p.timestamp,
                    agent_id=p.agent_id,
                    actual_cost=p.cost,
                    expected_cost=round(mean, 2),
                    deviation=round(z, 2),
                    direction="spike" if z > 0 else "drop",
                ))

        return anomalies
