"""Tests for aegis.loops.latency_scale — LatencyAutoScale closed loop."""

from __future__ import annotations

import time

from aegis.loops.latency_scale import LatencyAutoScale
from aegis.loops.base import LoopStatus
from aegis.observe.metrics import SlidingWindowMetrics
from aegis.remember.provenance import ActivityType, ProvenanceTracker


class TestLatencyAutoScale:
    def _make(self, *, threshold=1000.0, cooldown=0.0):
        metrics = SlidingWindowMetrics(window_seconds=300)
        tracker = ProvenanceTracker()
        fallback_calls = []

        def fallback_fn(diag):
            fallback_calls.append(diag)
            # Simulate: clear metrics after fallback (model switch)
            metrics.clear()
            return {"action": "switched_to_light_model"}

        loop = LatencyAutoScale(
            metrics=metrics,
            p95_threshold_ms=threshold,
            fallback_fn=fallback_fn,
            tracker=tracker,
            cooldown_seconds=cooldown,
        )
        return loop, metrics, tracker, fallback_calls

    def test_detect_no_data(self):
        loop, _, _, _ = self._make()
        assert loop.detect() is None

    def test_detect_below_threshold(self):
        loop, metrics, _, _ = self._make(threshold=5000)
        for _ in range(10):
            metrics.record(100.0)
        assert loop.detect() is None

    def test_detect_above_threshold(self):
        loop, metrics, _, _ = self._make(threshold=500)
        for _ in range(20):
            metrics.record(1000.0)
        diag = loop.detect()
        assert diag is not None
        assert diag["p95"] > 500

    def test_full_cycle_success(self):
        loop, metrics, tracker, calls = self._make(threshold=500)
        for _ in range(20):
            metrics.record(2000.0)
        result = loop.run()
        assert result.status == LoopStatus.SUCCESS
        assert result.validated
        assert len(calls) == 1
        assert calls[0]["p95"] > 500

    def test_provenance_logged(self):
        loop, metrics, tracker, _ = self._make(threshold=500)
        for _ in range(20):
            metrics.record(2000.0)
        loop.run()
        trail = tracker.trail(activity=ActivityType.UPDATE)
        actions = [r.attributes.get("action") for r in trail]
        assert "fallback" in actions

    def test_cooldown(self):
        loop, metrics, _, calls = self._make(threshold=500, cooldown=60)
        for _ in range(20):
            metrics.record(2000.0)
        now = time.time()
        loop.run(now=now)
        # Refill with high latency
        for _ in range(20):
            metrics.record(2000.0)
        # Run again within cooldown
        result = loop.run(now=now + 10)
        assert result.status == LoopStatus.IDLE  # cooldown prevents detection

    def test_cooldown_expired(self):
        loop, metrics, _, calls = self._make(threshold=500, cooldown=60)
        for _ in range(20):
            metrics.record(2000.0)
        now = time.time()
        loop.run(now=now)
        for _ in range(20):
            metrics.record(2000.0)
        result = loop.run(now=now + 61)
        assert result.status == LoopStatus.SUCCESS

    def test_load_patterns_recorded(self):
        loop, metrics, _, _ = self._make(threshold=500)
        for _ in range(20):
            metrics.record(2000.0)
        loop.run()
        assert len(loop.load_patterns) == 1
        assert loop.load_patterns[0]["validated"]

    def test_threshold_property(self):
        loop, _, _, _ = self._make(threshold=1234.0)
        assert loop.threshold == 1234.0

    def test_idle_when_below(self):
        loop, metrics, _, _ = self._make(threshold=5000)
        for _ in range(10):
            metrics.record(100.0)
        result = loop.run()
        assert result.status == LoopStatus.IDLE
