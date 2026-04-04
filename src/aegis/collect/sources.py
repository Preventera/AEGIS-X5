"""Data sources — ABC, WebSource, confidence scoring."""

from __future__ import annotations

import abc
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CollectedItem:
    """A single item retrieved from a source."""

    content: str
    source_name: str
    confidence: float = 1.0  # 0.0–1.0
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0–1.0, got {self.confidence}")
        if self.timestamp == 0.0:
            object.__setattr__(self, "timestamp", time.time())


class Source(abc.ABC):
    """Abstract data source — implement :meth:`collect` to create plug-in sources.

    Each source has a ``name`` and a default ``confidence`` (0.0–1.0).
    """

    def __init__(self, name: str, *, confidence: float = 1.0, domain: str = "") -> None:
        self.name = name
        self.confidence = confidence
        self.domain = domain

    @abc.abstractmethod
    def collect(self, query: str, **kwargs: Any) -> list[CollectedItem]:
        """Retrieve items matching *query*."""
        ...


# ---------------------------------------------------------------------------
# Built-in: WebSource (abstraction — no Tavily/Serper dependency)
# ---------------------------------------------------------------------------


class WebSource(Source):
    """Structured web search source (abstraction layer).

    Accepts a ``search_fn`` callable to decouple from any specific API::

        def my_search(query: str, **kw) -> list[dict]:
            return [{"content": "...", "url": "..."}]

        web = WebSource(search_fn=my_search)
        items = web.collect("AI governance")
    """

    def __init__(
        self,
        *,
        search_fn: Any | None = None,
        confidence: float = 0.7,
        max_results: int = 5,
    ) -> None:
        super().__init__("web", confidence=confidence, domain="web")
        self._search_fn = search_fn
        self._max_results = max_results

    def collect(self, query: str, **kwargs: Any) -> list[CollectedItem]:
        if self._search_fn is None:
            return []
        max_results = kwargs.get("max_results", self._max_results)
        raw = self._search_fn(query, max_results=max_results)
        items: list[CollectedItem] = []
        for entry in raw:
            if isinstance(entry, dict):
                content = entry.get("content", entry.get("snippet", ""))
                meta = {k: v for k, v in entry.items() if k not in ("content", "snippet")}
            else:
                content = str(entry)
                meta = {}
            items.append(CollectedItem(
                content=content,
                source_name=self.name,
                confidence=self.confidence,
                metadata=meta,
            ))
        return items[:max_results]
