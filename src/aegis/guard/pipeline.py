"""Guard pipeline — sequential validator execution with HITL gate."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from aegis.core.guard_levels import GuardLevel, GuardResult, GuardViolation
from aegis.guard.validators import BaseValidator


@dataclass(frozen=True)
class PipelineResult:
    """Aggregated result from running all validators in the pipeline."""

    passed: bool
    results: tuple[GuardResult, ...]
    blocked_by: GuardResult | None = None
    needs_approval: bool = False


# Type for the human-in-the-loop callback:
#   (content, failing_result) -> bool  (True = approve, False = reject)
HITLCallback = Callable[[str, GuardResult], bool]


class GuardPipeline:
    """Sequential validator pipeline: Input → Validators → Output → HITL gate.

    Usage::

        pipeline = GuardPipeline()
        pipeline.add(PIIDetector())
        pipeline.add(InjectionDetector())

        result = pipeline.run("some LLM output")
        if not result.passed:
            print(result.blocked_by)
    """

    def __init__(self, *, hitl_callback: HITLCallback | None = None) -> None:
        self._validators: list[BaseValidator] = []
        self._hitl: HITLCallback | None = hitl_callback

    @property
    def validators(self) -> list[BaseValidator]:
        return list(self._validators)

    def add(self, validator: BaseValidator) -> GuardPipeline:
        """Append a validator to the pipeline. Returns self for chaining."""
        self._validators.append(validator)
        return self

    def remove(self, name: str) -> GuardPipeline:
        """Remove a validator by name. Returns self for chaining."""
        self._validators = [v for v in self._validators if v.name != name]
        return self

    def run(
        self,
        content: str,
        *,
        context: dict[str, Any] | None = None,
        raise_on_block: bool = False,
    ) -> PipelineResult:
        """Execute all validators sequentially on *content*.

        Behaviour by guard level on failure:
          - N1: log only → continue
          - N2: warn → flag ``needs_approval``, invoke HITL if configured
          - N3: block → stop pipeline, return blocked result
          - N4: kill → stop pipeline, optionally raise :class:`GuardViolation`

        Parameters
        ----------
        content : str
            The text to validate.
        context : dict | None
            Extra context passed to each validator.
        raise_on_block : bool
            If True, raise :class:`GuardViolation` on N3/N4 failures.
        """
        results: list[GuardResult] = []
        needs_approval = False

        for validator in self._validators:
            result = validator.validate(content, context=context)
            results.append(result)

            if result.passed:
                continue

            # N1 — log only, continue
            if result.level == GuardLevel.N1:
                continue

            # N2 — warn, ask HITL if available
            if result.level == GuardLevel.N2:
                needs_approval = True
                if self._hitl is not None:
                    approved = self._hitl(content, result)
                    if not approved:
                        return PipelineResult(
                            passed=False,
                            results=tuple(results),
                            blocked_by=result,
                            needs_approval=True,
                        )
                continue

            # N3/N4 — block / kill
            if raise_on_block:
                raise GuardViolation(result)
            return PipelineResult(
                passed=False,
                results=tuple(results),
                blocked_by=result,
            )

        return PipelineResult(
            passed=True,
            results=tuple(results),
            needs_approval=needs_approval,
        )
