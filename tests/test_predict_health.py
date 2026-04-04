"""Tests for aegis.predict.health_score — HealthScore calculator."""

from __future__ import annotations

import pytest

from aegis.predict.health_score import (
    DEFAULT_WEIGHTS,
    HealthScore,
    HealthStatus,
    ScoreSnapshot,
)


@pytest.fixture()
def hs() -> HealthScore:
    return HealthScore()


# ---------------------------------------------------------------------------
# Score computation
# ---------------------------------------------------------------------------

class TestHealthScoreCompute:
    def test_perfect_metrics(self, hs: HealthScore) -> None:
        snap = hs.compute("a1", {
            "latency_p95": 200.0,   # ideal
            "error_rate": 0.0,       # ideal
            "cost_per_day": 0.0,     # ideal
            "faithfulness": 1.0,     # ideal
            "guard_blocks": 0.0,     # ideal
            "drift": 0.0,            # ideal
            "memory_usage": 0.0,     # ideal
        })
        assert snap.score == 100.0
        assert snap.status == HealthStatus.HEALTHY

    def test_worst_metrics(self, hs: HealthScore) -> None:
        snap = hs.compute("a1", {
            "latency_p95": 10000.0,
            "error_rate": 0.5,
            "cost_per_day": 100.0,
            "faithfulness": 0.0,
            "guard_blocks": 50.0,
            "drift": 0.5,
            "memory_usage": 1.0,
        })
        assert snap.score == 0.0
        assert snap.status == HealthStatus.CRITICAL

    def test_mixed_healthy(self, hs: HealthScore) -> None:
        snap = hs.compute("a1", {
            "latency_p95": 350.0,
            "error_rate": 0.02,
            "faithfulness": 0.95,
        })
        assert snap.status == HealthStatus.HEALTHY
        assert snap.score >= 80.0

    def test_warning_zone(self, hs: HealthScore) -> None:
        snap = hs.compute("a1", {
            "latency_p95": 5000.0,
            "error_rate": 0.15,
            "faithfulness": 0.6,
            "guard_blocks": 20.0,
        })
        assert snap.status in (HealthStatus.WARNING, HealthStatus.CRITICAL)
        assert snap.score < 80.0

    def test_partial_metrics(self, hs: HealthScore) -> None:
        """Score should work with only a subset of metrics."""
        snap = hs.compute("a1", {"faithfulness": 0.95})
        assert isinstance(snap.score, float)
        assert 0 <= snap.score <= 100

    def test_no_metrics(self, hs: HealthScore) -> None:
        """No metrics → default healthy (no evidence of problems)."""
        snap = hs.compute("a1", {})
        assert snap.score == 100.0

    def test_returns_snapshot(self, hs: HealthScore) -> None:
        snap = hs.compute("a1", {"error_rate": 0.1})
        assert isinstance(snap, ScoreSnapshot)
        assert snap.agent_id == "a1"
        assert snap.timestamp > 0
        assert "error_rate" in snap.components
        assert "error_rate" in snap.raw_inputs


# ---------------------------------------------------------------------------
# Classification thresholds
# ---------------------------------------------------------------------------

class TestHealthStatusClassification:
    def test_healthy_at_80(self, hs: HealthScore) -> None:
        assert hs._classify(80.0) == HealthStatus.HEALTHY

    def test_healthy_at_100(self, hs: HealthScore) -> None:
        assert hs._classify(100.0) == HealthStatus.HEALTHY

    def test_warning_at_79(self, hs: HealthScore) -> None:
        assert hs._classify(79.9) == HealthStatus.WARNING

    def test_warning_at_60(self, hs: HealthScore) -> None:
        assert hs._classify(60.0) == HealthStatus.WARNING

    def test_critical_at_59(self, hs: HealthScore) -> None:
        assert hs._classify(59.9) == HealthStatus.CRITICAL

    def test_critical_at_0(self, hs: HealthScore) -> None:
        assert hs._classify(0.0) == HealthStatus.CRITICAL


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

class TestNormalise:
    def test_ideal_value(self) -> None:
        assert HealthScore._normalise(200.0, 200.0, 10000.0) == 100.0

    def test_worst_value(self) -> None:
        assert HealthScore._normalise(10000.0, 200.0, 10000.0) == 0.0

    def test_mid_value(self) -> None:
        result = HealthScore._normalise(5100.0, 200.0, 10000.0)
        assert 45 < result < 55  # approximately 50%

    def test_beyond_worst(self) -> None:
        """Values worse than worst should clamp to 0."""
        assert HealthScore._normalise(20000.0, 200.0, 10000.0) == 0.0

    def test_better_than_ideal(self) -> None:
        """Values better than ideal should clamp to 100."""
        assert HealthScore._normalise(50.0, 200.0, 10000.0) == 100.0

    def test_inverted_scale(self) -> None:
        """Faithfulness: 1.0 ideal, 0.0 worst."""
        assert HealthScore._normalise(1.0, 1.0, 0.0) == 100.0
        assert HealthScore._normalise(0.0, 1.0, 0.0) == 0.0


# ---------------------------------------------------------------------------
# History and trend
# ---------------------------------------------------------------------------

class TestHealthHistory:
    def test_history_stored(self, hs: HealthScore) -> None:
        hs.compute("a1", {"error_rate": 0.01})
        hs.compute("a1", {"error_rate": 0.02})
        assert len(hs.history("a1")) == 2

    def test_history_per_agent(self, hs: HealthScore) -> None:
        hs.compute("a1", {"error_rate": 0.01})
        hs.compute("a2", {"error_rate": 0.01})
        assert len(hs.history("a1")) == 1
        assert len(hs.history("a2")) == 1

    def test_empty_history(self, hs: HealthScore) -> None:
        assert hs.history("nonexistent") == []

    def test_clear_history(self, hs: HealthScore) -> None:
        hs.compute("a1", {"error_rate": 0.01})
        hs.clear_history("a1")
        assert hs.history("a1") == []

    def test_clear_all_history(self, hs: HealthScore) -> None:
        hs.compute("a1", {"error_rate": 0.01})
        hs.compute("a2", {"error_rate": 0.01})
        hs.clear_history()
        assert hs.history("a1") == []
        assert hs.history("a2") == []


class TestHealthTrend:
    def test_stable(self, hs: HealthScore) -> None:
        for _ in range(5):
            hs.compute("a1", {"error_rate": 0.01})
        trend = hs.trend("a1")
        assert trend["direction"] == "stable"

    def test_improving(self, hs: HealthScore) -> None:
        rates = [0.3, 0.25, 0.20, 0.15, 0.10, 0.05]
        for r in rates:
            hs.compute("a1", {"error_rate": r})
        trend = hs.trend("a1")
        assert trend["direction"] == "improving"

    def test_degrading(self, hs: HealthScore) -> None:
        rates = [0.01, 0.05, 0.10, 0.15, 0.25, 0.35]
        for r in rates:
            hs.compute("a1", {"error_rate": r})
        trend = hs.trend("a1")
        assert trend["direction"] == "degrading"

    def test_insufficient_data(self, hs: HealthScore) -> None:
        hs.compute("a1", {"error_rate": 0.01})
        trend = hs.trend("a1")
        assert trend["direction"] == "stable"
        assert trend["points"] == 1


# ---------------------------------------------------------------------------
# Custom weights
# ---------------------------------------------------------------------------

class TestCustomWeights:
    def test_custom_weights(self) -> None:
        hs = HealthScore(weights={"error_rate": 1.0})
        snap = hs.compute("a1", {"error_rate": 0.0})
        assert snap.score == 100.0

    def test_properties(self, hs: HealthScore) -> None:
        assert hs.weights == DEFAULT_WEIGHTS
        assert "latency_p95" in hs.normalisers
