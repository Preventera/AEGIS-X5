"""Tests for aegis.observe.cost — configurable cost calculation."""

from __future__ import annotations

from aegis.observe.cost import CostCalculator, CostResult
from aegis.observe.tokens import TokenUsage


class TestCostCalculator:
    def test_default_pricing_exists(self):
        calc = CostCalculator()
        assert "claude-sonnet" in calc.pricing
        assert "gpt-4o" in calc.pricing

    def test_compute_known_model(self):
        calc = CostCalculator()
        usage = TokenUsage(input_tokens=1_000_000, output_tokens=500_000)
        cost = calc.compute(usage, model="claude-sonnet")
        assert cost.model == "claude-sonnet"
        assert cost.input_cost == 3.0  # 1M * $3/1M
        assert cost.output_cost == 7.5  # 0.5M * $15/1M
        assert cost.total_cost == 10.5
        assert cost.currency == "USD"

    def test_compute_unknown_model_zero(self):
        calc = CostCalculator()
        usage = TokenUsage(input_tokens=1000, output_tokens=500)
        cost = calc.compute(usage, model="unknown-model")
        assert cost.total_cost == 0.0

    def test_set_custom_price(self):
        calc = CostCalculator()
        calc.set_price("my-model", input=10.0, output=30.0)
        usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)
        cost = calc.compute(usage, model="my-model")
        assert cost.input_cost == 10.0
        assert cost.output_cost == 30.0

    def test_remove_price(self):
        calc = CostCalculator()
        calc.set_price("temp", input=1.0, output=2.0)
        calc.remove_price("temp")
        usage = TokenUsage(input_tokens=1000)
        cost = calc.compute(usage, model="temp")
        assert cost.total_cost == 0.0

    def test_prefix_match(self):
        calc = CostCalculator()
        # "claude-sonnet-4" should match "claude-sonnet" prefix
        usage = TokenUsage(input_tokens=1_000_000, output_tokens=0)
        cost = calc.compute(usage, model="claude-sonnet-4")
        assert cost.input_cost == 3.0

    def test_custom_pricing_at_init(self):
        calc = CostCalculator(pricing={"custom": {"input": 5.0, "output": 10.0}})
        assert "custom" in calc.pricing
        # Default still there
        assert "claude-sonnet" in calc.pricing

    def test_small_token_counts(self):
        calc = CostCalculator()
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        cost = calc.compute(usage, model="claude-sonnet")
        assert cost.total_cost > 0
        assert cost.total_cost < 0.01


class TestCostResult:
    def test_frozen(self):
        r = CostResult(model="x", input_cost=1.0, output_cost=2.0, total_cost=3.0)
        try:
            r.model = "y"  # type: ignore[misc]
            assert False, "should be frozen"
        except AttributeError:
            pass
