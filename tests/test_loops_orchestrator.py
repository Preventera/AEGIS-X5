"""Tests for aegis.loops.orchestrator — LoopOrchestrator with autonomy modes."""

from __future__ import annotations

import pytest

from aegis.loops.base import ClosedLoop, LoopStatus
from aegis.loops.orchestrator import AutonomyLevel, LoopOrchestrator
from aegis.remember.provenance import ActivityType, ProvenanceTracker

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


class DetectOnlyLoop(ClosedLoop):
    """Always detects a problem."""

    def detect(self, **ctx):
        return {"issue": "found"}

    def correct(self, diag, **ctx):
        return {"fixed": True}

    def validate(self, corr, **ctx):
        return True

    def learn(self, result, **ctx):
        return {}


class IdleLoop(ClosedLoop):
    def detect(self, **ctx):
        return None

    def correct(self, diag, **ctx):
        return {}

    def validate(self, corr, **ctx):
        return True

    def learn(self, result, **ctx):
        return {}


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_register(self):
        orch = LoopOrchestrator()
        orch.register(DetectOnlyLoop("a"))
        assert "a" in orch.loops

    def test_unregister(self):
        orch = LoopOrchestrator()
        orch.register(DetectOnlyLoop("a"))
        orch.unregister("a")
        assert "a" not in orch.loops

    def test_chaining(self):
        orch = LoopOrchestrator()
        orch.register(DetectOnlyLoop("a")).register(IdleLoop("b"))
        assert len(orch.loops) == 2

    def test_run_one_missing(self):
        orch = LoopOrchestrator()
        with pytest.raises(KeyError):
            orch.run_one("nonexistent")


# ---------------------------------------------------------------------------
# Monitor mode
# ---------------------------------------------------------------------------


class TestMonitorMode:
    def test_detect_only(self):
        orch = LoopOrchestrator(autonomy="monitor")
        orch.register(DetectOnlyLoop("a"))
        results = orch.run_all()
        assert len(results) == 1
        assert results[0].status == LoopStatus.DETECTED
        assert results[0].detected == {"issue": "found"}
        # No correction attempted
        assert results[0].correction == {}

    def test_idle(self):
        orch = LoopOrchestrator(autonomy="monitor")
        orch.register(IdleLoop("idle"))
        results = orch.run_all()
        assert results[0].status == LoopStatus.IDLE

    def test_no_correct_in_monitor(self):
        """Even high-risk loops only detect in monitor mode."""
        orch = LoopOrchestrator(autonomy="monitor")
        orch.register(DetectOnlyLoop("risky"), high_risk=True)
        result = orch.run_one("risky")
        assert result.status == LoopStatus.DETECTED
        assert result.correction == {}


# ---------------------------------------------------------------------------
# Full-auto mode
# ---------------------------------------------------------------------------


class TestFullAutoMode:
    def test_auto_correct(self):
        orch = LoopOrchestrator(autonomy="full-auto")
        orch.register(DetectOnlyLoop("a"))
        result = orch.run_one("a")
        assert result.status == LoopStatus.SUCCESS
        assert result.validated

    def test_high_risk_auto(self):
        """In full-auto, even high-risk loops run without HITL."""
        orch = LoopOrchestrator(autonomy="full-auto")
        orch.register(DetectOnlyLoop("risky"), high_risk=True)
        result = orch.run_one("risky")
        assert result.status == LoopStatus.SUCCESS

    def test_idle_in_full_auto(self):
        orch = LoopOrchestrator(autonomy="full-auto")
        orch.register(IdleLoop("idle"))
        result = orch.run_one("idle")
        assert result.status == LoopStatus.IDLE


# ---------------------------------------------------------------------------
# Semi-auto mode
# ---------------------------------------------------------------------------


class TestSemiAutoMode:
    def test_low_risk_auto(self):
        """Low-risk loops run automatically in semi-auto."""
        orch = LoopOrchestrator(autonomy="semi-auto")
        orch.register(DetectOnlyLoop("low"), high_risk=False)
        result = orch.run_one("low")
        assert result.status == LoopStatus.SUCCESS

    def test_high_risk_no_hitl_skips(self):
        """High-risk without HITL callback → skipped."""
        orch = LoopOrchestrator(autonomy="semi-auto")
        orch.register(DetectOnlyLoop("risky"), high_risk=True)
        result = orch.run_one("risky")
        assert result.status == LoopStatus.SKIPPED

    def test_high_risk_hitl_approved(self):
        approvals = []

        def hitl(name, diag):
            approvals.append((name, diag))
            return True

        orch = LoopOrchestrator(autonomy="semi-auto", hitl_fn=hitl)
        orch.register(DetectOnlyLoop("risky"), high_risk=True)
        result = orch.run_one("risky")
        assert result.status == LoopStatus.SUCCESS
        assert len(approvals) == 1
        assert approvals[0][0] == "risky"

    def test_high_risk_hitl_rejected(self):
        def hitl(name, diag):
            return False

        orch = LoopOrchestrator(autonomy="semi-auto", hitl_fn=hitl)
        orch.register(DetectOnlyLoop("risky"), high_risk=True)
        result = orch.run_one("risky")
        assert result.status == LoopStatus.SKIPPED

    def test_high_risk_idle_no_hitl(self):
        """If nothing detected, HITL is never called."""
        calls = []

        def hitl(name, diag):
            calls.append(1)
            return True

        orch = LoopOrchestrator(autonomy="semi-auto", hitl_fn=hitl)
        orch.register(IdleLoop("idle"), high_risk=True)
        result = orch.run_one("idle")
        assert result.status == LoopStatus.IDLE
        assert len(calls) == 0


# ---------------------------------------------------------------------------
# Provenance & history
# ---------------------------------------------------------------------------


class TestOrchestratorProvenance:
    def test_provenance_logged(self):
        tracker = ProvenanceTracker()
        orch = LoopOrchestrator(autonomy="full-auto", tracker=tracker)
        orch.register(DetectOnlyLoop("a"))
        orch.run_all()
        trail = tracker.trail(activity=ActivityType.UPDATE)
        assert any(r.attributes.get("action") == "cycle_complete" for r in trail)

    def test_hitl_rejection_logged(self):
        tracker = ProvenanceTracker()
        orch = LoopOrchestrator(autonomy="semi-auto", tracker=tracker, hitl_fn=lambda n, d: False)
        orch.register(DetectOnlyLoop("risky"), high_risk=True)
        orch.run_one("risky")
        trail = tracker.trail(activity=ActivityType.READ)
        assert any(r.attributes.get("action") == "hitl_rejected" for r in trail)

    def test_hitl_approval_logged(self):
        tracker = ProvenanceTracker()
        orch = LoopOrchestrator(autonomy="semi-auto", tracker=tracker, hitl_fn=lambda n, d: True)
        orch.register(DetectOnlyLoop("risky"), high_risk=True)
        orch.run_one("risky")
        trail = tracker.trail(activity=ActivityType.READ)
        assert any(r.attributes.get("action") == "hitl_approved" for r in trail)

    def test_history(self):
        orch = LoopOrchestrator(autonomy="full-auto")
        orch.register(DetectOnlyLoop("a"))
        orch.register(IdleLoop("b"))
        orch.run_all()
        assert len(orch.history) == 2

    def test_run_all_multiple(self):
        orch = LoopOrchestrator(autonomy="full-auto")
        orch.register(DetectOnlyLoop("a"))
        orch.register(DetectOnlyLoop("b"))
        results = orch.run_all()
        assert len(results) == 2
        assert all(r.status == LoopStatus.SUCCESS for r in results)


# ---------------------------------------------------------------------------
# Autonomy level switching
# ---------------------------------------------------------------------------


class TestAutonomySwitch:
    def test_change_level(self):
        orch = LoopOrchestrator(autonomy="monitor")
        assert orch.autonomy == AutonomyLevel.MONITOR
        orch.autonomy = "full-auto"
        assert orch.autonomy == AutonomyLevel.FULL_AUTO

    def test_enum_value(self):
        orch = LoopOrchestrator(autonomy=AutonomyLevel.SEMI_AUTO)
        assert orch.autonomy == AutonomyLevel.SEMI_AUTO

    def test_all_values(self):
        assert AutonomyLevel.MONITOR.value == "monitor"
        assert AutonomyLevel.SEMI_AUTO.value == "semi-auto"
        assert AutonomyLevel.FULL_AUTO.value == "full-auto"
