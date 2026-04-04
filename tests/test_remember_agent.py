"""Tests for aegis.remember.agent_memory — per-agent namespace isolation."""

from __future__ import annotations

from aegis.remember.agent_memory import AgentMemory
from aegis.remember.store import InMemoryStore


class TestAgentMemory:
    def test_remember_and_recall(self):
        mem = AgentMemory("agent-1")
        mem.remember("name", "Alice")
        assert mem.recall("name") == "Alice"

    def test_recall_missing(self):
        mem = AgentMemory("agent-1")
        assert mem.recall("nope") is None

    def test_forget(self):
        mem = AgentMemory("agent-1")
        mem.remember("k", "v")
        assert mem.forget("k")
        assert mem.recall("k") is None

    def test_forget_missing(self):
        mem = AgentMemory("agent-1")
        assert not mem.forget("nope")

    def test_isolation(self):
        store = InMemoryStore()
        m1 = AgentMemory("agent-1", store=store)
        m2 = AgentMemory("agent-2", store=store)
        m1.remember("color", "red")
        m2.remember("color", "blue")
        assert m1.recall("color") == "red"
        assert m2.recall("color") == "blue"

    def test_list_keys(self):
        mem = AgentMemory("agent-1")
        mem.remember("a", 1)
        mem.remember("b", 2)
        assert sorted(mem.list_keys()) == ["a", "b"]

    def test_search(self):
        mem = AgentMemory("agent-1")
        mem.remember("greeting", "hello world")
        mem.remember("farewell", "goodbye")
        results = mem.search("hello")
        assert len(results) == 1

    def test_clear(self):
        store = InMemoryStore()
        m1 = AgentMemory("agent-1", store=store)
        m2 = AgentMemory("agent-2", store=store)
        m1.remember("a", 1)
        m2.remember("b", 2)
        count = m1.clear()
        assert count == 1
        assert m1.recall("a") is None
        assert m2.recall("b") == 2  # agent-2 untouched

    def test_metadata(self):
        mem = AgentMemory("agent-1")
        entry = mem.remember("k", "v", metadata={"source": "user"})
        assert entry.metadata["source"] == "user"

    def test_ttl(self):
        mem = AgentMemory("agent-1")
        entry = mem.remember("temp", "data", ttl=3600)
        assert entry.ttl == 3600

    def test_shared_store(self):
        store = InMemoryStore()
        m = AgentMemory("a1", store=store)
        assert m.store is store
