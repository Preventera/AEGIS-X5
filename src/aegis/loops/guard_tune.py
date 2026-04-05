"""GuardAutoTune — closed loop that detects recurring hallucinations and auto-adds guard patterns."""

from __future__ import annotations

from typing import Any

from aegis.guard.validators import HallucinationDetector
from aegis.loops.base import ClosedLoop, LoopResult
from aegis.remember.provenance import ActivityType, ProvenanceTracker


class GuardAutoTune(ClosedLoop):
    """Detects recurring hallucination on a subject and adds guard patterns.

    Parameters
    ----------
    detector : HallucinationDetector
        The hallucination validator to tune.
    tracker : ProvenanceTracker | None
        Audit trail.
    recurrence_threshold : int
        How many times a subject must fail before auto-tuning (default 2).
    """

    def __init__(
        self,
        *,
        detector: HallucinationDetector,
        tracker: ProvenanceTracker | None = None,
        recurrence_threshold: int = 2,
    ) -> None:
        super().__init__(name="guard-auto-tune")
        self._detector = detector
        self._tracker = tracker or ProvenanceTracker()
        self._threshold = recurrence_threshold
        # subject -> failure count
        self._failure_log: dict[str, int] = {}
        # subjects already tuned
        self._tuned: set[str] = set()

    @property
    def tracker(self) -> ProvenanceTracker:
        return self._tracker

    @property
    def detector(self) -> HallucinationDetector:
        return self._detector

    @property
    def failure_log(self) -> dict[str, int]:
        return dict(self._failure_log)

    def report_failure(self, subject: str) -> None:
        """Report a hallucination failure for a subject (called externally)."""
        self._failure_log[subject] = self._failure_log.get(subject, 0) + 1

    def detect(self, **context: Any) -> dict[str, Any] | None:
        subject = context.get("subject")
        # If specific subject provided, check that one
        if subject:
            count = self._failure_log.get(subject, 0)
            if count >= self._threshold and subject not in self._tuned:
                return {"subject": subject, "count": count}
            return None

        # Otherwise scan all subjects
        for subj, count in self._failure_log.items():
            if count >= self._threshold and subj not in self._tuned:
                return {"subject": subj, "count": count}
        return None

    def correct(self, diagnosis: dict[str, Any], **context: Any) -> dict[str, Any]:
        subject = diagnosis["subject"]
        # Add the subject as a confidence phrase to catch future hallucinations
        phrase = subject.lower()
        if phrase not in self._detector.confidence_phrases:
            self._detector.confidence_phrases.append(phrase)

        self._tuned.add(subject)
        self._tracker.record(
            ActivityType.UPDATE,
            f"loop:{self.name}",
            action="add_pattern",
            subject=subject,
            phrase=phrase,
        )
        return {"added_phrase": phrase, "subject": subject}

    def validate(self, correction: dict[str, Any], **context: Any) -> bool:
        phrase = correction["added_phrase"]
        # Validate that text containing the phrase is now caught
        test_content = f"The answer involves {phrase} which may be inaccurate."
        result = self._detector.validate(test_content)
        return not result.passed  # Should fail = phrase is detected

    def learn(self, result: LoopResult, **context: Any) -> dict[str, Any]:
        subject = result.detected.get("subject", "")
        if result.validated:
            # Reset failure count for this subject
            self._failure_log.pop(subject, None)
            self._tracker.record(
                ActivityType.UPDATE,
                f"loop:{self.name}",
                action="tune_validated",
                subject=subject,
            )
            return {"subject": subject, "status": "tuned"}

        # If validation failed, remove the phrase we just added
        phrase = result.correction.get("added_phrase", "")
        if phrase in self._detector.confidence_phrases:
            self._detector.confidence_phrases.remove(phrase)
        self._tuned.discard(subject)
        return {"subject": subject, "status": "rollback"}
