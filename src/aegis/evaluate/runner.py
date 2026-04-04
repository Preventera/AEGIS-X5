"""EvalRunner — execute test cases against metrics, produce reports."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from aegis.evaluate.metrics import EvalMetric, MetricResult


@dataclass(frozen=True)
class TestCase:
    """A single evaluation test case."""

    name: str
    query: str = ""
    response: str = ""
    context: str = ""
    reference: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CaseResult:
    """Results of all metrics for one test case."""

    case: TestCase
    metric_results: tuple[MetricResult, ...]

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.metric_results)

    @property
    def avg_score(self) -> float:
        if not self.metric_results:
            return 0.0
        return sum(r.score for r in self.metric_results) / len(self.metric_results)


@dataclass(frozen=True)
class EvalReport:
    """Aggregated evaluation report."""

    case_results: tuple[CaseResult, ...]
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(cr.passed for cr in self.case_results)

    @property
    def pass_rate(self) -> float:
        if not self.case_results:
            return 0.0
        return sum(1 for cr in self.case_results if cr.passed) / len(self.case_results)

    def to_json(self) -> str:
        return json.dumps(self._to_dict(), indent=2, default=str)

    def to_markdown(self) -> str:
        lines = ["# Evaluation Report", ""]
        lines.append(f"**Pass rate:** {self.pass_rate:.0%} ({sum(1 for c in self.case_results if c.passed)}/{len(self.case_results)})")
        lines.append("")
        lines.append("| Test Case | Score | Status |")
        lines.append("|-----------|-------|--------|")
        for cr in self.case_results:
            status = "PASS" if cr.passed else "FAIL"
            lines.append(f"| {cr.case.name} | {cr.avg_score:.2f} | {status} |")
        lines.append("")
        for cr in self.case_results:
            lines.append(f"## {cr.case.name}")
            for mr in cr.metric_results:
                status = "PASS" if mr.passed else "FAIL"
                lines.append(f"- **{mr.name}**: {mr.score:.4f} [{status}]")
            lines.append("")
        return "\n".join(lines)

    def _to_dict(self) -> dict[str, Any]:
        return {
            "pass_rate": self.pass_rate,
            "total_cases": len(self.case_results),
            "passed_cases": sum(1 for c in self.case_results if c.passed),
            "cases": [
                {
                    "name": cr.case.name,
                    "passed": cr.passed,
                    "avg_score": cr.avg_score,
                    "metrics": [
                        {"name": mr.name, "score": mr.score, "passed": mr.passed, "details": mr.details}
                        for mr in cr.metric_results
                    ],
                }
                for cr in self.case_results
            ],
            "summary": self.summary,
        }


class EvalRunner:
    """Execute a set of test cases against configured metrics.

    Usage::

        runner = EvalRunner()
        runner.add_metric(FaithfulnessMetric())
        runner.add_metric(RelevancyMetric())

        report = runner.run([
            TestCase(name="q1", query="What is X?", response="X is...", context="...")
        ])
    """

    def __init__(self) -> None:
        self._metrics: list[EvalMetric] = []

    @property
    def metrics(self) -> list[EvalMetric]:
        return list(self._metrics)

    def add_metric(self, metric: EvalMetric) -> EvalRunner:
        self._metrics.append(metric)
        return self

    def remove_metric(self, name: str) -> EvalRunner:
        self._metrics = [m for m in self._metrics if m.name != name]
        return self

    def run(self, cases: list[TestCase]) -> EvalReport:
        case_results: list[CaseResult] = []
        for case in cases:
            metric_results: list[MetricResult] = []
            for metric in self._metrics:
                result = metric.evaluate(
                    query=case.query,
                    response=case.response,
                    context=case.context,
                    reference=case.reference,
                )
                metric_results.append(result)
            case_results.append(CaseResult(case=case, metric_results=tuple(metric_results)))

        total = len(case_results)
        passed = sum(1 for cr in case_results if cr.passed)
        summary = {"total": total, "passed": passed, "failed": total - passed}
        return EvalReport(case_results=tuple(case_results), summary=summary)
