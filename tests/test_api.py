"""Tests for aegis.api — REST API endpoints."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from aegis.api.auth import require_api_key

# Try to import FastAPI test client
try:
    from fastapi.testclient import TestClient

    _HAS_TESTCLIENT = True
except ImportError:
    _HAS_TESTCLIENT = False


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuth:
    def test_no_keys_open_access(self) -> None:
        assert require_api_key("anything", valid_keys=[]) is True

    def test_valid_key(self) -> None:
        assert require_api_key("key-1", valid_keys=["key-1", "key-2"]) is True

    def test_invalid_key(self) -> None:
        assert require_api_key("bad", valid_keys=["key-1"]) is False

    def test_empty_key(self) -> None:
        assert require_api_key("", valid_keys=["key-1"]) is False


# ---------------------------------------------------------------------------
# API endpoints (requires FastAPI)
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path: Path) -> TestClient | None:
    if not _HAS_TESTCLIENT:
        pytest.skip("FastAPI not installed")
    from aegis.api.app import create_api

    app = create_api(db_path=str(tmp_path / "test.db"), api_keys=[])
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self, client: TestClient) -> None:
        if client is None:
            pytest.skip("No test client")
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestTraceEndpoint:
    def test_record_trace(self, client: TestClient) -> None:
        if client is None:
            pytest.skip("No test client")
        r = client.post("/api/v1/trace", json={
            "name": "test-span",
            "workspace": "test",
            "start_time": time.time() - 0.1,
            "end_time": time.time(),
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "span_id" in data

    def test_trace_default_values(self, client: TestClient) -> None:
        if client is None:
            pytest.skip("No test client")
        r = client.post("/api/v1/trace", json={})
        assert r.status_code == 200


class TestGuardEndpoint:
    def test_validate_clean(self, client: TestClient) -> None:
        if client is None:
            pytest.skip("No test client")
        r = client.post("/api/v1/guard/validate", json={
            "content": "This is a perfectly normal response about weather."
        })
        assert r.status_code == 200
        data = r.json()
        assert data["passed"] is True

    def test_validate_pii(self, client: TestClient) -> None:
        if client is None:
            pytest.skip("No test client")
        r = client.post("/api/v1/guard/validate", json={
            "content": "Contact john@example.com or call 555-123-4567"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["passed"] is False


class TestAgentsEndpoint:
    def test_list_agents_empty(self, client: TestClient) -> None:
        if client is None:
            pytest.skip("No test client")
        r = client.get("/api/v1/agents")
        assert r.status_code == 200
        data = r.json()
        assert data["count"] == 0

    def test_list_agents_after_trace(self, client: TestClient) -> None:
        if client is None:
            pytest.skip("No test client")
        # Record a trace first
        client.post("/api/v1/trace", json={
            "name": "agent-op",
            "workspace": "agent-1",
        })
        r = client.get("/api/v1/agents")
        data = r.json()
        assert data["count"] >= 1


class TestPredictionsEndpoint:
    def test_list_predictions(self, client: TestClient) -> None:
        if client is None:
            pytest.skip("No test client")
        r = client.get("/api/v1/predictions")
        assert r.status_code == 200
        data = r.json()
        assert "pending" in data
        assert "accuracy" in data


class TestStatsEndpoint:
    def test_get_stats(self, client: TestClient) -> None:
        if client is None:
            pytest.skip("No test client")
        r = client.get("/api/v1/stats")
        assert r.status_code == 200
        data = r.json()
        assert "total_traces" in data


class TestTracesEndpoint:
    def test_get_traces(self, client: TestClient) -> None:
        if client is None:
            pytest.skip("No test client")
        r = client.get("/api/v1/traces")
        assert r.status_code == 200
        data = r.json()
        assert "traces" in data


# ---------------------------------------------------------------------------
# API key authentication
# ---------------------------------------------------------------------------

class TestAPIKeyAuth:
    def test_auth_required(self, tmp_path: Path) -> None:
        if not _HAS_TESTCLIENT:
            pytest.skip("FastAPI not installed")
        from aegis.api.app import create_api

        app = create_api(
            db_path=str(tmp_path / "auth.db"),
            api_keys=["secret-key-123"],
        )
        client = TestClient(app)

        # Health is public
        r = client.get("/api/v1/health")
        assert r.status_code == 200

        # Trace requires key
        r = client.post("/api/v1/trace", json={"name": "test"})
        assert r.status_code == 401

        # With valid key
        r = client.post(
            "/api/v1/trace",
            json={"name": "test"},
            headers={"X-API-Key": "secret-key-123"},
        )
        assert r.status_code == 200
