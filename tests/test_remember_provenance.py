"""Tests for aegis.remember.provenance — PROV-O audit trail."""

from __future__ import annotations

from aegis.remember.provenance import ActivityType, ProvenanceRecord, ProvenanceTracker


class TestProvenanceRecord:
    def test_basic(self):
        r = ProvenanceRecord(record_id="r1", activity=ActivityType.CREATE, entity_key="k")
        assert r.record_id == "r1"
        assert r.activity == ActivityType.CREATE
        assert r.timestamp > 0

    def test_to_dict(self):
        r = ProvenanceRecord(record_id="r1", activity=ActivityType.READ, entity_key="k")
        d = r.to_dict()
        assert d["activity"] == "prov:Usage"
        assert d["entity_key"] == "k"


class TestActivityType:
    def test_values(self):
        assert ActivityType.CREATE.value == "prov:Generation"
        assert ActivityType.READ.value == "prov:Usage"
        assert ActivityType.UPDATE.value == "prov:Revision"
        assert ActivityType.DELETE.value == "prov:Invalidation"
        assert ActivityType.ERASURE.value == "prov:Erasure"


class TestProvenanceTracker:
    def test_record_and_trail(self):
        t = ProvenanceTracker()
        t.record(ActivityType.CREATE, "user_name", namespace="agent-1")
        trail = t.trail(entity_key="user_name")
        assert len(trail) == 1
        assert trail[0].entity_key == "user_name"

    def test_filter_by_namespace(self):
        t = ProvenanceTracker()
        t.record(ActivityType.CREATE, "k", namespace="ns1")
        t.record(ActivityType.CREATE, "k", namespace="ns2")
        assert len(t.trail(namespace="ns1")) == 1

    def test_filter_by_activity(self):
        t = ProvenanceTracker()
        t.record(ActivityType.CREATE, "k")
        t.record(ActivityType.READ, "k")
        t.record(ActivityType.DELETE, "k")
        assert len(t.trail(activity=ActivityType.READ)) == 1

    def test_filter_by_agent_id(self):
        t = ProvenanceTracker()
        t.record(ActivityType.CREATE, "k", agent_id="a1")
        t.record(ActivityType.CREATE, "k", agent_id="a2")
        assert len(t.trail(agent_id="a1")) == 1

    def test_all_records(self):
        t = ProvenanceTracker()
        t.record(ActivityType.CREATE, "a")
        t.record(ActivityType.READ, "b")
        assert len(t.all_records) == 2

    def test_clear(self):
        t = ProvenanceTracker()
        t.record(ActivityType.CREATE, "k")
        t.clear()
        assert len(t.all_records) == 0

    def test_attributes(self):
        t = ProvenanceTracker()
        rec = t.record(ActivityType.UPDATE, "k", source="api", version=2)
        assert rec.attributes["source"] == "api"
        assert rec.attributes["version"] == 2

    def test_combined_filters(self):
        t = ProvenanceTracker()
        t.record(ActivityType.CREATE, "k1", namespace="ns1", agent_id="a1")
        t.record(ActivityType.CREATE, "k2", namespace="ns1", agent_id="a2")
        t.record(ActivityType.READ, "k1", namespace="ns1", agent_id="a1")
        results = t.trail(namespace="ns1", agent_id="a1", activity=ActivityType.CREATE)
        assert len(results) == 1
        assert results[0].entity_key == "k1"
