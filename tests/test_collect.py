"""Tests for aegis.collect — sources, registry, scheduler."""

from __future__ import annotations

import time

import pytest

from aegis.collect.registry import SourceRegistry
from aegis.collect.scheduler import ScheduledCollector
from aegis.collect.sources import CollectedItem, Source, WebSource


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class MockSource(Source):
    def __init__(self, name="mock", items=None, **kw):
        super().__init__(name, **kw)
        self._items = items or []

    def collect(self, query, **kwargs):
        return [
            CollectedItem(content=f"{query}:{item}", source_name=self.name, confidence=self.confidence)
            for item in self._items
        ]


# ---------------------------------------------------------------------------
# CollectedItem
# ---------------------------------------------------------------------------


class TestCollectedItem:
    def test_basic(self):
        item = CollectedItem(content="hello", source_name="test")
        assert item.content == "hello"
        assert item.confidence == 1.0
        assert item.timestamp > 0

    def test_invalid_confidence(self):
        with pytest.raises(ValueError, match="confidence"):
            CollectedItem(content="x", source_name="y", confidence=1.5)

    def test_negative_confidence(self):
        with pytest.raises(ValueError, match="confidence"):
            CollectedItem(content="x", source_name="y", confidence=-0.1)

    def test_custom_metadata(self):
        item = CollectedItem(content="x", source_name="y", metadata={"url": "http://example.com"})
        assert item.metadata["url"] == "http://example.com"


# ---------------------------------------------------------------------------
# Source ABC
# ---------------------------------------------------------------------------


class TestSourceABC:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            Source("test")  # type: ignore[abstract]

    def test_mock_source(self):
        s = MockSource("s1", items=["a", "b"], confidence=0.8, domain="test")
        items = s.collect("q")
        assert len(items) == 2
        assert items[0].confidence == 0.8
        assert "q:a" == items[0].content


# ---------------------------------------------------------------------------
# WebSource
# ---------------------------------------------------------------------------


class TestWebSource:
    def test_no_search_fn(self):
        ws = WebSource()
        assert ws.collect("anything") == []

    def test_with_search_fn(self):
        def fake_search(query, max_results=5):
            return [{"content": f"result for {query}", "url": "http://x.com"}]

        ws = WebSource(search_fn=fake_search)
        items = ws.collect("AI governance")
        assert len(items) == 1
        assert "AI governance" in items[0].content
        assert items[0].metadata["url"] == "http://x.com"

    def test_max_results(self):
        def fake_search(query, max_results=5):
            return [{"content": f"r{i}"} for i in range(10)]

        ws = WebSource(search_fn=fake_search, max_results=3)
        items = ws.collect("test")
        assert len(items) == 3

    def test_string_items(self):
        def fake_search(query, max_results=5):
            return ["result1", "result2"]

        ws = WebSource(search_fn=fake_search)
        items = ws.collect("q")
        assert items[0].content == "result1"

    def test_default_confidence(self):
        ws = WebSource()
        assert ws.confidence == 0.7


# ---------------------------------------------------------------------------
# SourceRegistry
# ---------------------------------------------------------------------------


class TestSourceRegistry:
    def test_register_and_get(self):
        reg = SourceRegistry()
        s = MockSource("s1", domain="test")
        reg.register(s)
        assert reg.get("s1") is s

    def test_unregister(self):
        reg = SourceRegistry()
        reg.register(MockSource("s1"))
        reg.unregister("s1")
        assert reg.get("s1") is None

    def test_list_domains(self):
        reg = SourceRegistry()
        reg.register(MockSource("a", domain="web"))
        reg.register(MockSource("b", domain="db"))
        reg.register(MockSource("c", domain="web"))
        assert sorted(reg.list_domains()) == ["db", "web"]

    def test_collect_all(self):
        reg = SourceRegistry()
        reg.register(MockSource("s1", items=["a"]))
        reg.register(MockSource("s2", items=["b"]))
        items = reg.collect_all("q")
        assert len(items) == 2

    def test_collect_by_domain(self):
        reg = SourceRegistry()
        reg.register(MockSource("web1", items=["w"], domain="web"))
        reg.register(MockSource("db1", items=["d"], domain="db"))
        items = reg.collect_by_domain("web", "q")
        assert len(items) == 1
        assert "w" in items[0].content

    def test_chaining(self):
        reg = SourceRegistry().register(MockSource("a")).register(MockSource("b"))
        assert len(reg.sources) == 2

    def test_overwrite(self):
        reg = SourceRegistry()
        reg.register(MockSource("s1", items=["old"]))
        reg.register(MockSource("s1", items=["new"]))
        items = reg.collect_all("q")
        assert len(items) == 1
        assert "new" in items[0].content


# ---------------------------------------------------------------------------
# ScheduledCollector
# ---------------------------------------------------------------------------


class TestScheduledCollector:
    def test_add_and_tick(self):
        sc = ScheduledCollector()
        sc.add_job("j1", MockSource("s", items=["data"]), "q", interval_seconds=60)
        items = sc.tick()
        assert len(items) == 1

    def test_not_due_yet(self):
        sc = ScheduledCollector()
        now = time.time()
        sc.add_job("j1", MockSource("s", items=["x"]), "q", interval_seconds=3600)
        sc.tick(now=now)  # first run
        items = sc.tick(now=now + 10)  # 10s later — not due
        assert len(items) == 0

    def test_due_again(self):
        sc = ScheduledCollector()
        now = time.time()
        sc.add_job("j1", MockSource("s", items=["x"]), "q", interval_seconds=60)
        sc.tick(now=now)
        items = sc.tick(now=now + 61)  # 61s later — due
        assert len(items) == 1

    def test_callback(self):
        received = []
        sc = ScheduledCollector()
        sc.add_job("j1", MockSource("s", items=["x"]), "q", interval_seconds=1, callback=received.extend)
        sc.tick()
        assert len(received) == 1

    def test_remove_job(self):
        sc = ScheduledCollector()
        sc.add_job("j1", MockSource("s", items=["x"]), "q", interval_seconds=1)
        sc.remove_job("j1")
        items = sc.tick()
        assert len(items) == 0

    def test_collected_property(self):
        sc = ScheduledCollector()
        sc.add_job("j1", MockSource("s", items=["a", "b"]), "q", interval_seconds=1)
        sc.tick()
        assert len(sc.collected) == 2

    def test_clear(self):
        sc = ScheduledCollector()
        sc.add_job("j1", MockSource("s", items=["a"]), "q", interval_seconds=1)
        sc.tick()
        sc.clear()
        assert len(sc.collected) == 0

    def test_invalid_interval(self):
        sc = ScheduledCollector()
        with pytest.raises(ValueError, match="positive"):
            sc.add_job("j", MockSource("s"), "q", interval_seconds=0)

    def test_run_count(self):
        sc = ScheduledCollector()
        now = time.time()
        sc.add_job("j1", MockSource("s", items=["x"]), "q", interval_seconds=10)
        sc.tick(now=now)
        sc.tick(now=now + 11)
        sc.tick(now=now + 22)
        assert sc.jobs["j1"].run_count == 3
