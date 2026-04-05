"""Tests for the full AEGIS-X5 dashboard — HTML + API endpoints."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from aegis.core.trace import Span, SpanStatus
from aegis.dashboard.html import DASHBOARD_HTML
from aegis.local.store import LocalStore

try:
    from fastapi.testclient import TestClient

    _HAS_TESTCLIENT = True
except ImportError:
    _HAS_TESTCLIENT = False


# ---------------------------------------------------------------------------
# HTML validation
# ---------------------------------------------------------------------------

class TestDashboardHTML:
    def test_has_doctype(self) -> None:
        assert "<!DOCTYPE html>" in DASHBOARD_HTML

    def test_has_title(self) -> None:
        assert "<title>AEGIS-X5 Dashboard</title>" in DASHBOARD_HTML

    def test_has_5_views(self) -> None:
        assert 'id="v-overview"' in DASHBOARD_HTML
        assert 'id="v-agents"' in DASHBOARD_HTML
        assert 'id="v-guard"' in DASHBOARD_HTML
        assert 'id="v-predictions"' in DASHBOARD_HTML
        assert 'id="v-traces"' in DASHBOARD_HTML

    def test_has_sidebar(self) -> None:
        assert 'class="sidebar"' in DASHBOARD_HTML

    def test_has_nav_buttons(self) -> None:
        assert "showView('overview')" in DASHBOARD_HTML
        assert "showView('agents')" in DASHBOARD_HTML
        assert "showView('guard')" in DASHBOARD_HTML
        assert "showView('predictions')" in DASHBOARD_HTML
        assert "showView('traces')" in DASHBOARD_HTML

    def test_has_dark_theme(self) -> None:
        assert "--bg: #0a0e17" in DASHBOARD_HTML
        assert "--gold: #f59e0b" in DASHBOARD_HTML
        assert "--cyan: #06b6d4" in DASHBOARD_HTML

    def test_has_auto_refresh(self) -> None:
        assert "setInterval(refresh" in DASHBOARD_HTML

    def test_has_dashboard_api_calls(self) -> None:
        assert "/api/v1/dashboard/overview" in DASHBOARD_HTML
        assert "/api/v1/dashboard/agents" in DASHBOARD_HTML
        assert "/api/v1/dashboard/guard" in DASHBOARD_HTML
        assert "/api/v1/dashboard/predictions" in DASHBOARD_HTML
        assert "/api/v1/dashboard/traces" in DASHBOARD_HTML

    def test_has_workspace_filter(self) -> None:
        assert 'id="ws-filter"' in DASHBOARD_HTML

    def test_has_agent_search(self) -> None:
        assert 'id="agent-search"' in DASHBOARD_HTML

    def test_has_trace_filters(self) -> None:
        assert 'id="trace-search"' in DASHBOARD_HTML
        assert 'id="trace-status-filter"' in DASHBOARD_HTML

    def test_has_health_bar(self) -> None:
        assert "health-bar" in DASHBOARD_HTML

    def test_has_sort_agents(self) -> None:
        assert "sortAgents" in DASHBOARD_HTML


# ---------------------------------------------------------------------------
# Helper: populate store with test data
# ---------------------------------------------------------------------------

def _populate_store(store: LocalStore, count: int = 20) -> None:
    """Add test traces to a store."""
    for i in range(count):
        span = Span(
            name=f"agent-{i % 5}:operation-{i}",
            workspace="shield-ops-x5",
            tenant_id="test",
        )
        span.start_time = time.time() - (count - i) * 60
        span.end_time = span.start_time + 0.1 + (i % 10) * 0.05
        span.set_attribute("model", "claude-sonnet")
        span.set_attribute("tokens", 500 + i * 10)
        span.set_attribute("cost", 0.002 + i * 0.001)
        span.set_attribute("faithfulness", 0.95 - i * 0.002)
        span.set_attribute("aegis.guard.status", "PASS")

        if i % 7 == 0:
            span.status = SpanStatus.ERROR
            span.error = "Guard N4: Safety assertion violation detected"

        store.store_span(span)


# ---------------------------------------------------------------------------
# Dashboard API endpoints
# ---------------------------------------------------------------------------

@pytest.fixture()
def populated_client(tmp_path: Path) -> "TestClient | None":
    if not _HAS_TESTCLIENT:
        pytest.skip("FastAPI not installed")
    from aegis.dashboard.server import create_app

    db_path = str(tmp_path / "dash.db")
    store = LocalStore(db_path=db_path)
    _populate_store(store, count=30)

    app = create_app(db_path=db_path)
    return TestClient(app)


class TestDashboardOverview:
    def test_overview_endpoint(self, populated_client: "TestClient") -> None:
        r = populated_client.get("/api/v1/dashboard/overview")
        assert r.status_code == 200
        data = r.json()
        assert "total_traces" in data
        assert "active_agents" in data
        assert "avg_health" in data
        assert "total_cost" in data
        assert "guard_blocks" in data
        assert "avg_faithfulness" in data
        assert "alerts" in data

    def test_overview_has_data(self, populated_client: "TestClient") -> None:
        data = populated_client.get("/api/v1/dashboard/overview").json()
        assert data["total_traces"] == 30
        assert data["active_agents"] >= 1
        assert data["guard_blocks"] >= 1

    def test_overview_cost_computed(self, populated_client: "TestClient") -> None:
        data = populated_client.get("/api/v1/dashboard/overview").json()
        assert data["total_cost"] > 0

    def test_overview_alerts(self, populated_client: "TestClient") -> None:
        data = populated_client.get("/api/v1/dashboard/overview").json()
        assert len(data["alerts"]) >= 1


class TestDashboardAgents:
    def test_agents_endpoint(self, populated_client: "TestClient") -> None:
        r = populated_client.get("/api/v1/dashboard/agents")
        assert r.status_code == 200
        data = r.json()
        assert "agents" in data
        assert "count" in data
        assert data["count"] >= 1

    def test_agent_fields(self, populated_client: "TestClient") -> None:
        data = populated_client.get("/api/v1/dashboard/agents").json()
        agent = data["agents"][0]
        assert "name" in agent
        assert "health_score" in agent
        assert "total_traces" in agent
        assert "avg_latency_ms" in agent
        assert "guard_blocks" in agent
        assert "last_seen" in agent

    def test_health_scores_valid(self, populated_client: "TestClient") -> None:
        data = populated_client.get("/api/v1/dashboard/agents").json()
        for agent in data["agents"]:
            assert 0 <= agent["health_score"] <= 100


class TestDashboardGuard:
    def test_guard_endpoint(self, populated_client: "TestClient") -> None:
        r = populated_client.get("/api/v1/dashboard/guard")
        assert r.status_code == 200
        data = r.json()
        assert "total_blocks" in data
        assert "pii_blocks" in data
        assert "injection_blocks" in data
        assert "hallucination_blocks" in data
        assert "events" in data

    def test_guard_has_blocks(self, populated_client: "TestClient") -> None:
        data = populated_client.get("/api/v1/dashboard/guard").json()
        assert data["total_blocks"] >= 1
        assert len(data["events"]) >= 1

    def test_guard_event_fields(self, populated_client: "TestClient") -> None:
        data = populated_client.get("/api/v1/dashboard/guard").json()
        if data["events"]:
            event = data["events"][0]
            assert "name" in event
            assert "level" in event
            assert "message" in event
            assert "time" in event


class TestDashboardPredictions:
    def test_predictions_endpoint(self, populated_client: "TestClient") -> None:
        r = populated_client.get("/api/v1/dashboard/predictions")
        assert r.status_code == 200
        data = r.json()
        assert "avg_health" in data
        assert "health_distribution" in data
        assert "drift_alerts" in data
        assert "anomaly_count" in data
        assert "anomalies" in data

    def test_health_distribution(self, populated_client: "TestClient") -> None:
        data = populated_client.get("/api/v1/dashboard/predictions").json()
        dist = data["health_distribution"]
        assert "0-59" in dist
        assert "60-79" in dist
        assert "80-100" in dist
        total = sum(dist.values())
        assert total >= 1


class TestDashboardTraces:
    def test_traces_endpoint(self, populated_client: "TestClient") -> None:
        r = populated_client.get("/api/v1/dashboard/traces")
        assert r.status_code == 200
        data = r.json()
        assert "traces" in data
        assert "count" in data

    def test_traces_limit(self, populated_client: "TestClient") -> None:
        data = populated_client.get("/api/v1/dashboard/traces?limit=5").json()
        assert data["count"] <= 5

    def test_traces_status_filter(self, populated_client: "TestClient") -> None:
        data = populated_client.get("/api/v1/dashboard/traces?status=error").json()
        for t in data["traces"]:
            assert t["status"] == "error"

    def test_traces_name_filter(self, populated_client: "TestClient") -> None:
        data = populated_client.get("/api/v1/dashboard/traces?name=agent-0").json()
        for t in data["traces"]:
            assert "agent-0" in t["name"].lower()


class TestDashboardHTMLServed:
    def test_index_serves_html(self, populated_client: "TestClient") -> None:
        r = populated_client.get("/")
        assert r.status_code == 200
        assert "AEGIS-X5" in r.text
        assert "<!DOCTYPE html>" in r.text

    def test_dashboard_route(self, populated_client: "TestClient") -> None:
        r = populated_client.get("/dashboard")
        assert r.status_code == 200
        assert "v-overview" in r.text


class TestWorkspaceFilter:
    def test_overview_with_workspace(self, populated_client: "TestClient") -> None:
        data = populated_client.get("/api/v1/dashboard/overview?workspace=shield-ops-x5").json()
        assert data["total_traces"] > 0

    def test_overview_nonexistent_workspace(self, populated_client: "TestClient") -> None:
        data = populated_client.get("/api/v1/dashboard/overview?workspace=nonexistent").json()
        assert data["total_traces"] == 0
