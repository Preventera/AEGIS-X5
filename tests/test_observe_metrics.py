"""Tests for aegis.observe.metrics — sliding window latency percentiles."""

from __future__ import annotations

import time

from aegis.observe.metrics import SlidingWindowMetrics, _percentile


class TestPercentile:
    def test_single_value(self):
        assert _percentile([5.0], 0.50) == 5.0

    def test_even_distribution(self):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert _percentile(vals, 0.50) == 3.0
        assert _percentile(vals, 0.99) >= 4.0

    def test_empty(self):
        assert _percentile([], 0.50) == 0.0


class TestSlidingWindowMetrics:
    def test_record_and_stats(self):
        m = SlidingWindowMetrics(window_seconds=60)
        for v in [10.0, 20.0, 30.0, 40.0, 50.0]:
            m.record(v)
        s = m.stats()
        assert s.count == 5
        assert s.min == 10.0
        assert s.max == 50.0
        assert s.mean == 30.0
        assert s.p50 == 30.0

    def test_empty_stats(self):
        m = SlidingWindowMetrics()
        s = m.stats()
        assert s.count == 0
        assert s.p50 == 0.0
        assert s.mean == 0.0

    def test_window_expiry(self):
        m = SlidingWindowMetrics(window_seconds=1.0)
        now = time.time()
        # Old entry (expired)
        m.record(100.0, timestamp=now - 5.0)
        # Recent entry
        m.record(50.0, timestamp=now)
        s = m.stats()
        assert s.count == 1
        assert s.p50 == 50.0

    def test_clear(self):
        m = SlidingWindowMetrics()
        m.record(10.0)
        m.record(20.0)
        m.clear()
        assert m.count == 0

    def test_count_property(self):
        m = SlidingWindowMetrics()
        assert m.count == 0
        m.record(1.0)
        m.record(2.0)
        assert m.count == 2

    def test_p95_p99(self):
        m = SlidingWindowMetrics()
        # 100 values: 1..100
        for i in range(1, 101):
            m.record(float(i))
        s = m.stats()
        assert s.count == 100
        assert s.p95 >= 90.0
        assert s.p99 >= 95.0
        assert s.min == 1.0
        assert s.max == 100.0
