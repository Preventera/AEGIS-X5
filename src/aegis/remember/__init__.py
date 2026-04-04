"""aegis.remember — Module Remember.

Mémoire persistante avec isolation par agent, audit trail PROV-O,
droit à l'oubli RGPD/Loi 25, et interface plug-in pour stores externes.
"""

from aegis.remember.agent_memory import AgentMemory
from aegis.remember.erasure import ErasureManager, ErasureRequest, ErasureResult
from aegis.remember.provenance import ActivityType, ProvenanceRecord, ProvenanceTracker
from aegis.remember.store import InMemoryStore, MemoryEntry, MemoryStore

__all__ = [
    "ActivityType",
    "AgentMemory",
    "ErasureManager",
    "ErasureRequest",
    "ErasureResult",
    "InMemoryStore",
    "MemoryEntry",
    "MemoryStore",
    "ProvenanceRecord",
    "ProvenanceTracker",
]
