"""Cost calculation — configurable per-model pricing."""

from __future__ import annotations

from dataclasses import dataclass

from aegis.observe.tokens import TokenUsage

# ---------------------------------------------------------------------------
# Default pricing table (USD per 1M tokens) — users override via configure()
# ---------------------------------------------------------------------------

_DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet": {"input": 3.0, "output": 15.0},
    "claude-haiku": {"input": 0.25, "output": 1.25},
    "claude-opus": {"input": 15.0, "output": 75.0},
    "gpt-4o": {"input": 2.5, "output": 10.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}


@dataclass(frozen=True)
class CostResult:
    """Computed cost for a single LLM call."""

    model: str
    input_cost: float
    output_cost: float
    total_cost: float
    currency: str = "USD"


class CostCalculator:
    """Configurable per-model cost calculator.

    Usage::

        calc = CostCalculator()
        calc.set_price("my-model", input=5.0, output=20.0)
        cost = calc.compute(usage, model="my-model")
    """

    def __init__(self, pricing: dict[str, dict[str, float]] | None = None) -> None:
        self._pricing = dict(_DEFAULT_PRICING)
        if pricing:
            self._pricing.update(pricing)

    @property
    def pricing(self) -> dict[str, dict[str, float]]:
        return dict(self._pricing)

    def set_price(self, model: str, *, input: float, output: float) -> None:
        """Set or update pricing for a model (USD per 1M tokens)."""
        self._pricing[model] = {"input": input, "output": output}

    def remove_price(self, model: str) -> None:
        """Remove pricing for a model."""
        self._pricing.pop(model, None)

    def _resolve_model(self, model: str) -> dict[str, float] | None:
        """Find pricing — try exact match, then prefix match."""
        if model in self._pricing:
            return self._pricing[model]
        for key in self._pricing:
            if model.startswith(key):
                return self._pricing[key]
        return None

    def compute(self, usage: TokenUsage, *, model: str) -> CostResult:
        """Compute cost for a token usage against a model's pricing.

        Returns zero costs if the model has no configured pricing.
        """
        prices = self._resolve_model(model)
        if prices is None:
            return CostResult(model=model, input_cost=0.0, output_cost=0.0, total_cost=0.0)

        input_cost = (usage.input_tokens / 1_000_000) * prices["input"]
        output_cost = (usage.output_tokens / 1_000_000) * prices["output"]
        return CostResult(
            model=model,
            input_cost=round(input_cost, 8),
            output_cost=round(output_cost, 8),
            total_cost=round(input_cost + output_cost, 8),
        )
