"""Tests for aegis.loops.base — ClosedLoop ABC and LoopResult."""

from __future__ import annotations

from typing import Any

import pytest

from aegis.loops.base import ClosedLoop, LoopResult, LoopStatus


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class AlwaysOKLoop(ClosedLoop):
    def detect(self, **ctx):
        return {"issue": "minor"}

    def correct(self, diag, **ctx):
        return {"action": "fixed"}

    def validate(self, corr, **ctx):
        return True

    def learn(self, result, **ctx):
        return {"learned": True}


class NothingToDoLoop(ClosedLoop):
    def detect(self, **ctx):
        return None

    def correct(self, diag, **ctx):
        return {}

    def validate(self, corr, **ctx):
        return True

    def learn(self, result, **ctx):
        return {}


class FailDetectLoop(ClosedLoop):
    def detect(self, **ctx):
        raise RuntimeError("detect exploded")

    def correct(self, diag, **ctx):
        return {}

    def validate(self, corr, **ctx):
        return True

    def learn(self, result, **ctx):
        return {}


class FailCorrectLoop(ClosedLoop):
    def detect(self, **ctx):
        return {"issue": "x"}

    def correct(self, diag, **ctx):
        raise RuntimeError("correct failed")

    def validate(self, corr, **ctx):
        return True

    def learn(self, result, **ctx):
        return {}


class FailValidateLoop(ClosedLoop):
    def detect(self, **ctx):
        return {"issue": "x"}

    def correct(self, diag, **ctx):
        return {"action": "y"}

    def validate(self, corr, **ctx):
        return False

    def learn(self, result, **ctx):
        return {}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLoopResult:
    def test_defaults(self):
        r = LoopResult(loop_name="test")
        assert r.status == LoopStatus.IDLE
        assert len(r.cycle_id) == 12
        assert r.started_at > 0

    def test_duration(self):
        r = LoopResult(loop_name="x", started_at=1.0, finished_at=1.05)
        assert abs(r.duration_ms - 50.0) < 0.01


class TestClosedLoopABC:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            ClosedLoop("test")  # type: ignore[abstract]


class TestFullCycle:
    def test_success(self):
        loop = AlwaysOKLoop("ok-loop")
        result = loop.run()
        assert result.status == LoopStatus.SUCCESS
        assert result.validated
        assert result.detected == {"issue": "minor"}
        assert result.correction == {"action": "fixed"}
        assert result.learned == {"learned": True}
        assert result.finished_at > 0

    def test_nothing_detected(self):
        loop = NothingToDoLoop("idle-loop")
        result = loop.run()
        assert result.status == LoopStatus.IDLE
        assert result.detected == {}

    def test_detect_error(self):
        loop = FailDetectLoop("fail-detect")
        result = loop.run()
        assert result.status == LoopStatus.FAILED
        assert "detect failed" in result.error

    def test_correct_error(self):
        loop = FailCorrectLoop("fail-correct")
        result = loop.run()
        assert result.status == LoopStatus.FAILED
        assert "correct failed" in result.error

    def test_validation_fails(self):
        loop = FailValidateLoop("fail-validate")
        result = loop.run()
        assert result.status == LoopStatus.FAILED
        assert not result.validated

    def test_history(self):
        loop = AlwaysOKLoop("h-loop")
        loop.run()
        loop.run()
        assert len(loop.history) == 2

    def test_context_passed(self):
        class CtxLoop(ClosedLoop):
            def detect(self, **ctx):
                return {"got": ctx.get("key")}

            def correct(self, diag, **ctx):
                return diag

            def validate(self, corr, **ctx):
                return True

            def learn(self, result, **ctx):
                return {}

        loop = CtxLoop("ctx")
        r = loop.run(key="value")
        assert r.detected["got"] == "value"


class TestLoopStatus:
    def test_all_values(self):
        assert LoopStatus.IDLE.value == "idle"
        assert LoopStatus.DETECTED.value == "detected"
        assert LoopStatus.CORRECTING.value == "correcting"
        assert LoopStatus.SUCCESS.value == "success"
        assert LoopStatus.FAILED.value == "failed"
        assert LoopStatus.SKIPPED.value == "skipped"
