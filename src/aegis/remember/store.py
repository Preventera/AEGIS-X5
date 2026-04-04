"""Memory stores — ABC + InMemoryStore default implementation."""

from __future__ import annotations

import abc
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryEntry:
    """A single memory record."""

    key: str
    value: Any
    namespace: str = ""
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)
    ttl: float | None = None  # seconds, None = no expiry


class MemoryStore(abc.ABC):
    """Abstract memory store — implement to plug Pinecone/Redis/Neo4j/etc."""

    @abc.abstractmethod
    def get(self, key: str, *, namespace: str = "") -> MemoryEntry | None:
        ...

    @abc.abstractmethod
    def put(self, entry: MemoryEntry) -> None:
        ...

    @abc.abstractmethod
    def delete(self, key: str, *, namespace: str = "") -> bool:
        ...

    @abc.abstractmethod
    def list_keys(self, *, namespace: str = "") -> list[str]:
        ...

    @abc.abstractmethod
    def search(self, query: str, *, namespace: str = "", limit: int = 10) -> list[MemoryEntry]:
        ...

    @abc.abstractmethod
    def clear(self, *, namespace: str | None = None) -> int:
        """Clear entries. If namespace is None, clear all. Return count deleted."""
        ...


class InMemoryStore(MemoryStore):
    """Default in-memory store — no external dependencies."""

    def __init__(self) -> None:
        # (namespace, key) -> MemoryEntry
        self._data: dict[tuple[str, str], MemoryEntry] = {}

    def _is_expired(self, entry: MemoryEntry) -> bool:
        if entry.ttl is None:
            return False
        return (time.time() - entry.created_at) > entry.ttl

    def get(self, key: str, *, namespace: str = "") -> MemoryEntry | None:
        entry = self._data.get((namespace, key))
        if entry is None:
            return None
        if self._is_expired(entry):
            del self._data[(namespace, key)]
            return None
        return entry

    def put(self, entry: MemoryEntry) -> None:
        existing = self._data.get((entry.namespace, entry.key))
        if existing:
            entry.updated_at = time.time()
        self._data[(entry.namespace, entry.key)] = entry

    def delete(self, key: str, *, namespace: str = "") -> bool:
        return self._data.pop((namespace, key), None) is not None

    def list_keys(self, *, namespace: str = "") -> list[str]:
        self._prune_expired()
        return [k for (ns, k) in self._data if ns == namespace]

    def search(self, query: str, *, namespace: str = "", limit: int = 10) -> list[MemoryEntry]:
        """Simple substring search across keys and string values."""
        self._prune_expired()
        q_lower = query.lower()
        results: list[MemoryEntry] = []
        for (ns, key), entry in self._data.items():
            if namespace and ns != namespace:
                continue
            if q_lower in key.lower() or (isinstance(entry.value, str) and q_lower in entry.value.lower()):
                results.append(entry)
                if len(results) >= limit:
                    break
        return results

    def clear(self, *, namespace: str | None = None) -> int:
        if namespace is None:
            count = len(self._data)
            self._data.clear()
            return count
        keys = [(ns, k) for (ns, k) in self._data if ns == namespace]
        for key in keys:
            del self._data[key]
        return len(keys)

    def _prune_expired(self) -> None:
        expired = [k for k, e in self._data.items() if self._is_expired(e)]
        for k in expired:
            del self._data[k]

    @property
    def size(self) -> int:
        return len(self._data)
