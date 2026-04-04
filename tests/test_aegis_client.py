"""Tests for the main Aegis client — init, decorators, trace context manager."""

from __future__ import annotations

import pytest

from aegis import Aegis, AutonomyMode
from aegis.core.guard_levels import GuardLevel
from aegis.core.trace import get_collector


@pytest.fixture(autouse=True)
def _clear_collector():
    get_collector().clear()
    yield
    get_collector().clear()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestAegisInit:
    def test_basic(self):
        a = Aegis(workspace="org1", api_key="k")
        assert a.workspace == "org1"
        assert a.autonomy == AutonomyMode.MONITOR
        assert a.modules == ["observe"]

    def test_autonomy_string(self):
        a = Aegis(workspace="x", autonomy="full-auto")
        assert a.autonomy == AutonomyMode.FULL_AUTO

    def test_autonomy_enum(self):
        a = Aegis(workspace="x", autonomy=AutonomyMode.SEMI_AUTO)
        assert a.autonomy == AutonomyMode.SEMI_AUTO

    def test_invalid_autonomy(self):
        with pytest.raises(ValueError):
            Aegis(workspace="x", autonomy="yolo")

    def test_invalid_module(self):
        with pytest.raises(ValueError, match="Unknown modules"):
            Aegis(workspace="x", modules=["observe", "alien"])

    def test_multiple_modules(self):
        a = Aegis(workspace="x", modules=["observe", "guard", "evaluate"])
        assert set(a.modules) == {"observe", "guard", "evaluate"}

    def test_tenant_created(self):
        a = Aegis(workspace="acme")
        assert a.tenant.workspace == "acme"
        assert len(a.tenant_id) == 16

    def test_config_accessible(self):
        a = Aegis(workspace="org", api_key="key", modules=["guard"], autonomy="semi-auto")
        assert a.config.workspace == "org"
        assert a.config.api_key == "key"
        assert a.config.autonomy == "semi-auto"


# ---------------------------------------------------------------------------
# @aegis.observe()
# ---------------------------------------------------------------------------


class TestObserveDecorator:
    def test_basic(self):
        a = Aegis(workspace="obs-org")

        @a.observe("my-op")
        def my_func():
            return 42

        result = my_func()
        assert result == 42
        spans = get_collector().spans
        assert len(spans) == 1
        assert spans[0].name == "my-op"

    def test_preserves_function_name(self):
        a = Aegis(workspace="x")

        @a.observe("op")
        def original_name():
            pass

        assert original_name.__name__ == "original_name"

    def test_tenant_on_span(self):
        a = Aegis(workspace="tenant-org")

        @a.observe("traced")
        def work():
            return "done"

        work()
        span = get_collector().spans[0]
        assert span.workspace == "tenant-org"
        assert span.tenant_id == a.tenant_id

    def test_default_name_from_qualname(self):
        a = Aegis(workspace="x")

        @a.observe()
        def auto_named():
            pass

        auto_named()
        assert "auto_named" in get_collector().spans[0].name

    def test_exception_propagates(self):
        a = Aegis(workspace="x")

        @a.observe("fail")
        def bad():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            bad()
        span = get_collector().spans[0]
        assert span.error == "boom"

    def test_with_args_and_kwargs(self):
        a = Aegis(workspace="x")

        @a.observe("add")
        def add(x, y, extra=0):
            return x + y + extra

        assert add(1, 2, extra=10) == 13

    def test_observe_module_attribute(self):
        a = Aegis(workspace="x")

        @a.observe("op")
        def fn():
            pass

        fn()
        assert get_collector().spans[0].attributes["aegis.module"] == "observe"


# ---------------------------------------------------------------------------
# @aegis.protect()
# ---------------------------------------------------------------------------


class TestProtectDecorator:
    def test_basic(self):
        a = Aegis(workspace="x", modules=["guard"])

        @a.protect("check", level="N2")
        def process(data):
            return data.upper()

        assert process("hello") == "HELLO"
        spans = get_collector().spans
        assert len(spans) == 1
        assert spans[0].attributes["aegis.guard.level"] == "N2"

    def test_default_level_n2(self):
        a = Aegis(workspace="x", modules=["guard"])

        @a.protect("rule")
        def fn():
            pass

        fn()
        assert get_collector().spans[0].attributes["aegis.guard.level"] == "N2"

    def test_level_enum(self):
        a = Aegis(workspace="x", modules=["guard"])

        @a.protect("rule", level=GuardLevel.N4)
        def fn():
            pass

        fn()
        assert get_collector().spans[0].attributes["aegis.guard.level"] == "N4"

    def test_guard_rule_name(self):
        a = Aegis(workspace="x", modules=["guard"])

        @a.protect("pii-filter", level="N3")
        def fn():
            pass

        fn()
        assert get_collector().spans[0].attributes["aegis.guard.rule"] == "pii-filter"

    def test_tenant_propagation(self):
        a = Aegis(workspace="guard-org", modules=["guard"])

        @a.protect("rule")
        def fn():
            pass

        fn()
        span = get_collector().spans[0]
        assert span.workspace == "guard-org"
        assert span.tenant_id == a.tenant_id


# ---------------------------------------------------------------------------
# aegis.trace() context manager
# ---------------------------------------------------------------------------


class TestTraceContextManager:
    def test_basic(self):
        a = Aegis(workspace="tr-org")
        with a.trace("my-span") as span:
            span.set_attribute("model", "claude")
        assert span.name == "my-span"
        assert span.attributes["model"] == "claude"
        assert span.duration_ms >= 0

    def test_collects_span(self):
        a = Aegis(workspace="x")
        with a.trace("op"):
            pass
        assert len(get_collector().spans) == 1

    def test_error_status(self):
        a = Aegis(workspace="x")
        with pytest.raises(ValueError):
            with a.trace("fail") as span:
                raise ValueError("bad")
        assert span.error == "bad"

    def test_nested_traces(self):
        a = Aegis(workspace="x")
        with a.trace("parent") as parent:
            with a.trace("child") as child:
                pass
        assert child.parent_id == parent.span_id

    def test_attributes_at_creation(self):
        a = Aegis(workspace="x")
        with a.trace("op", framework="custom") as span:
            pass
        assert span.attributes["framework"] == "custom"


# ---------------------------------------------------------------------------
# Autonomy modes
# ---------------------------------------------------------------------------


class TestAutonomyMode:
    def test_all_values(self):
        assert AutonomyMode.MONITOR.value == "monitor"
        assert AutonomyMode.SEMI_AUTO.value == "semi-auto"
        assert AutonomyMode.FULL_AUTO.value == "full-auto"

    def test_string_conversion(self):
        assert AutonomyMode("monitor") == AutonomyMode.MONITOR
        assert AutonomyMode("semi-auto") == AutonomyMode.SEMI_AUTO
        assert AutonomyMode("full-auto") == AutonomyMode.FULL_AUTO
