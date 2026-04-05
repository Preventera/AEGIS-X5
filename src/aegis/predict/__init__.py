"""aegis.predict — ML Predictive Analytics.

Health scoring, drift prediction, cost forecasting, anomaly detection,
and predictive loop integration. Pure stdlib — no PyTorch/sklearn.
"""

from aegis.predict.anomaly import AnomalyDetector, AnomalyDirection, AnomalyResult
from aegis.predict.cost import CostAnomaly, CostForecaster, CostForecastResult, DailyForecast
from aegis.predict.drift import DriftPrediction, DriftPredictor, DriftSeverity
from aegis.predict.engine import CalibrationRecord, PredictionEngine
from aegis.predict.health_score import HealthScore, HealthStatus, ScoreSnapshot
from aegis.predict.integration import AlertType, PredictiveAlert, PredictiveLoopIntegration

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
