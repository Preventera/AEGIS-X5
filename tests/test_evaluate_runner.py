"""Tests for aegis.evaluate.runner — EvalRunner + reports."""

from __future__ import annotations

import json

from aegis.evaluate.metrics import EvalMetric, FaithfulnessMetric, MetricResult, RelevancyMetric
from aegis.evaluate.runner import CaseResult, EvalReport, EvalRunner, TestCase


class TestTestCase:
    def test_basic(self):
        tc = TestCase(name="q1", query="hi", response="hello")
        assert tc.name == "q1"
        assert tc.query == "hi"


class TestCaseResult:
    def test_all_pass(self):
        tc = TestCase(name="t")
        mr = (MetricResult(name="m1", score=0.9, passed=True),)
        cr = CaseResult(case=tc, metric_results=mr)
        assert cr.passed
        assert cr.avg_score == 0.9

    def test_one_fails(self):
        tc = TestCase(name="t")
        mr = (
            MetricResult(name="m1", score=0.9, passed=True),
            MetricResult(name="m2", score=0.3, passed=False),
        )
        cr = CaseResult(case=tc, metric_results=mr)
        assert not cr.passed
        assert abs(cr.avg_score - 0.6) < 0.01

    def test_empty(self):
        cr = CaseResult(case=TestCase(name="t"), metric_results=())
        assert cr.passed
        assert cr.avg_score == 0.0


class TestEvalRunner:
    def test_no_metrics(self):
        runner = EvalRunner()
        report = runner.run([TestCase(name="q1", query="x", response="y")])
        assert report.passed
        assert len(report.case_results) == 1

    def test_single_metric(self):
        runner = EvalRunner()
        runner.add_metric(RelevancyMetric())
        report = runner.run([
            TestCase(name="q1", query="capital France", response="Paris is the capital of France."),
        ])
        assert len(report.case_results) == 1
        assert report.case_results[0].metric_results[0].name == "relevancy"

    def test_multiple_metrics(self):
        runner = EvalRunner()
        runner.add_metric(FaithfulnessMetric())
        runner.add_metric(RelevancyMetric())
        report = runner.run([
            TestCase(
                name="q1",
                query="What is Python?",
                response="Python is a programming language.",
                context="Python is a popular programming language.",
            )
        ])
        assert len(report.case_results[0].metric_results) == 2

    def test_multiple_cases(self):
        runner = EvalRunner().add_metric(RelevancyMetric())
        cases = [
            TestCase(name=f"q{i}", query="test", response="test response")
            for i in range(5)
        ]
        report = runner.run(cases)
        assert len(report.case_results) == 5

    def test_remove_metric(self):
        runner = EvalRunner()
        runner.add_metric(FaithfulnessMetric())
        runner.add_metric(RelevancyMetric())
        runner.remove_metric("faithfulness")
        assert len(runner.metrics) == 1

    def test_chaining(self):
        runner = EvalRunner().add_metric(FaithfulnessMetric()).add_metric(RelevancyMetric())
        assert len(runner.metrics) == 2

    def test_custom_metric(self):
        class Always1(EvalMetric):
            def evaluate(self, **kw):
                return MetricResult(name=self.name, score=1.0, passed=True)

        runner = EvalRunner().add_metric(Always1("custom"))
        report = runner.run([TestCase(name="q")])
        assert report.case_results[0].metric_results[0].score == 1.0


class TestEvalReport:
    def _make_report(self) -> EvalReport:
        runner = EvalRunner().add_metric(RelevancyMetric())
        return runner.run([
            TestCase(name="pass", query="capital France", response="Paris is the capital of France."),
            TestCase(name="fail", query="quantum physics", response="Apples are red."),
        ])

    def test_pass_rate(self):
        report = self._make_report()
        assert 0.0 <= report.pass_rate <= 1.0

    def test_summary(self):
        report = self._make_report()
        assert "total" in report.summary
        assert "passed" in report.summary
        assert "failed" in report.summary

    def test_to_json(self):
        report = self._make_report()
        data = json.loads(report.to_json())
        assert "pass_rate" in data
        assert "cases" in data
        assert isinstance(data["cases"], list)

    def test_to_markdown(self):
        report = self._make_report()
        md = report.to_markdown()
        assert "# Evaluation Report" in md
        assert "PASS" in md or "FAIL" in md
        assert "|" in md
