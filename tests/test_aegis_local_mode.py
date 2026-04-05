"""Tests for Aegis client in local (standalone) mode."""

from __future__ import annotations

from pathlib import Path

import pytest

from aegis import Aegis
from aegis.core.trace import get_collector


@pytest.fixture(autouse=True)
def _clear_collector() -> None:
    get_collector().clear()


@pytest.fixture()
def local_aegis(tmp_path: Path) -> Aegis:
    """Aegis client in local mode with temp DB."""
    return Aegis(workspace="test-local", local_db=str(tmp_path / "test.db"), verbose=False)


# ---------------------------------------------------------------------------
# Standalone mode activation
# ---------------------------------------------------------------------------

class TestLocalModeActivation:
    def test_no_args_is_local(self, tmp_path: Path) -> None:
        a = Aegis(local_db=str(tmp_path / "t.db"), verbose=False)
        assert a.is_local is True
        assert a.workspace == "local"

    def test_api_key_is_cloud(self) -> None:
        a = Aegis(workspace="org", api_key="ak_test")
        assert a.is_local is False

    def test_local_store_created(self, local_aegis: Aegis) -> None:
        assert local_aegis.local_store is not None

    def test_cloud_mode_no_local_store(self) -> None:
        a = Aegis(workspace="org", api_key="ak_test")
        assert a.local_store is None


# ---------------------------------------------------------------------------
# Framework auto-detection
# ---------------------------------------------------------------------------

class TestFrameworkDetection:
    def test_detects_installed_packages(self, local_aegis: Aegis) -> None:
        # At minimum, we should get a list (possibly empty in test env)
        frameworks = local_aegis.detected_frameworks
        assert isinstance(frameworks, list)

    def test_returns_list_copy(self, local_aegis: Aegis) -> None:
        f1 = local_aegis.detected_frameworks
        f2 = local_aegis.detected_frameworks
        assert f1 is not f2  # returns copies


# ---------------------------------------------------------------------------
# observe in local mode
# ---------------------------------------------------------------------------

class TestLocalObserve:
    def test_observe_stores_to_sqlite(self, local_aegis: Aegis) -> None:
        @local_aegis.observe("test-fn")
        def my_func() -> str:
            return "ok"

        result = my_func()
        assert result == "ok"

        traces = local_aegis.local_store.recent_traces()
        assert len(traces) == 1
        assert traces[0]["name"] == "test-fn"

    def test_observe_preserves_function_name(self, local_aegis: Aegis) -> None:
        @local_aegis.observe("tracked")
        def original_name() -> None:
            pass

        assert original_name.__name__ == "original_name"

    def test_observe_passes_args(self, local_aegis: Aegis) -> None:
        @local_aegis.observe("add")
        def add(a: int, b: int) -> int:
            return a + b

        assert add(3, 4) == 7

    def test_multiple_calls_multiple_traces(self, local_aegis: Aegis) -> None:
        @local_aegis.observe("repeat")
        def noop() -> None:
            pass

        for _ in range(5):
            noop()
        assert local_aegis.local_store.stats()["total_traces"] == 5


# ---------------------------------------------------------------------------
# protect in local mode
# ---------------------------------------------------------------------------

class TestLocalProtect:
    def test_protect_stores_to_sqlite(self, local_aegis: Aegis) -> None:
        @local_aegis.protect("safety-check", level="N2")
        def guarded() -> str:
            return "safe"

        result = guarded()
        assert result == "safe"

        traces = local_aegis.local_store.recent_traces()
        assert len(traces) == 1
        assert "guard:" in traces[0]["name"]

    def test_protect_preserves_function_name(self, local_aegis: Aegis) -> None:
        @local_aegis.protect("check")
        def protected_fn() -> None:
            pass

        assert protected_fn.__name__ == "protected_fn"


# ---------------------------------------------------------------------------
# trace context manager in local mode
# ---------------------------------------------------------------------------

class TestLocalTrace:
    def test_trace_stores_to_sqlite(self, local_aegis: Aegis) -> None:
        with local_aegis.trace("manual-span") as span:
            span.set_attribute("model", "test")

        traces = local_aegis.local_store.recent_traces()
        assert len(traces) == 1
        assert traces[0]["name"] == "manual-span"

    def test_trace_captures_duration(self, local_aegis: Aegis) -> None:
        import time

        with local_aegis.trace("timed") as _span:
            time.sleep(0.01)

        traces = local_aegis.local_store.recent_traces()
        assert traces[0]["duration_ms"] >= 5  # at least some duration


# ---------------------------------------------------------------------------
# Verbose terminal output
# ---------------------------------------------------------------------------

class TestVerboseOutput:
    def test_verbose_prints_summary(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        a = Aegis(workspace="test", local_db=str(tmp_path / "t.db"), verbose=True)

        @a.observe("verbose-test")
        def fn() -> str:
            return "ok"

        fn()
        captured = capsys.readouterr()
        assert "Trace captured" in captured.err
        assert "verbose-test" in captured.err

    def test_silent_when_not_verbose(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        a = Aegis(workspace="test", local_db=str(tmp_path / "t.db"), verbose=False)

        @a.observe("silent-test")
        def fn() -> str:
            return "ok"

        fn()
        captured = capsys.readouterr()
        assert captured.err == ""


# ---------------------------------------------------------------------------
# Backward compatibility — cloud mode unchanged
# ---------------------------------------------------------------------------

class TestCloudModeUnchanged:
    def test_observe_still_works(self) -> None:
        a = Aegis(workspace="org", api_key="ak_test")

        @a.observe("cloud-fn")
        def fn() -> str:
            return "cloud"

        assert fn() == "cloud"

    def test_protect_still_works(self) -> None:
        a = Aegis(workspace="org", api_key="ak_test")

        @a.protect("cloud-guard", level="N3")
        def fn() -> str:
            return "guarded"

        assert fn() == "guarded"

    def test_trace_still_works(self) -> None:
        a = Aegis(workspace="org", api_key="ak_test")
        with a.trace("cloud-trace") as span:
            span.set_attribute("key", "val")
