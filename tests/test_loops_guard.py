"""Tests for aegis.loops.guard_tune — GuardAutoTune closed loop."""

from __future__ import annotations

from aegis.guard.validators import HallucinationDetector
from aegis.loops.base import LoopStatus
from aegis.loops.guard_tune import GuardAutoTune
from aegis.remember.provenance import ActivityType, ProvenanceTracker


class TestGuardAutoTune:
    def _make(self, recurrence=2):
        detector = HallucinationDetector()
        tracker = ProvenanceTracker()
        loop = GuardAutoTune(
            detector=detector,
            tracker=tracker,
            recurrence_threshold=recurrence,
        )
        return loop, detector, tracker

    def test_detect_no_failures(self):
        loop, _, _ = self._make()
        assert loop.detect() is None

    def test_detect_below_threshold(self):
        loop, _, _ = self._make(recurrence=3)
        loop.report_failure("quantum")
        loop.report_failure("quantum")
        assert loop.detect(subject="quantum") is None

    def test_detect_at_threshold(self):
        loop, _, _ = self._make(recurrence=2)
        loop.report_failure("quantum")
        loop.report_failure("quantum")
        diag = loop.detect(subject="quantum")
        assert diag is not None
        assert diag["subject"] == "quantum"
        assert diag["count"] == 2

    def test_detect_scans_all_subjects(self):
        loop, _, _ = self._make(recurrence=2)
        loop.report_failure("topic-a")
        loop.report_failure("topic-a")
        diag = loop.detect()
        assert diag is not None
        assert diag["subject"] == "topic-a"

    def test_full_cycle_success(self):
        loop, detector, tracker = self._make(recurrence=2)
        loop.report_failure("bad-topic")
        loop.report_failure("bad-topic")

        result = loop.run(subject="bad-topic")
        assert result.status == LoopStatus.SUCCESS
        assert result.validated
        # Phrase was added to detector
        assert "bad-topic" in detector.confidence_phrases

    def test_phrase_catches_content(self):
        loop, detector, _ = self._make(recurrence=1)
        loop.report_failure("unobtainium")
        loop.run(subject="unobtainium")

        # The detector should now catch text mentioning unobtainium
        r = detector.validate("The response mentions unobtainium which is uncertain.")
        assert not r.passed

    def test_provenance_logged(self):
        loop, _, tracker = self._make(recurrence=1)
        loop.report_failure("topic-x")
        loop.run(subject="topic-x")

        trail = tracker.trail(activity=ActivityType.UPDATE)
        actions = [r.attributes.get("action") for r in trail]
        assert "add_pattern" in actions
        assert "tune_validated" in actions

    def test_already_tuned_skipped(self):
        loop, _, _ = self._make(recurrence=1)
        loop.report_failure("topic")
        loop.run(subject="topic")
        # Second run — already tuned
        result = loop.run(subject="topic")
        assert result.status == LoopStatus.IDLE

    def test_failure_log(self):
        loop, _, _ = self._make()
        loop.report_failure("a")
        loop.report_failure("a")
        loop.report_failure("b")
        assert loop.failure_log == {"a": 2, "b": 1}

    def test_failure_count_reset_after_tune(self):
        loop, _, _ = self._make(recurrence=1)
        loop.report_failure("topic")
        loop.run(subject="topic")
        assert "topic" not in loop.failure_log
