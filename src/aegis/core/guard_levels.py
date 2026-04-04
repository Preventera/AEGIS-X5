"""Guard levels N1–N4 for output protection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Any


class GuardLevel(IntEnum):
    """Severity levels for guard checks.

    N1 — Log only (observe, no block)
    N2 — Warn (flag to human, allow through)
    N3 — Block (reject output, request retry)
    N4 — Kill (terminate agent execution immediately)
    """

    N1 = 1
    N2 = 2
    N3 = 3
    N4 = 4


@dataclass(frozen=True)
class GuardResult:
    """Outcome of a guard check on a single invocation."""

    passed: bool
    level: GuardLevel
    rule: str = ""
    message: str = ""
    metadata: dict[str, Any] | None = None

    @property
    def should_block(self) -> bool:
        """True if the guard level requires blocking execution."""
        return not self.passed and self.level >= GuardLevel.N3


class GuardViolation(Exception):
    """Raised when a guard check fails at level N3 or N4."""

    def __init__(self, result: GuardResult) -> None:
        self.result = result
        super().__init__(
            f"Guard violation [{result.level.name}]: {result.rule} — {result.message}"
        )
