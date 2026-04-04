"""aegis.predict — ML Predictive Analytics.

Health scoring, drift prediction, cost forecasting, anomaly detection,
and predictive loop integration. Pure stdlib — no PyTorch/sklearn.
"""

from aegis.predict.anomaly import AnomalyDetector, AnomalyDirection, AnomalyResult
from aegis.predict.cost import CostForecaster, CostForecastResult, DailyForecast, CostAnomaly
from aegis.predict.drift import DriftPredictor, DriftPrediction, DriftSeverity
from aegis.predict.engine import PredictionEngine, CalibrationRecord
from aegis.predict.health_score import HealthScore, HealthStatus, ScoreSnapshot
from aegis.predict.integration import PredictiveLoopIntegration, PredictiveAlert, AlertType

__all__ = [
    "AlertType",
    "AnomalyDetector",
    "AnomalyDirection",
    "AnomalyResult",
    "CalibrationRecord",
    "CostAnomaly",
    "CostForecaster",
    "CostForecastResult",
    "DailyForecast",
    "DriftPredictor",
    "DriftPrediction",
    "DriftSeverity",
    "HealthScore",
    "HealthStatus",
    "PredictionEngine",
    "PredictiveAlert",
    "PredictiveLoopIntegration",
    "ScoreSnapshot",
]
