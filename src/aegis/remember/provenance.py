"""ProvenanceTracker — PROV-O inspired audit trail for memory operations."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ActivityType(str, Enum):
    """PROV-O activity types for memory operations."""

    CREATE = "prov:Generation"
    READ = "prov:Usage"
    UPDATE = "prov:Revision"
    DELETE = "prov:Invalidation"
    ERASURE = "prov:Erasure"  # GDPR/Loi 25 specific


@dataclass(frozen=True)
class ProvenanceRecord:
    """PROV-O style audit record for a single memory operation."""

    record_id: str
    activity: ActivityType
    entity_key: str
    namespace: str = ""
    agent_id: str = ""
    timestamp: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            object.__setattr__(self, "timestamp", time.time())

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "activity": self.activity.value,
            "entity_key": self.entity_key,
            "namespace": self.namespace,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
            "attributes": self.attributes,
        }


class ProvenanceTracker:
    """Tracks all memory operations with PROV-O audit trail.

    Usage::

        tracker = ProvenanceTracker()
        tracker.record(ActivityType.CREATE, "user_name", namespace="agent-1")
        trail = tracker.trail(entity_key="user_name")
    """

    def __init__(self) -> None:
        self._records: list[ProvenanceRecord] = []

    def record(
        self,
        activity: ActivityType,
        entity_key: str,
        *,
        namespace: str = "",
        agent_id: str = "",
        **attributes: Any,
    ) -> ProvenanceRecord:
        """Record a provenance event."""
        rec = ProvenanceRecord(
            record_id=uuid.uuid4().hex[:16],
            activity=activity,
            entity_key=entity_key,
            namespace=namespace,
            agent_id=agent_id,
            attributes=dict(attributes),
        )
        self._records.append(rec)
        return rec

    def trail(
        self,
        *,
        entity_key: str | None = None,
        namespace: str | None = None,
        agent_id: str | None = None,
        activity: ActivityType | None = None,
    ) -> list[ProvenanceRecord]:
        """Query the audit trail with optional filters."""
        results = self._records
        if entity_key is not None:
            results = [r for r in results if r.entity_key == entity_key]
        if namespace is not None:
            results = [r for r in results if r.namespace == namespace]
        if agent_id is not None:
            results = [r for r in results if r.agent_id == agent_id]
        if activity is not None:
            results = [r for r in results if r.activity == activity]
        return results

    @property
    def all_records(self) -> list[ProvenanceRecord]:
        return list(self._records)

    def clear(self) -> None:
        self._records.clear()
