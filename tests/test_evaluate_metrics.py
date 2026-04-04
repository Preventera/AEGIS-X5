"""Tests for aegis.evaluate.metrics — built-in eval metrics."""

from __future__ import annotations

import pytest

from aegis.evaluate.metrics import (
    ContextPrecision,
    EvalMetric,
    FaithfulnessMetric,
    MetricResult,
    RelevancyMetric,
)


class TestMetricResult:
    def test_basic(self):
        r = MetricResult(name="test", score=0.8, passed=True)
        assert r.name == "test"
        assert r.score == 0.8
        assert r.passed

    def test_frozen(self):
        r = MetricResult(name="x", score=0.5, passed=True)
        with pytest.raises(AttributeError):
            r.score = 0.9  # type: ignore[misc]


class TestEvalMetricABC:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            EvalMetric("test")  # type: ignore[abstract]

    def test_custom_metric(self):
        class LengthMetric(EvalMetric):
            def evaluate(self, *, response="", **kw):
                score = min(len(response) / 100, 1.0)
                return MetricResult(name=self.name, score=score, passed=score >= self.threshold)

        m = LengthMetric("length", threshold=0.5)
        r = m.evaluate(response="a" * 60)
        assert r.score == 0.6
        assert r.passed


class TestFaithfulness:
    def test_grounded_response(self):
        ctx = "Paris is the capital of France. It has the Eiffel Tower."
        resp = "Paris is the capital of France."
        m = FaithfulnessMetric()
        r = m.evaluate(response=resp, context=ctx)
        assert r.passed
        assert r.score >= 0.5

    def test_ungrounded_response(self):
        ctx = "The sky is blue."
        resp = "Tokyo has excellent sushi restaurants. The weather varies by season."
        m = FaithfulnessMetric()
        r = m.evaluate(response=resp, context=ctx)
        assert r.score < 0.5

    def test_empty_response(self):
        m = FaithfulnessMetric()
        r = m.evaluate(response="", context="Some context")
        assert not r.passed
        assert r.score == 0.0

    def test_empty_context(self):
        m = FaithfulnessMetric()
        r = m.evaluate(response="Some response", context="")
        assert not r.passed

    def test_custom_threshold(self):
        m = FaithfulnessMetric(threshold=0.9)
        assert m.threshold == 0.9

    def test_details_present(self):
        m = FaithfulnessMetric()
        r = m.evaluate(response="Paris is great.", context="Paris is great.")
        assert "grounded" in r.details
        assert "total" in r.details


class TestRelevancy:
    def test_relevant(self):
        m = RelevancyMetric()
        r = m.evaluate(query="What is machine learning?", response="Machine learning is a branch of AI.")
        assert r.passed
        assert r.score >= 0.5

    def test_irrelevant(self):
        m = RelevancyMetric()
        r = m.evaluate(query="What is quantum computing?", response="Apples are red fruits.")
        assert r.score < 0.5

    def test_empty_query(self):
        m = RelevancyMetric()
        r = m.evaluate(query="", response="some response")
        assert not r.passed

    def test_empty_response(self):
        m = RelevancyMetric()
        r = m.evaluate(query="some query", response="")
        assert not r.passed

    def test_details(self):
        m = RelevancyMetric()
        r = m.evaluate(query="capital France", response="The capital of France is Paris.")
        assert "matched" in r.details


class TestContextPrecision:
    def test_precise_context(self):
        m = ContextPrecision()
        r = m.evaluate(
            context="Machine learning uses algorithms. Deep learning uses neural networks.",
            reference="Machine learning algorithms are powerful.",
        )
        assert r.score >= 0.5

    def test_irrelevant_context(self):
        m = ContextPrecision()
        r = m.evaluate(
            context="The weather is sunny. Apples are tasty.",
            reference="Quantum computing uses qubits.",
        )
        assert r.score < 0.5

    def test_empty_context(self):
        m = ContextPrecision()
        r = m.evaluate(context="", reference="something")
        assert not r.passed

    def test_empty_reference(self):
        m = ContextPrecision()
        r = m.evaluate(context="Some context.", reference="")
        assert not r.passed
