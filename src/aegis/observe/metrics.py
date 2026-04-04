"""Latency metrics — sliding window percentiles (p50/p95/p99)."""

from __future__ import annotations

import bisect
import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class LatencyStats:
    """Snapshot of latency percentiles."""

    count: int
    p50: float
    p95: float
    p99: float
    min: float
    max: float
    mean: float


class SlidingWindowMetrics:
    """Thread-safe sliding-window latency tracker.

    Parameters
    ----------
    window_seconds : float
        How far back to look (default 300s = 5 min).
    """

    def __init__(self, window_seconds: float = 300.0) -> None:
        self._window = window_seconds
        self._lock = threading.Lock()
        # Entries: (timestamp, latency_ms)
        self._entries: list[tuple[float, float]] = []

    def record(self, latency_ms: float, *, timestamp: float | None = None) -> None:
        """Record a latency sample."""
        ts = timestamp or time.time()
        with self._lock:
            self._entries.append((ts, latency_ms))

    def _prune(self, now: float) -> list[float]:
        """Remove expired entries, return current latencies sorted."""
        cutoff = now - self._window
        # Find first entry that is within the window
        idx = bisect.bisect_left(self._entries, (cutoff,))
        self._entries = self._entries[idx:]
        return sorted(lat for _, lat in self._entries)

    def stats(self) -> LatencyStats:
        """Compute current percentile snapshot."""
        with self._lock:
            values = self._prune(time.time())

        if not values:
            return LatencyStats(count=0, p50=0.0, p95=0.0, p99=0.0, min=0.0, max=0.0, mean=0.0)

        n = len(values)
        return LatencyStats(
            count=n,
            p50=_percentile(values, 0.50),
            p95=_percentile(values, 0.95),
            p99=_percentile(values, 0.99),
            min=values[0],
            max=values[-1],
            mean=sum(values) / n,
        )

    @property
    def count(self) -> int:
        with self._lock:
            self._prune(time.time())
            return len(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Nearest-rank percentile on a pre-sorted list."""
    n = len(sorted_values)
    if n == 0:
        return 0.0
    idx = int(pct * (n - 1))
    return sorted_values[idx]
