"""ScheduledCollector — cron-like polling of sources."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from aegis.collect.sources import CollectedItem, Source


@dataclass
class ScheduledJob:
    """A registered polling job."""

    name: str
    source: Source
    query: str
    interval_seconds: float
    callback: Callable[[list[CollectedItem]], None] | None = None
    last_run: float = 0.0
    run_count: int = 0


class ScheduledCollector:
    """Cron-like collector that polls sources at configurable intervals.

    Usage::

        collector = ScheduledCollector()
        collector.add_job("news", web_source, "AI governance", interval_seconds=3600)
        collector.tick()  # manually trigger due jobs
    """

    def __init__(self) -> None:
        self._jobs: dict[str, ScheduledJob] = {}
        self._collected: list[CollectedItem] = []
        self._lock = threading.Lock()

    @property
    def jobs(self) -> dict[str, ScheduledJob]:
        return dict(self._jobs)

    @property
    def collected(self) -> list[CollectedItem]:
        with self._lock:
            return list(self._collected)

    def add_job(
        self,
        name: str,
        source: Source,
        query: str,
        *,
        interval_seconds: float = 3600,
        callback: Callable[[list[CollectedItem]], None] | None = None,
    ) -> ScheduledCollector:
        """Register a polling job. Returns self."""
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self._jobs[name] = ScheduledJob(
            name=name,
            source=source,
            query=query,
            interval_seconds=interval_seconds,
            callback=callback,
        )
        return self

    def remove_job(self, name: str) -> ScheduledCollector:
        self._jobs.pop(name, None)
        return self

    def tick(self, *, now: float | None = None) -> list[CollectedItem]:
        """Check all jobs and run those that are due. Returns newly collected items."""
        current = now or time.time()
        new_items: list[CollectedItem] = []

        for job in self._jobs.values():
            elapsed = current - job.last_run
            if elapsed >= job.interval_seconds:
                items = job.source.collect(job.query)
                job.last_run = current
                job.run_count += 1
                new_items.extend(items)
                if job.callback:
                    job.callback(items)

        with self._lock:
            self._collected.extend(new_items)
        return new_items

    def clear(self) -> None:
        with self._lock:
            self._collected.clear()
