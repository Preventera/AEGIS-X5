"""Tests for aegis.remember.erasure — GDPR/Loi 25 right-to-erasure."""

from __future__ import annotations

from aegis.remember.erasure import ErasureManager, ErasureRequest
from aegis.remember.provenance import ActivityType, ProvenanceTracker
from aegis.remember.store import InMemoryStore, MemoryEntry


class TestErasureManager:
    def _setup(self):
        store = InMemoryStore()
        tracker = ProvenanceTracker()
        manager = ErasureManager(store=store, tracker=tracker)
        return store, tracker, manager

    def test_erase_by_key(self):
        store, tracker, manager = self._setup()
        store.put(MemoryEntry(key="user-42-name", value="Alice"))
        store.put(MemoryEntry(key="other", value="keep"))

        req = ErasureRequest(request_id="req-1", subject_id="user-42")
        result = manager.erase(req, namespaces=[""])
        assert len(result.keys_deleted) == 1
        assert "user-42-name" in result.keys_deleted
        assert store.get("other") is not None
        assert result.success

    def test_erase_by_value(self):
        store, tracker, manager = self._setup()
        store.put(MemoryEntry(key="data", value="belongs to user-42"))
        store.put(MemoryEntry(key="safe", value="no match"))

        result = manager.erase(
            ErasureRequest(request_id="r2", subject_id="user-42"),
            namespaces=[""],
        )
        assert "data" in result.keys_deleted
        assert "safe" not in result.keys_deleted

    def test_erase_dict_value(self):
        store, tracker, manager = self._setup()
        store.put(MemoryEntry(key="profile", value={"name": "User-42 Data"}))

        result = manager.erase(
            ErasureRequest(request_id="r3", subject_id="user-42"),
            namespaces=[""],
        )
        assert "profile" in result.keys_deleted

    def test_audit_trail(self):
        store, tracker, manager = self._setup()
        store.put(MemoryEntry(key="user-42-k", value="x"))

        manager.erase(
            ErasureRequest(request_id="r1", subject_id="user-42", reason="GDPR request"),
            namespaces=[""],
        )

        trail = tracker.trail(activity=ActivityType.ERASURE)
        assert len(trail) == 1
        assert trail[0].attributes["reason"] == "GDPR request"
        assert trail[0].attributes["subject_id"] == "user-42"

    def test_multi_namespace(self):
        store, _, manager = self._setup()
        store.put(MemoryEntry(key="user-42-a", value="x", namespace="ns1"))
        store.put(MemoryEntry(key="user-42-b", value="y", namespace="ns2"))
        store.put(MemoryEntry(key="other", value="z", namespace="ns1"))

        result = manager.erase(
            ErasureRequest(request_id="r", subject_id="user-42"),
            namespaces=["ns1", "ns2"],
        )
        assert len(result.keys_deleted) == 2
        assert set(result.namespaces_affected) == {"ns1", "ns2"}

    def test_no_match(self):
        store, _, manager = self._setup()
        store.put(MemoryEntry(key="safe", value="data"))

        result = manager.erase(
            ErasureRequest(request_id="r", subject_id="user-99"),
            namespaces=[""],
        )
        assert len(result.keys_deleted) == 0
        assert result.success

    def test_history(self):
        _, _, manager = self._setup()
        manager.erase(
            ErasureRequest(request_id="r1", subject_id="a"),
            namespaces=[""],
        )
        manager.erase(
            ErasureRequest(request_id="r2", subject_id="b"),
            namespaces=[""],
        )
        assert len(manager.history) == 2

    def test_erasure_request_fields(self):
        req = ErasureRequest(request_id="r1", subject_id="u42", reason="GDPR Art.17")
        assert req.request_id == "r1"
        assert req.reason == "GDPR Art.17"
        assert req.requested_at > 0

    def test_case_insensitive_match(self):
        store, _, manager = self._setup()
        store.put(MemoryEntry(key="data", value="USER-42 info"))

        result = manager.erase(
            ErasureRequest(request_id="r", subject_id="user-42"),
            namespaces=[""],
        )
        assert "data" in result.keys_deleted
