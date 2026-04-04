"""ClosedLoop ABC — universal interface for autonomous feedback loops."""

from __future__ import annotations

import abc
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LoopStatus(str, Enum):
    """Status of a single loop execution cycle."""

    IDLE = "idle"
    DETECTED = "detected"
    CORRECTING = "correcting"
    VALIDATING = "validating"
    LEARNING = "learning"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"  # semi-auto: human rejected


@dataclass
class LoopResult:
    """Outcome of one full detect → correct → validate → learn cycle."""

    loop_name: str
    cycle_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: LoopStatus = LoopStatus.IDLE
    detected: dict[str, Any] = field(default_factory=dict)
    correction: dict[str, Any] = field(default_factory=dict)
    validated: bool = False
    learned: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    started_at: float = field(default_factory=time.time)
    finished_at: float = 0.0

    @property
    def duration_ms(self) -> float:
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at) * 1000
        return 0.0


class ClosedLoop(abc.ABC):
    """Abstract closed-loop controller.

    Subclasses implement the four phases:

    1. :meth:`detect` — diagnose a problem from current state
    2. :meth:`correct` — apply a fix
    3. :meth:`validate` — verify the fix worked
    4. :meth:`learn` — update thresholds / patterns for next time

    The :meth:`run` method orchestrates the full cycle.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self._history: list[LoopResult] = []

    @abc.abstractmethod
    def detect(self, **context: Any) -> dict[str, Any] | None:
        """Return diagnostic info if a problem is detected, else None."""
        ...

    @abc.abstractmethod
    def correct(self, diagnosis: dict[str, Any], **context: Any) -> dict[str, Any]:
        """Apply correction based on *diagnosis*. Return correction details."""
        ...

    @abc.abstractmethod
    def validate(self, correction: dict[str, Any], **context: Any) -> bool:
        """Return True if the correction resolved the problem."""
        ...

    @abc.abstractmethod
    def learn(self, result: LoopResult, **context: Any) -> dict[str, Any]:
        """Update internal state based on the cycle outcome. Return learned info."""
        ...

    def run(self, **context: Any) -> LoopResult:
        """Execute a full detect → correct → validate → learn cycle."""
        result = LoopResult(loop_name=self.name)

        # 1 — Detect
        try:
            diagnosis = self.detect(**context)
        except Exception as exc:
            result.status = LoopStatus.FAILED
            result.error = f"detect failed: {exc}"
            result.finished_at = time.time()
            self._history.append(result)
            return result

        if diagnosis is None:
            result.status = LoopStatus.IDLE
            result.finished_at = time.time()
            self._history.append(result)
            return result

        result.detected = diagnosis
        result.status = LoopStatus.DETECTED

        # 2 — Correct
        try:
            result.status = LoopStatus.CORRECTING
            correction = self.correct(diagnosis, **context)
            result.correction = correction
        except Exception as exc:
            result.status = LoopStatus.FAILED
            result.error = f"correct failed: {exc}"
            result.finished_at = time.time()
            self._history.append(result)
            return result

        # 3 — Validate
        try:
            result.status = LoopStatus.VALIDATING
            result.validated = self.validate(correction, **context)
        except Exception as exc:
            result.status = LoopStatus.FAILED
            result.error = f"validate failed: {exc}"
            result.finished_at = time.time()
            self._history.append(result)
            return result

        # 4 — Learn
        try:
            result.status = LoopStatus.LEARNING
            result.learned = self.learn(result, **context)
        except Exception as exc:
            result.status = LoopStatus.FAILED
            result.error = f"learn failed: {exc}"
            result.finished_at = time.time()
            self._history.append(result)
            return result

        result.status = LoopStatus.SUCCESS if result.validated else LoopStatus.FAILED
        result.finished_at = time.time()
        self._history.append(result)
        return result

    @property
    def history(self) -> list[LoopResult]:
        return list(self._history)
