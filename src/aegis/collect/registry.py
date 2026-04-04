"""SourceRegistry — dynamic registration and lookup of sources by domain."""

from __future__ import annotations

from typing import Any

from aegis.collect.sources import CollectedItem, Source


class SourceRegistry:
    """Registry for dynamically managing data sources by domain.

    Usage::

        registry = SourceRegistry()
        registry.register(my_web_source)
        registry.register(my_db_source)

        # Query all sources
        items = registry.collect_all("AI governance")

        # Query by domain
        items = registry.collect_by_domain("web", "AI governance")
    """

    def __init__(self) -> None:
        self._sources: dict[str, Source] = {}

    @property
    def sources(self) -> dict[str, Source]:
        return dict(self._sources)

    def register(self, source: Source) -> SourceRegistry:
        """Register a source. Overwrites if same name exists. Returns self."""
        self._sources[source.name] = source
        return self

    def unregister(self, name: str) -> SourceRegistry:
        """Remove a source by name. Returns self."""
        self._sources.pop(name, None)
        return self

    def get(self, name: str) -> Source | None:
        return self._sources.get(name)

    def list_domains(self) -> list[str]:
        return sorted({s.domain for s in self._sources.values() if s.domain})

    def collect_all(self, query: str, **kwargs: Any) -> list[CollectedItem]:
        """Query all registered sources and merge results."""
        items: list[CollectedItem] = []
        for source in self._sources.values():
            items.extend(source.collect(query, **kwargs))
        return items

    def collect_by_domain(self, domain: str, query: str, **kwargs: Any) -> list[CollectedItem]:
        """Query only sources matching *domain*."""
        items: list[CollectedItem] = []
        for source in self._sources.values():
            if source.domain == domain:
                items.extend(source.collect(query, **kwargs))
        return items
