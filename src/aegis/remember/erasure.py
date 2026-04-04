"""ErasureManager — GDPR / Loi 25 right-to-erasure compliance."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from aegis.remember.provenance import ActivityType, ProvenanceTracker
from aegis.remember.store import MemoryStore


@dataclass(frozen=True)
class ErasureRequest:
    """A formal erasure request."""

    request_id: str
    subject_id: str
    reason: str = ""
    requested_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ErasureResult:
    """Result of executing an erasure request."""

    request: ErasureRequest
    keys_deleted: tuple[str, ...]
    namespaces_affected: tuple[str, ...]
    completed_at: float = field(default_factory=time.time)
    success: bool = True


class ErasureManager:
    """Manages right-to-erasure (GDPR Art.17, Loi 25) for memory stores.

    Usage::

        manager = ErasureManager(store=my_store, tracker=my_tracker)
        result = manager.erase(
            ErasureRequest(request_id="req-1", subject_id="user-42")
        )
    """

    def __init__(
        self,
        *,
        store: MemoryStore,
        tracker: ProvenanceTracker | None = None,
    ) -> None:
        self._store = store
        self._tracker = tracker or ProvenanceTracker()
        self._history: list[ErasureResult] = []

    @property
    def tracker(self) -> ProvenanceTracker:
        return self._tracker

    @property
    def history(self) -> list[ErasureResult]:
        return list(self._history)

    def erase(
        self,
        request: ErasureRequest,
        *,
        namespaces: list[str] | None = None,
    ) -> ErasureResult:
        """Execute an erasure request across specified namespaces.

        If *namespaces* is None, erases from all namespaces that contain
        the subject_id as a key.

        Every deletion is logged to the provenance tracker with
        :attr:`ActivityType.ERASURE`.
        """
        deleted_keys: list[str] = []
        affected_ns: set[str] = set()
        search_ns = namespaces or [""]

        for ns in search_ns:
            keys = self._store.list_keys(namespace=ns)
            for key in keys:
                entry = self._store.get(key, namespace=ns)
                if entry is None:
                    continue
                # Match: key contains subject_id, or value contains subject_id
                if self._matches_subject(entry.key, entry.value, request.subject_id):
                    self._store.delete(key, namespace=ns)
                    deleted_keys.append(key)
                    affected_ns.add(ns)
                    self._tracker.record(
                        ActivityType.ERASURE,
                        key,
                        namespace=ns,
                        reason=request.reason,
                        request_id=request.request_id,
                        subject_id=request.subject_id,
                    )

        result = ErasureResult(
            request=request,
            keys_deleted=tuple(deleted_keys),
            namespaces_affected=tuple(sorted(affected_ns)),
        )
        self._history.append(result)
        return result

    def _matches_subject(self, key: str, value: Any, subject_id: str) -> bool:
        """Check if a memory entry relates to the subject."""
        sid = subject_id.lower()
        if sid in key.lower():
            return True
        if isinstance(value, str) and sid in value.lower():
            return True
        if isinstance(value, dict):
            for v in value.values():
                if isinstance(v, str) and sid in v.lower():
                    return True
        return False
