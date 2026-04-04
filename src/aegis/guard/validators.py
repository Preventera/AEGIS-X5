"""Validator framework — BaseValidator interface and built-in validators."""

from __future__ import annotations

import abc
import re
from dataclasses import dataclass, field
from typing import Any

from aegis.core.guard_levels import GuardLevel, GuardResult


# ---------------------------------------------------------------------------
# Base interface
# ---------------------------------------------------------------------------


class BaseValidator(abc.ABC):
    """Abstract validator — implement :meth:`validate` to create plug-in validators.

    Every validator has a ``name`` and a default ``level`` (N1–N4).
    """

    def __init__(self, name: str, level: GuardLevel = GuardLevel.N2) -> None:
        self.name = name
        self.level = level

    @abc.abstractmethod
    def validate(self, content: str, *, context: dict[str, Any] | None = None) -> GuardResult:
        """Run the validation on *content*.

        Return a :class:`GuardResult` indicating pass/fail.
        """
        ...


# ---------------------------------------------------------------------------
# Built-in: PII Detector
# ---------------------------------------------------------------------------

# Patterns for common PII — intentionally conservative to avoid false positives.
_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
}


class PIIDetector(BaseValidator):
    """Detects personally identifiable information in text.

    Parameters
    ----------
    patterns : dict[str, re.Pattern] | None
        Custom patterns to use instead of built-in ones.
    level : GuardLevel
        Default severity when PII is detected.
    """

    def __init__(
        self,
        *,
        patterns: dict[str, re.Pattern[str]] | None = None,
        level: GuardLevel = GuardLevel.N3,
    ) -> None:
        super().__init__(name="pii-detector", level=level)
        self.patterns = patterns or dict(_PII_PATTERNS)

    def validate(self, content: str, *, context: dict[str, Any] | None = None) -> GuardResult:
        found: list[str] = []
        for pii_type, pattern in self.patterns.items():
            if pattern.search(content):
                found.append(pii_type)
        if found:
            return GuardResult(
                passed=False,
                level=self.level,
                rule=self.name,
                message=f"PII detected: {', '.join(found)}",
                metadata={"pii_types": found},
            )
        return GuardResult(passed=True, level=self.level, rule=self.name)


# ---------------------------------------------------------------------------
# Built-in: Injection Detector
# ---------------------------------------------------------------------------

_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(your\s+)?instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE),
    re.compile(r"\]\s*\}\s*\{", re.IGNORECASE),  # JSON injection attempt
]


class InjectionDetector(BaseValidator):
    """Detects prompt injection attempts in text.

    Parameters
    ----------
    extra_patterns : list[re.Pattern] | None
        Additional patterns to check beyond the built-in set.
    level : GuardLevel
        Default severity when injection is detected.
    """

    def __init__(
        self,
        *,
        extra_patterns: list[re.Pattern[str]] | None = None,
        level: GuardLevel = GuardLevel.N4,
    ) -> None:
        super().__init__(name="injection-detector", level=level)
        self.patterns = list(_INJECTION_PATTERNS)
        if extra_patterns:
            self.patterns.extend(extra_patterns)

    def validate(self, content: str, *, context: dict[str, Any] | None = None) -> GuardResult:
        for pattern in self.patterns:
            match = pattern.search(content)
            if match:
                return GuardResult(
                    passed=False,
                    level=self.level,
                    rule=self.name,
                    message=f"Injection pattern detected: {match.group()!r}",
                    metadata={"matched": match.group()},
                )
        return GuardResult(passed=True, level=self.level, rule=self.name)


# ---------------------------------------------------------------------------
# Built-in: Hallucination Detector
# ---------------------------------------------------------------------------


class HallucinationDetector(BaseValidator):
    """Detects potential hallucination signals in LLM output.

    Checks for common hedging/fabrication indicators and optionally
    validates against a set of known facts (ground truth).

    Parameters
    ----------
    ground_truth : list[str] | None
        Known facts — if provided, output that contradicts them is flagged.
    confidence_phrases : list[str] | None
        Phrases that indicate fabrication (overridable).
    level : GuardLevel
        Default severity.
    """

    _DEFAULT_CONFIDENCE_PHRASES = [
        "as an ai",
        "i cannot verify",
        "i don't have access to real-time",
        "i'm not able to confirm",
        "my training data",
        "i apologize, but i",
    ]

    def __init__(
        self,
        *,
        ground_truth: list[str] | None = None,
        confidence_phrases: list[str] | None = None,
        level: GuardLevel = GuardLevel.N2,
    ) -> None:
        super().__init__(name="hallucination-detector", level=level)
        self.ground_truth = ground_truth or []
        self.confidence_phrases = confidence_phrases or list(self._DEFAULT_CONFIDENCE_PHRASES)

    def validate(self, content: str, *, context: dict[str, Any] | None = None) -> GuardResult:
        lower = content.lower()
        signals: list[str] = []

        # Check hedging / fabrication phrases
        for phrase in self.confidence_phrases:
            if phrase in lower:
                signals.append(f"hedging: {phrase!r}")

        # Ground truth contradiction (simple substring absence check)
        ctx = context or {}
        facts = ctx.get("ground_truth", self.ground_truth)
        for fact in facts:
            if fact.lower() not in lower:
                signals.append(f"missing fact: {fact!r}")

        if signals:
            return GuardResult(
                passed=False,
                level=self.level,
                rule=self.name,
                message=f"Hallucination signals: {len(signals)} found",
                metadata={"signals": signals},
            )
        return GuardResult(passed=True, level=self.level, rule=self.name)
