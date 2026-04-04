"""aegis.collect — Module Collect.

Ingestion structurée multi-sources avec registre dynamique,
scheduling cron-like et scoring de confiance par source.
"""

from aegis.collect.registry import SourceRegistry
from aegis.collect.scheduler import ScheduledCollector, ScheduledJob
from aegis.collect.sources import CollectedItem, Source, WebSource

__all__ = [
    "CollectedItem",
    "ScheduledCollector",
    "ScheduledJob",
    "Source",
    "SourceRegistry",
    "WebSource",
]
