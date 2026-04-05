"""LoopOrchestrator — registers and runs closed loops with autonomy modes."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from aegis.loops.base import ClosedLoop, LoopResult, LoopStatus
from aegis.remember.provenance import ActivityType, ProvenanceTracker


class AutonomyLevel(str, Enum):
    MONITOR = "monitor"
    SEMI_AUTO = "semi-auto"
    FULL_AUTO = "full-auto"


# Callback for HITL approval: (loop_name, diagnosis) -> bool
HITLApprovalFn = Callable[[str, dict[str, Any]], bool]


@dataclass
class LoopRegistration:
    """A registered loop with its risk classification."""

    loop: ClosedLoop
    high_risk: bool = False


class LoopOrchestrator:
    """Orchestrates autonomous closed loops with autonomy modes and HITL gates.

    Usage::

        orch = LoopOrchestrator(autonomy="semi-auto", tracker=tracker)
        orch.register(my_drift_loop, high_risk=True)
        orch.register(my_guard_loop, high_risk=False)
        results = orch.run_all()

    Autonomy modes:
      - ``monitor``: detect only, never correct
      - ``semi-auto``: auto-correct low-risk; HITL approval for high-risk
      - ``full-auto``: auto-correct everything
    """

    def __init__(
        self,
        *,
        autonomy: str | AutonomyLevel = AutonomyLevel.MONITOR,
        tracker: ProvenanceTracker | None = None,
        hitl_fn: HITLApprovalFn | None = None,
    ) -> None:
        if isinstance(autonomy, str):
            autonomy = AutonomyLevel(autonomy)
        self._autonomy = autonomy
        self._tracker = tracker or ProvenanceTracker()
        self._hitl_fn = hitl_fn
        self._loops: dict[str, LoopRegistration] = {}
        self._history: list[LoopResult] = []

    @property
    def autonomy(self) -> AutonomyLevel:
        return self._autonomy

    @autonomy.setter
    def autonomy(self, value: str | AutonomyLevel) -> None:
        if isinstance(value, str):
            value = AutonomyLevel(value)
        self._autonomy = value

    @property
    def tracker(self) -> ProvenanceTracker:
        return self._tracker

    @property
    def loops(self) -> dict[str, LoopRegistration]:
        return dict(self._loops)

    @property
    def history(self) -> list[LoopResult]:
        return list(self._history)

    def register(self, loop: ClosedLoop, *, high_risk: bool = False) -> LoopOrchestrator:
        """Register a closed loop. Returns self for chaining."""
        self._loops[loop.name] = LoopRegistration(loop=loop, high_risk=high_risk)
        return self

    def unregister(self, name: str) -> LoopOrchestrator:
        self._loops.pop(name, None)
        return self

    def run_one(self, name: str, **context: Any) -> LoopResult:
        """Run a single named loop through the autonomy gate."""
        reg = self._loops.get(name)
        if reg is None:
            raise KeyError(f"No loop registered with name {name!r}")
        return self._execute(reg, **context)

    def run_all(self, **context: Any) -> list[LoopResult]:
        """Run all registered loops. Returns list of results."""
        results: list[LoopResult] = []
        for reg in self._loops.values():
            result = self._execute(reg, **context)
            results.append(result)
        return results

    def _execute(self, reg: LoopRegistration, **context: Any) -> LoopResult:
        loop = reg.loop

        # --- MONITOR mode: detect only ---
        if self._autonomy == AutonomyLevel.MONITOR:
            result = LoopResult(loop_name=loop.name)
            diagnosis = loop.detect(**context)
            if diagnosis:
                result.detected = diagnosis
                result.status = LoopStatus.DETECTED
            else:
                result.status = LoopStatus.IDLE
            result.finished_at = time.time()
            self._log_result(result)
            return result

        # --- SEMI_AUTO: HITL gate for high-risk ---
        if self._autonomy == AutonomyLevel.SEMI_AUTO and reg.high_risk:
            # First detect
            result = LoopResult(loop_name=loop.name)
            diagnosis = loop.detect(**context)
            if diagnosis is None:
                result.status = LoopStatus.IDLE
                result.finished_at = time.time()
                self._log_result(result)
                return result

            result.detected = diagnosis
            result.status = LoopStatus.DETECTED

            # Ask human
            approved = False
            if self._hitl_fn is not None:
                approved = self._hitl_fn(loop.name, diagnosis)

            if not approved:
                result.status = LoopStatus.SKIPPED
                result.finished_at = time.time()
                self._tracker.record(
                    ActivityType.READ,
                    f"orchestrator:{loop.name}",
                    action="hitl_rejected",
                    diagnosis=str(diagnosis),
                )
                self._log_result(result)
                return result

            # Approved — run full cycle
            self._tracker.record(
                ActivityType.READ,
                f"orchestrator:{loop.name}",
                action="hitl_approved",
                diagnosis=str(diagnosis),
            )
            result = loop.run(**context)
            self._log_result(result)
            return result

        # --- FULL_AUTO or SEMI_AUTO low-risk: run directly ---
        result = loop.run(**context)
        self._log_result(result)
        return result

    def _log_result(self, result: LoopResult) -> None:
        self._history.append(result)
        self._tracker.record(
            ActivityType.UPDATE,
            f"orchestrator:{result.loop_name}",
            action="cycle_complete",
            status=result.status.value,
            cycle_id=result.cycle_id,
        )
