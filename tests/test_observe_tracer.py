"""Tests for aegis.observe.tracer — universal sync/async tracer."""

from __future__ import annotations

import asyncio

import pytest

from aegis.core.tenant import Tenant, TenantContext
from aegis.core.trace import get_collector
from aegis.observe.tracer import Tracer


@pytest.fixture(autouse=True)
def _clear():
    get_collector().clear()
    yield
    get_collector().clear()


class TestTracerSync:
    def test_basic_trace(self):
        tracer = Tracer()

        @tracer.trace("my-op")
        def work():
            return {"usage": {"input_tokens": 10, "output_tokens": 5}}

        result = work()
        assert result["usage"]["input_tokens"] == 10
        spans = get_collector().spans
        assert len(spans) == 1
        assert spans[0].name == "my-op"
        assert spans[0].attributes["aegis.tokens.total"] == 15

    def test_model_attribute(self):
        tracer = Tracer()

        @tracer.trace("call", model="claude-sonnet")
        def call():
            return {"usage": {"input_tokens": 100, "output_tokens": 50}}

        call()
        span = get_collector().spans[0]
        assert span.attributes["aegis.model"] == "claude-sonnet"
        assert span.attributes["aegis.cost.total"] > 0

    def test_no_tokens_no_cost(self):
        tracer = Tracer()

        @tracer.trace("plain")
        def fn():
            return "hello"

        fn()
        span = get_collector().spans[0]
        assert "aegis.tokens.total" not in span.attributes
        assert "aegis.cost.total" not in span.attributes

    def test_preserves_function_name(self):
        tracer = Tracer()

        @tracer.trace("op")
        def original():
            pass

        assert original.__name__ == "original"

    def test_exception_propagates(self):
        tracer = Tracer()

        @tracer.trace("fail")
        def bad():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            bad()
        span = get_collector().spans[0]
        assert span.error == "boom"

    def test_default_name(self):
        tracer = Tracer()

        @tracer.trace()
        def auto_named():
            return {}

        auto_named()
        assert "auto_named" in get_collector().spans[0].name

    def test_tenant_propagation(self):
        tenant = Tenant(workspace="org", tenant_id="t1")
        tracer = Tracer(tenant=tenant)

        @tracer.trace("op")
        def fn():
            return {}

        fn()
        span = get_collector().spans[0]
        assert span.workspace == "org"
        assert span.tenant_id == "t1"

    def test_tenant_from_context(self):
        tracer = Tracer()
        tenant = Tenant(workspace="ctx-org", tenant_id="ctx1")

        @tracer.trace("op")
        def fn():
            return {}

        with TenantContext(tenant):
            fn()

        span = get_collector().spans[0]
        assert span.workspace == "ctx-org"

    def test_latency_recorded(self):
        tracer = Tracer()

        @tracer.trace("op")
        def fn():
            import time
            time.sleep(0.001)  # Ensure non-zero duration
            return {}

        fn()
        assert tracer.metrics.count >= 1

    def test_custom_cost_calculator(self):
        from aegis.observe.cost import CostCalculator

        calc = CostCalculator(pricing={"test-model": {"input": 100.0, "output": 200.0}})
        tracer = Tracer(cost_calculator=calc)

        @tracer.trace("op", model="test-model")
        def fn():
            return {"usage": {"input_tokens": 1_000_000, "output_tokens": 500_000}}

        fn()
        span = get_collector().spans[0]
        assert span.attributes["aegis.cost.total"] == 200.0  # 100 + 100


class TestTracerAsync:
    def test_async_trace(self):
        tracer = Tracer()

        @tracer.trace("async-op")
        async def work():
            return {"usage": {"input_tokens": 20, "output_tokens": 10}}

        result = asyncio.run(work())
        assert result["usage"]["input_tokens"] == 20
        spans = get_collector().spans
        assert len(spans) == 1
        assert spans[0].name == "async-op"
        assert spans[0].attributes["aegis.tokens.total"] == 30

    def test_async_exception(self):
        tracer = Tracer()

        @tracer.trace("async-fail")
        async def bad():
            raise RuntimeError("async boom")

        with pytest.raises(RuntimeError, match="async boom"):
            asyncio.run(bad())
        span = get_collector().spans[0]
        assert span.error == "async boom"

    def test_async_preserves_name(self):
        tracer = Tracer()

        @tracer.trace("op")
        async def my_coro():
            return {}

        assert my_coro.__name__ == "my_coro"

    def test_async_with_model(self):
        tracer = Tracer()

        @tracer.trace("embed", model="gpt-4o")
        async def embed():
            return {"usage": {"prompt_tokens": 500, "completion_tokens": 0, "total_tokens": 500}}

        asyncio.run(embed())
        span = get_collector().spans[0]
        assert span.attributes["aegis.model"] == "gpt-4o"
        assert span.attributes["aegis.tokens.total"] == 500
