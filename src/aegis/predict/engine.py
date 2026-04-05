"""PredictionEngine — orchestrates all predictors with calibration tracking.

Registers predictions, compares them against reality, and exposes accuracy metrics.
"""

from __future__ import annotations

import math
import statistics
import time
from dataclasses import dataclass
from typing import Any

from aegis.predict.anomaly import AnomalyDetector
from aegis.predict.cost import CostForecaster
from aegis.predict.drift import DriftPredictor
from aegis.predict.health_score import HealthScore

# ---------------------------------------------------------------------------
# Calibration record: prediction vs reality
# ---------------------------------------------------------------------------

@dataclass
class CalibrationRecord:
    """Tracks a prediction and its eventual actual outcome."""

    prediction_id: str
    metric: str
    agent_id: str
    predicted_value: float
    predicted_at: float
    horizon_hours: float
    actual_value: float | None = None
    resolved_at: float | None = None

    @property
    def error(self) -> float | None:
        """Absolute error (None if not yet resolved)."""
        if self.actual_value is None:
            return None
        return abs(self.predicted_value - self.actual_value)

    @property
    def is_resolved(self) -> bool:
        return self.actual_value is not None


# ---------------------------------------------------------------------------
# PredictionEngine
# ---------------------------------------------------------------------------

class PredictionEngine:
    """Orchestrates HealthScore, DriftPredictor, CostForecaster, AnomalyDetector.

    Usage::

        engine = PredictionEngine()
        engine.health_score.compute("agent-1", {"latency_p95": 300})
        engine.drift_predictor.add_point("faithfulness", ts, 0.93)
        report = engine.full_report("agent-1")
        acc = engine.accuracy()

    Provides calibration tracking: register predictions, then resolve with
    actual values to compute prediction accuracy over time.
    """

    def __init__(
        self,
        *,
        health_score: HealthScore | None = None,
        drift_predictor: DriftPredictor | None = None,
        cost_forecaster: CostForecaster | None = None,
        anomaly_detector: AnomalyDetector | None = None,
    ) -> None:
        self.health_score = health_score or HealthScore()
        self.drift_predictor = drift_predictor or DriftPredictor()
        self.cost_forecaster = cost_forecaster or CostForecaster()
        self.anomaly_detector = anomaly_detector or AnomalyDetector()

        self._calibration: list[CalibrationRecord] = []
        self._prediction_counter = 0

    # -- prediction registration --

    def register_prediction(
        self,
        metric: str,
        agent_id: str,
        predicted_value: float,
        horizon_hours: float = 48.0,
    ) -> str:
        """Register a prediction for later calibration. Returns prediction_id."""
        self._prediction_counter += 1
        pid = f"pred-{self._prediction_counter:06d}"
        self._calibration.append(CalibrationRecord(
            prediction_id=pid,
            metric=metric,
            agent_id=agent_id,
            predicted_value=predicted_value,
            predicted_at=time.time(),
            horizon_hours=horizon_hours,
        ))
        return pid

    def resolve_prediction(
        self, prediction_id: str, actual_value: float
    ) -> CalibrationRecord | None:
        """Record the actual outcome of a prediction."""
        for rec in self._calibration:
            if rec.prediction_id == prediction_id:
                rec.actual_value = actual_value
                rec.resolved_at = time.time()
                return rec
        return None

    # -- accuracy --

    def accuracy(self, metric: str | None = None) -> dict[str, Any]:
        """Compute prediction accuracy from resolved calibration records.

        Returns MAE, RMSE, count, and per-metric breakdown.
        """
        resolved = [
            r for r in self._calibration
            if r.is_resolved and (metric is None or r.metric == metric)
        ]

        if not resolved:
            return {
                "count": 0,
                "mae": None,
                "rmse": None,
                "metrics": {},
            }

        errors = [r.error for r in resolved if r.error is not None]
        mae = statistics.mean(errors)
        rmse = math.sqrt(statistics.mean([e * e for e in errors]))

        # Per-metric breakdown
        by_metric: dict[str, list[float]] = {}
        for r in resolved:
            if r.error is not None:
                by_metric.setdefault(r.metric, []).append(r.error)

        metric_stats = {}
        for m, errs in by_metric.items():
            metric_stats[m] = {
                "count": len(errs),
                "mae": round(statistics.mean(errs), 4),
                "rmse": round(math.sqrt(statistics.mean([e * e for e in errs])), 4),
            }

        return {
            "count": len(resolved),
            "mae": round(mae, 4),
            "rmse": round(rmse, 4),
            "metrics": metric_stats,
        }

    @property
    def calibration_records(self) -> list[CalibrationRecord]:
        return list(self._calibration)

    def pending_predictions(self) -> list[CalibrationRecord]:
        """Return predictions not yet resolved."""
        return [r for r in self._calibration if not r.is_resolved]

    # -- full report --

    def full_report(
        self,
        agent_id: str,
        *,
        metrics: dict[str, float] | None = None,
        drift_metric: str = "faithfulness",
        drift_horizon: float = 48.0,
        cost_days: int = 7,
    ) -> dict[str, Any]:
        """Generate a comprehensive prediction report for an agent.

        Parameters
        ----------
        agent_id : str
            Agent identifier.
        metrics : dict | None
            Current health metrics (passed to HealthScore).
        drift_metric : str
            Which metric to predict drift for.
        drift_horizon : float
            Hours ahead to predict drift.
        cost_days : int
            Days ahead to forecast costs.
        """
        report: dict[str, Any] = {"agent_id": agent_id, "timestamp": time.time()}

        # Health score
        if metrics:
            snap = self.health_score.compute(agent_id, metrics)
            report["health"] = {
                "score": snap.score,
                "status": snap.status.value,
                "components": snap.components,
                "trend": self.health_score.trend(agent_id),
            }

        # Drift prediction
        drift_series = self.drift_predictor.series(drift_metric)
        if drift_series:
            drift_pred = self.drift_predictor.predict(
                drift_metric, horizon_hours=drift_horizon
            )
            report["drift"] = {
                "metric": drift_pred.metric,
                "current": drift_pred.current_value,
                "predicted": drift_pred.predicted_value,
                "confidence_interval": drift_pred.confidence_interval,
                "time_to_threshold_hours": drift_pred.time_to_threshold_hours,
                "severity": drift_pred.severity.value,
                "message": drift_pred.message,
            }
            # Register for calibration
            self.register_prediction(
                drift_metric, agent_id,
                drift_pred.predicted_value,
                drift_horizon,
            )

        # Cost forecast
        cost_result = self.cost_forecaster.forecast(agent_id, days=cost_days)
        if cost_result.daily_forecast:
            report["cost"] = {
                "weekly_total": cost_result.weekly_total,
                "daily_forecast": [
                    {"day": f.day_offset, "cost": f.predicted_cost}
                    for f in cost_result.daily_forecast
                ],
                "anomalies": len(cost_result.anomalies),
                "budget_alert": cost_result.budget_alert,
            }

        # Accuracy
        report["accuracy"] = self.accuracy()

        return report

    def clear(self) -> None:
        """Reset all predictors and calibration data."""
        self.health_score.clear_history()
        self.drift_predictor.clear()
        self.cost_forecaster.clear()
        self.anomaly_detector.clear()
        self._calibration.clear()
        self._prediction_counter = 0
