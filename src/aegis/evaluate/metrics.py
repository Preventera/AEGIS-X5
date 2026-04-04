"""Evaluation metrics — ABC + built-in metrics."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MetricResult:
    """Outcome of a single metric evaluation."""

    name: str
    score: float  # 0.0–1.0
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)


class EvalMetric(abc.ABC):
    """Abstract evaluation metric — implement :meth:`evaluate` to create custom metrics."""

    def __init__(self, name: str, *, threshold: float = 0.5) -> None:
        self.name = name
        self.threshold = threshold

    @abc.abstractmethod
    def evaluate(
        self,
        *,
        query: str = "",
        response: str = "",
        context: str = "",
        reference: str = "",
        **kwargs: Any,
    ) -> MetricResult:
        ...


# ---------------------------------------------------------------------------
# Built-in: FaithfulnessMetric
# ---------------------------------------------------------------------------


class FaithfulnessMetric(EvalMetric):
    """Measures how faithful the response is to the provided context.

    Heuristic: fraction of response sentences whose key terms appear in context.
    """

    def __init__(self, *, threshold: float = 0.5) -> None:
        super().__init__("faithfulness", threshold=threshold)

    def evaluate(
        self,
        *,
        query: str = "",
        response: str = "",
        context: str = "",
        reference: str = "",
        **kwargs: Any,
    ) -> MetricResult:
        if not response or not context:
            return MetricResult(name=self.name, score=0.0, passed=False)

        sentences = _split_sentences(response)
        if not sentences:
            return MetricResult(name=self.name, score=0.0, passed=False)

        ctx_lower = context.lower()
        grounded = sum(1 for s in sentences if _sentence_grounded(s, ctx_lower))
        score = grounded / len(sentences)
        return MetricResult(
            name=self.name,
            score=round(score, 4),
            passed=score >= self.threshold,
            details={"grounded": grounded, "total": len(sentences)},
        )


# ---------------------------------------------------------------------------
# Built-in: RelevancyMetric
# ---------------------------------------------------------------------------


class RelevancyMetric(EvalMetric):
    """Measures how relevant the response is to the query.

    Heuristic: fraction of query key-words present in the response.
    """

    def __init__(self, *, threshold: float = 0.5) -> None:
        super().__init__("relevancy", threshold=threshold)

    def evaluate(
        self,
        *,
        query: str = "",
        response: str = "",
        context: str = "",
        reference: str = "",
        **kwargs: Any,
    ) -> MetricResult:
        if not query or not response:
            return MetricResult(name=self.name, score=0.0, passed=False)

        keywords = _extract_keywords(query)
        if not keywords:
            return MetricResult(name=self.name, score=1.0, passed=True)

        resp_lower = response.lower()
        found = sum(1 for kw in keywords if kw in resp_lower)
        score = found / len(keywords)
        return MetricResult(
            name=self.name,
            score=round(score, 4),
            passed=score >= self.threshold,
            details={"matched": found, "total": len(keywords)},
        )


# ---------------------------------------------------------------------------
# Built-in: ContextPrecision
# ---------------------------------------------------------------------------


class ContextPrecision(EvalMetric):
    """Measures precision of context vs. reference answer.

    Heuristic: fraction of context sentences that contain reference key-words.
    """

    def __init__(self, *, threshold: float = 0.5) -> None:
        super().__init__("context_precision", threshold=threshold)

    def evaluate(
        self,
        *,
        query: str = "",
        response: str = "",
        context: str = "",
        reference: str = "",
        **kwargs: Any,
    ) -> MetricResult:
        if not context or not reference:
            return MetricResult(name=self.name, score=0.0, passed=False)

        ctx_sentences = _split_sentences(context)
        if not ctx_sentences:
            return MetricResult(name=self.name, score=0.0, passed=False)

        ref_kw = _extract_keywords(reference)
        if not ref_kw:
            return MetricResult(name=self.name, score=1.0, passed=True)

        relevant = sum(
            1 for s in ctx_sentences if any(kw in s.lower() for kw in ref_kw)
        )
        score = relevant / len(ctx_sentences)
        return MetricResult(
            name=self.name,
            score=round(score, 4),
            passed=score >= self.threshold,
            details={"relevant": relevant, "total": len(ctx_sentences)},
        )


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset(
    "a an the is are was were be been being have has had do does did will would "
    "shall should may might can could of in to for on with at by from as into "
    "through during before after above below between out off over under about "
    "and but or nor not no so yet both either neither each every all any few "
    "more most other some such than too very it its this that these those i me "
    "my we our you your he him his she her they them their what which who whom "
    "how when where why".split()
)


def _extract_keywords(text: str) -> list[str]:
    words = text.lower().split()
    return [w.strip(".,!?;:\"'()") for w in words if w.strip(".,!?;:\"'()") not in _STOP_WORDS and len(w) > 2]


def _split_sentences(text: str) -> list[str]:
    import re
    parts = re.split(r"[.!?]+", text)
    return [s.strip() for s in parts if s.strip()]


def _sentence_grounded(sentence: str, context_lower: str) -> bool:
    keywords = _extract_keywords(sentence)
    if not keywords:
        return True
    matched = sum(1 for kw in keywords if kw in context_lower)
    return matched / len(keywords) >= 0.5
