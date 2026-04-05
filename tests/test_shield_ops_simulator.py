"""Tests for scripts/simulate_shield_ops.py — data simulator."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.simulate_shield_ops import _generate_trace, simulate, MODEL_PROFILES, PLATFORM_MODELS
from aegis.core.trace import Span, SpanStatus
from aegis.local.store import LocalStore


# ---------------------------------------------------------------------------
# Individual trace generation
# ---------------------------------------------------------------------------

class TestTraceGeneration:
    def test_generates_span(self) -> None:
        span = _generate_trace("edgy", "claude-sonnet", "compliance-check", 1000.0, 1.0)
        assert isinstance(span, Span)
        assert span.name == "edgy:compliance-check"
        assert span.workspace == "shield-ops-x5"

    def test_has_required_attributes(self) -> None:
        span = _generate_trace("safefleet", "gpt-4o-mini", "query", 1000.0, 0.5)
        attrs = span.attributes
        assert "platform" in attrs
        assert "model" in attrs
        assert "tokens" in attrs
        assert "cost" in attrs
        assert "faithfulness" in attrs
        assert "aegis.guard.status" in attrs

    def test_cost_is_positive(self) -> None:
        for _ in range(50):
            span = _generate_trace("edgy", "claude-opus", "analyze", 1000.0, 1.0)
            assert span.attributes["cost"] >= 0

    def test_tokens_are_positive(self) -> None:
        for _ in range(50):
            span = _generate_trace("edgy", "claude-sonnet", "query", 1000.0, 1.0)
            assert span.attributes["tokens"] > 0

    def test_latency_is_positive(self) -> None:
        for _ in range(50):
            span = _generate_trace("edgy", "gpt-4o", "query", 1000.0, 1.0)
            assert span.duration_ms > 0

    def test_faithfulness_in_range(self) -> None:
        for _ in range(100):
            span = _generate_trace("edgy", "claude-sonnet", "query", 1000.0, 7.0)
            faith = span.attributes["faithfulness"]
            assert 0.0 <= faith <= 1.0

    def test_different_models_different_latency(self) -> None:
        opus_latencies = [
            _generate_trace("edgy", "claude-opus", "q", 1000.0, 1.0).duration_ms
            for _ in range(30)
        ]
        mini_latencies = [
            _generate_trace("edgy", "gpt-4o-mini", "q", 1000.0, 1.0).duration_ms
            for _ in range(30)
        ]
        # Opus should generally be slower than mini
        assert sum(opus_latencies) / len(opus_latencies) > sum(mini_latencies) / len(mini_latencies)


# ---------------------------------------------------------------------------
# Full simulation
# ---------------------------------------------------------------------------

class TestSimulation:
    def test_simulate_generates_traces(self, tmp_path: Path) -> None:
        db = str(tmp_path / "sim.db")
        stats = simulate(db_path=db, quiet=True)
        assert stats["total_traces"] > 1000
        assert stats["platforms"] == 21

    def test_simulate_stores_to_db(self, tmp_path: Path) -> None:
        db = str(tmp_path / "sim.db")
        simulate(db_path=db, quiet=True)
        store = LocalStore(db_path=db)
        traces = store.recent_traces(limit=10)
        assert len(traces) == 10
        assert all(t["workspace"] == "shield-ops-x5" for t in traces)

    def test_simulate_has_errors(self, tmp_path: Path) -> None:
        db = str(tmp_path / "sim.db")
        stats = simulate(db_path=db, quiet=True)
        assert stats["total_errors"] > 0

    def test_simulate_has_guard_blocks(self, tmp_path: Path) -> None:
        db = str(tmp_path / "sim.db")
        stats = simulate(db_path=db, quiet=True)
        assert stats["total_blocks"] > 0

    def test_simulate_covers_all_platforms(self, tmp_path: Path) -> None:
        db = str(tmp_path / "sim.db")
        simulate(db_path=db, quiet=True)
        store = LocalStore(db_path=db)
        traces = store.recent_traces(limit=5000)
        platforms = {t["name"].split(":")[0] for t in traces}
        assert len(platforms) == 21

    def test_simulate_has_varied_latency(self, tmp_path: Path) -> None:
        db = str(tmp_path / "sim.db")
        simulate(db_path=db, quiet=True)
        store = LocalStore(db_path=db)
        stats = store.stats()
        assert stats["avg_latency_ms"] > 50
        assert stats["max_latency_ms"] > stats["avg_latency_ms"]


# ---------------------------------------------------------------------------
# Model profiles
# ---------------------------------------------------------------------------

class TestModelProfiles:
    def test_all_profiles_exist(self) -> None:
        assert "claude-sonnet" in MODEL_PROFILES
        assert "claude-opus" in MODEL_PROFILES
        assert "gpt-4o" in MODEL_PROFILES
        assert "gpt-4o-mini" in MODEL_PROFILES

    def test_all_platform_models_valid(self) -> None:
        for code, models in PLATFORM_MODELS.items():
            for model in models:
                assert model in MODEL_PROFILES, f"{code} uses unknown model {model}"

    def test_cost_ordering(self) -> None:
        # Opus should be most expensive
        assert MODEL_PROFILES["claude-opus"]["cost_per_1k"] > MODEL_PROFILES["claude-sonnet"]["cost_per_1k"]
        assert MODEL_PROFILES["claude-sonnet"]["cost_per_1k"] > MODEL_PROFILES["gpt-4o-mini"]["cost_per_1k"]
