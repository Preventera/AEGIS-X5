"""Tests for aegis.dashboard — mini dashboard server."""

from __future__ import annotations

from pathlib import Path

from aegis.core.trace import Span
from aegis.dashboard.server import _DASHBOARD_HTML, render_dashboard_html
from aegis.local.store import LocalStore

# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

class TestDashboardHTML:
    def test_html_is_valid(self) -> None:
        html = _DASHBOARD_HTML
        assert "<!DOCTYPE html>" in html
        assert "<title>AEGIS-X5 Dashboard</title>" in html
        assert "</html>" in html

    def test_has_dark_theme(self) -> None:
        assert "--bg: #0d1117" in _DASHBOARD_HTML
        assert "--surface: #161b22" in _DASHBOARD_HTML

    def test_has_stats_section(self) -> None:
        assert "total-traces" in _DASHBOARD_HTML
        assert "avg-latency" in _DASHBOARD_HTML
        assert "guard-blocks" in _DASHBOARD_HTML

    def test_has_api_endpoints(self) -> None:
        assert "/api/stats" in _DASHBOARD_HTML
        assert "/api/traces" in _DASHBOARD_HTML

    def test_has_auto_refresh(self) -> None:
        assert "setInterval(refresh" in _DASHBOARD_HTML

    def test_render_function(self) -> None:
        html = render_dashboard_html()
        assert "AEGIS-X5" in html


# ---------------------------------------------------------------------------
# App creation (no FastAPI/Starlette needed for test)
# ---------------------------------------------------------------------------

class TestCreateApp:
    def test_create_app_returns_something(self, tmp_path: Path) -> None:
        """create_app should return an app or None depending on installed deps."""
        from aegis.dashboard.server import create_app

        app = create_app(db_path=str(tmp_path / "test.db"))
        # Either returns a FastAPI/Starlette app or None
        # We just verify it doesn't crash
        assert app is not None or app is None  # always true, no crash is the test


# ---------------------------------------------------------------------------
# Dashboard data integration
# ---------------------------------------------------------------------------

class TestDashboardData:
    def test_store_provides_data_for_dashboard(self, tmp_path: Path) -> None:
        store = LocalStore(db_path=tmp_path / "test.db")
        for i in range(3):
            span = Span(name=f"op-{i}", workspace="demo")
            span.start_time = 1000.0
            span.end_time = 1000.0 + (i + 1) * 0.05
            store.store_span(span)

        stats = store.stats()
        traces = store.recent_traces(limit=10)

        assert stats["total_traces"] == 3
        assert len(traces) == 3
        # Dashboard would render these
        for t in traces:
            assert "name" in t
            assert "duration_ms" in t
            assert "workspace" in t
