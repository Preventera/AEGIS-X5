"""AgentMemory — namespace-isolated memory per agent."""

from __future__ import annotations

from typing import Any

from aegis.remember.store import InMemoryStore, MemoryEntry, MemoryStore


class AgentMemory:
    """Per-agent memory with namespace isolation.

    Usage::

        store = InMemoryStore()
        mem = AgentMemory("agent-1", store=store)
        mem.remember("user_name", "Alice")
        mem.recall("user_name")  # → "Alice"
    """

    def __init__(self, agent_id: str, *, store: MemoryStore | None = None) -> None:
        self.agent_id = agent_id
        self._store = store or InMemoryStore()

    @property
    def store(self) -> MemoryStore:
        return self._store

    def remember(self, key: str, value: Any, *, metadata: dict[str, Any] | None = None, ttl: float | None = None) -> MemoryEntry:
        """Store a value under *key* in this agent's namespace."""
        entry = MemoryEntry(
            key=key,
            value=value,
            namespace=self.agent_id,
            metadata=metadata or {},
            ttl=ttl,
        )
        self._store.put(entry)
        return entry

    def recall(self, key: str) -> Any | None:
        """Retrieve a value by key, or None if not found."""
        entry = self._store.get(key, namespace=self.agent_id)
        return entry.value if entry else None

    def forget(self, key: str) -> bool:
        """Delete a key from this agent's memory."""
        return self._store.delete(key, namespace=self.agent_id)

    def search(self, query: str, *, limit: int = 10) -> list[MemoryEntry]:
        """Search this agent's memory."""
        return self._store.search(query, namespace=self.agent_id, limit=limit)

    def list_keys(self) -> list[str]:
        return self._store.list_keys(namespace=self.agent_id)

    def clear(self) -> int:
        """Clear all memory for this agent."""
        return self._store.clear(namespace=self.agent_id)
