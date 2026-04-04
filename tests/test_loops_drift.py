"""Tests for aegis.loops.drift_correct — DriftAutoCorrect closed loop."""

from __future__ import annotations

from aegis.evaluate.drift import DriftDetector
from aegis.loops.drift_correct import DriftAutoCorrect
from aegis.loops.base import LoopStatus
from aegis.remember.provenance import ActivityType, ProvenanceTracker


class TestDriftAutoCorrect:
    def _make(self, *, baseline=0.90, current_scores=None, post_retrain_scores=None):
        """Build a DriftAutoCorrect with controllable score/retrain fns."""
        detector = DriftDetector(warning_threshold=0.1, critical_threshold=0.25)
        detector.set_baseline({"faithfulness": baseline})
        tracker = ProvenanceTracker()

        call_count = {"retrain": 0, "score": 0}
        pre_scores = current_scores or {"faithfulness": 0.70}
        post_scores = post_retrain_scores or {"faithfulness": 0.88}

        def score_fn():
            call_count["score"] += 1
            # After retrain, return post-retrain scores
            if call_count["retrain"] > 0:
                return post_scores
            return pre_scores

        def retrain_fn(diagnosis):
            call_count["retrain"] += 1
            return {"retrained": True, "metric": diagnosis["metric"]}

        loop = DriftAutoCorrect(
            detector=detector,
            retrain_fn=retrain_fn,
            score_fn=score_fn,
            tracker=tracker,
        )
        return loop, tracker, call_count

    def test_detect_drift(self):
        loop, _, _ = self._make(current_scores={"faithfulness": 0.70})
        diag = loop.detect(scores={"faithfulness": 0.70})
        assert diag is not None
        assert diag["metric"] == "faithfulness"
        assert diag["delta"] > 0

    def test_no_drift(self):
        loop, _, _ = self._make(current_scores={"faithfulness": 0.88})
        diag = loop.detect(scores={"faithfulness": 0.88})
        assert diag is None

    def test_full_cycle_success(self):
        loop, tracker, counts = self._make(
            current_scores={"faithfulness": 0.70},
            post_retrain_scores={"faithfulness": 0.88},
        )
        result = loop.run(scores={"faithfulness": 0.70})
        assert result.status == LoopStatus.SUCCESS
        assert result.validated
        assert counts["retrain"] == 1

    def test_full_cycle_still_drifting(self):
        loop, _, _ = self._make(
            current_scores={"faithfulness": 0.60},
            post_retrain_scores={"faithfulness": 0.60},  # retrain didn't help
        )
        result = loop.run(scores={"faithfulness": 0.60})
        assert result.status == LoopStatus.FAILED
        assert not result.validated

    def test_provenance_logged(self):
        loop, tracker, _ = self._make(
            current_scores={"faithfulness": 0.70},
            post_retrain_scores={"faithfulness": 0.88},
        )
        loop.run(scores={"faithfulness": 0.70})
        trail = tracker.trail(activity=ActivityType.UPDATE)
        assert len(trail) >= 2  # retrain + baseline_updated
        actions = [r.attributes.get("action") for r in trail]
        assert "retrain" in actions
        assert "baseline_updated" in actions

    def test_baseline_updated_after_success(self):
        loop, _, _ = self._make(
            baseline=0.90,
            current_scores={"faithfulness": 0.70},
            post_retrain_scores={"faithfulness": 0.92},
        )
        loop.run(scores={"faithfulness": 0.70})
        # Baseline should now be 0.92
        assert loop.detector.baseline["faithfulness"] == 0.92

    def test_idle_when_no_scores_drift(self):
        loop, _, _ = self._make(current_scores={"faithfulness": 0.89})
        result = loop.run(scores={"faithfulness": 0.89})
        assert result.status == LoopStatus.IDLE

    def test_history(self):
        loop, _, _ = self._make(current_scores={"faithfulness": 0.89})
        loop.run(scores={"faithfulness": 0.89})
        loop.run(scores={"faithfulness": 0.89})
        assert len(loop.history) == 2
