"""Tests for aegis.remember.store — MemoryStore ABC + InMemoryStore."""

from __future__ import annotations

import time

import pytest

from aegis.remember.store import InMemoryStore, MemoryEntry, MemoryStore


class TestMemoryStoreABC:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            MemoryStore()  # type: ignore[abstract]


class TestMemoryEntry:
    def test_basic(self):
        e = MemoryEntry(key="k", value="v")
        assert e.key == "k"
        assert e.value == "v"
        assert len(e.entry_id) == 16
        assert e.created_at > 0


class TestInMemoryStore:
    def test_put_and_get(self):
        store = InMemoryStore()
        entry = MemoryEntry(key="name", value="Alice")
        store.put(entry)
        result = store.get("name")
        assert result is not None
        assert result.value == "Alice"

    def test_get_missing(self):
        store = InMemoryStore()
        assert store.get("missing") is None

    def test_delete(self):
        store = InMemoryStore()
        store.put(MemoryEntry(key="k", value="v"))
        assert store.delete("k")
        assert store.get("k") is None

    def test_delete_missing(self):
        store = InMemoryStore()
        assert not store.delete("nope")

    def test_list_keys(self):
        store = InMemoryStore()
        store.put(MemoryEntry(key="a", value=1))
        store.put(MemoryEntry(key="b", value=2))
        keys = store.list_keys()
        assert sorted(keys) == ["a", "b"]

    def test_namespace_isolation(self):
        store = InMemoryStore()
        store.put(MemoryEntry(key="k", value="ns1", namespace="agent-1"))
        store.put(MemoryEntry(key="k", value="ns2", namespace="agent-2"))
        assert store.get("k", namespace="agent-1").value == "ns1"
        assert store.get("k", namespace="agent-2").value == "ns2"

    def test_list_keys_by_namespace(self):
        store = InMemoryStore()
        store.put(MemoryEntry(key="a", value=1, namespace="ns1"))
        store.put(MemoryEntry(key="b", value=2, namespace="ns2"))
        assert store.list_keys(namespace="ns1") == ["a"]

    def test_search_by_key(self):
        store = InMemoryStore()
        store.put(MemoryEntry(key="user_name", value="Alice"))
        store.put(MemoryEntry(key="user_age", value=30))
        results = store.search("user")
        assert len(results) == 2

    def test_search_by_value(self):
        store = InMemoryStore()
        store.put(MemoryEntry(key="data", value="Machine learning is great"))
        results = store.search("machine")
        assert len(results) == 1

    def test_search_limit(self):
        store = InMemoryStore()
        for i in range(20):
            store.put(MemoryEntry(key=f"item_{i}", value=f"data_{i}"))
        results = store.search("item", limit=5)
        assert len(results) == 5

    def test_search_by_namespace(self):
        store = InMemoryStore()
        store.put(MemoryEntry(key="data", value="hello", namespace="ns1"))
        store.put(MemoryEntry(key="data2", value="hello", namespace="ns2"))
        results = store.search("hello", namespace="ns1")
        assert len(results) == 1

    def test_clear_all(self):
        store = InMemoryStore()
        store.put(MemoryEntry(key="a", value=1, namespace="ns1"))
        store.put(MemoryEntry(key="b", value=2, namespace="ns2"))
        count = store.clear()
        assert count == 2
        assert store.size == 0

    def test_clear_by_namespace(self):
        store = InMemoryStore()
        store.put(MemoryEntry(key="a", value=1, namespace="ns1"))
        store.put(MemoryEntry(key="b", value=2, namespace="ns2"))
        count = store.clear(namespace="ns1")
        assert count == 1
        assert store.size == 1

    def test_ttl_expiry(self):
        store = InMemoryStore()
        entry = MemoryEntry(key="temp", value="data", ttl=0.001)
        entry.created_at = time.time() - 1  # already expired
        store.put(entry)
        assert store.get("temp") is None

    def test_ttl_not_expired(self):
        store = InMemoryStore()
        entry = MemoryEntry(key="temp", value="data", ttl=3600)
        store.put(entry)
        assert store.get("temp") is not None

    def test_update_existing(self):
        store = InMemoryStore()
        store.put(MemoryEntry(key="k", value="old"))
        store.put(MemoryEntry(key="k", value="new"))
        assert store.get("k").value == "new"

    def test_size(self):
        store = InMemoryStore()
        assert store.size == 0
        store.put(MemoryEntry(key="a", value=1))
        assert store.size == 1
