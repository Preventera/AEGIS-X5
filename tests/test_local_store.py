"""Tests for aegis.local.store — SQLite local storage backend."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from aegis.core.trace import Span, SpanStatus
from aegis.local.store import LocalStore, TraceSummary


@pytest.fixture()
def store(tmp_path: Path) -> LocalStore:
    """Fresh SQLite store in a temp directory."""
    return LocalStore(db_path=tmp_path / "test.db")


@pytest.fixture()
def sample_span() -> Span:
    """A basic finished span."""
    span = Span(name="test-op", workspace="test-ws", tenant_id="t123")
    span.start_time = 1000.0
    span.end_time = 1000.142
    span.set_attribute("tokens", 1250)
    span.set_attribute("cost", 0.004)
    return span


# -- basic storage --

class TestLocalStoreBasic:
    def test_store_span_returns_summary(self, store: LocalStore, sample_span: Span) -> None:
        summary = store.store_span(sample_span)
        assert isinstance(summary, TraceSummary)
        assert summary.name == "test-op"
        assert summary.workspace == "test-ws"
        assert summary.tokens == 1250
        assert summary.cost == 0.004
        assert summary.duration_ms == pytest.approx(142.0, abs=1.0)

    def test_store_span_persists(self, store: LocalStore, sample_span: Span) -> None:
        store.store_span(sample_span)
        traces = store.recent_traces()
        assert len(traces) == 1
        assert traces[0]["name"] == "test-op"
        assert traces[0]["workspace"] == "test-ws"

    def test_store_multiple_spans(self, store: LocalStore) -> None:
        for i in range(5):
            span = Span(name=f"op-{i}", workspace="ws")
            span.start_time = 1000.0
            span.end_time = 1000.0 + i * 0.01
            store.store_span(span)
        traces = store.recent_traces()
        assert len(traces) == 5

    def test_empty_store(self, store: LocalStore) -> None:
        traces = store.recent_traces()
        assert traces == []

    def test_span_with_error(self, store: LocalStore) -> None:
        span = Span(name="fail-op", workspace="ws", status=SpanStatus.ERROR, error="boom")
        span.start_time = 1000.0
        span.end_time = 1000.05
        store.store_span(span)
        traces = store.recent_traces()
        assert traces[0]["status"] == "error"
        assert traces[0]["error"] == "boom"


# -- filtering --

class TestLocalStoreFiltering:
    def test_filter_by_workspace(self, store: LocalStore) -> None:
        for ws in ["alpha", "beta", "alpha"]:
            span = Span(name=f"op-{ws}", workspace=ws)
            span.start_time = 1000.0
            span.end_time = 1000.01
            store.store_span(span)

        alpha = store.recent_traces(workspace="alpha")
        assert len(alpha) == 2
        beta = store.recent_traces(workspace="beta")
        assert len(beta) == 1

    def test_limit(self, store: LocalStore) -> None:
        for i in range(10):
            span = Span(name=f"op-{i}", workspace="ws")
            span.start_time = 1000.0
            span.end_time = 1000.01
            store.store_span(span)

        traces = store.recent_traces(limit=3)
        assert len(traces) == 3


# -- stats --

class TestLocalStoreStats:
    def test_stats_empty(self, store: LocalStore) -> None:
        stats = store.stats()
        assert stats["total_traces"] == 0
        assert stats["avg_latency_ms"] == 0.0

    def test_stats_populated(self, store: LocalStore) -> None:
        for i in range(3):
            span = Span(name=f"op-{i}", workspace="ws")
            span.start_time = 1000.0
            span.end_time = 1000.1 * (i + 1) / 10 + 1000.0  # variable latency
            store.store_span(span)

        stats = store.stats()
        assert stats["total_traces"] == 3
        assert stats["avg_latency_ms"] > 0

    def test_stats_with_workspace_filter(self, store: LocalStore) -> None:
        for ws in ["a", "b"]:
            span = Span(name="op", workspace=ws)
            span.start_time = 1000.0
            span.end_time = 1000.1
            store.store_span(span)

        stats_a = store.stats(workspace="a")
        assert stats_a["total_traces"] == 1


# -- workspaces & clear --

class TestLocalStoreWorkspaces:
    def test_workspaces_list(self, store: LocalStore) -> None:
        for ws in ["beta", "alpha", "gamma"]:
            span = Span(name="op", workspace=ws)
            span.start_time = 1000.0
            span.end_time = 1000.01
            store.store_span(span)

        workspaces = store.workspaces()
        assert workspaces == ["alpha", "beta", "gamma"]  # sorted

    def test_clear_all(self, store: LocalStore) -> None:
        for i in range(3):
            span = Span(name=f"op-{i}", workspace="ws")
            span.start_time = 1000.0
            span.end_time = 1000.01
            store.store_span(span)

        deleted = store.clear()
        assert deleted == 3
        assert store.recent_traces() == []

    def test_clear_by_workspace(self, store: LocalStore) -> None:
        for ws in ["keep", "remove"]:
            span = Span(name="op", workspace=ws)
            span.start_time = 1000.0
            span.end_time = 1000.01
            store.store_span(span)

        deleted = store.clear(workspace="remove")
        assert deleted == 1
        remaining = store.recent_traces()
        assert len(remaining) == 1
        assert remaining[0]["workspace"] == "keep"


# -- TraceSummary --

class TestTraceSummary:
    def test_guard_pass_default(self, store: LocalStore) -> None:
        span = Span(name="op", workspace="ws")
        span.start_time = 1000.0
        span.end_time = 1000.01
        summary = store.store_span(span)
        assert summary.guard_status == "PASS"

    def test_guard_status_from_attribute(self, store: LocalStore) -> None:
        span = Span(name="op", workspace="ws")
        span.start_time = 1000.0
        span.end_time = 1000.01
        span.set_attribute("aegis.guard.status", "BLOCK")
        summary = store.store_span(span)
        assert summary.guard_status == "BLOCK"

    def test_token_counting(self, store: LocalStore) -> None:
        span = Span(name="op", workspace="ws")
        span.start_time = 1000.0
        span.end_time = 1000.01
        span.set_attribute("input_tokens", 100)
        span.set_attribute("output_tokens", 50)
        summary = store.store_span(span)
        assert summary.tokens == 150


# -- thread safety --

class TestLocalStoreThreadSafety:
    def test_concurrent_writes(self, store: LocalStore) -> None:
        import threading

        def write_spans(n: int) -> None:
            for i in range(n):
                span = Span(name=f"thread-op-{i}", workspace="ws")
                span.start_time = 1000.0
                span.end_time = 1000.01
                store.store_span(span)

        threads = [threading.Thread(target=write_spans, args=(10,)) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert store.stats()["total_traces"] == 40
