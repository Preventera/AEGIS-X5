"""Tests for aegis.connectors — all framework connectors and SDK wrappers."""

from __future__ import annotations

import time
from pathlib import Path
from uuid import uuid4

import pytest

from aegis import Aegis
from aegis.core.trace import Span, SpanStatus, get_collector


@pytest.fixture(autouse=True)
def _clear_collector() -> None:
    get_collector().clear()


@pytest.fixture()
def aegis_local(tmp_path: Path) -> Aegis:
    return Aegis(workspace="test-connectors", local_db=str(tmp_path / "c.db"), verbose=False)


# ---------------------------------------------------------------------------
# LangChain Connector
# ---------------------------------------------------------------------------

class TestLangChainConnector:
    def test_handler_creation(self, aegis_local: Aegis) -> None:
        handler = aegis_local.langchain_handler()
        assert handler is not None

    def test_llm_start_end_cycle(self, aegis_local: Aegis) -> None:
        handler = aegis_local.langchain_handler()
        run_id = uuid4()

        handler.on_llm_start(
            {"kwargs": {"model": "test-model"}, "id": ["TestLLM"]},
            ["test prompt"],
            run_id=run_id,
        )

        class MockResponse:
            llm_output = {"token_usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}}
            generations = [[type("G", (), {"text": "test output"})()]]

        handler.on_llm_end(MockResponse(), run_id=run_id)

        traces = aegis_local.local_store.recent_traces()
        assert len(traces) == 1
        assert "langchain:llm:test-model" in traces[0]["name"]

    def test_llm_error(self, aegis_local: Aegis) -> None:
        handler = aegis_local.langchain_handler()
        run_id = uuid4()

        handler.on_llm_start(
            {"kwargs": {"model": "m"}, "id": ["LLM"]},
            ["prompt"],
            run_id=run_id,
        )
        handler.on_llm_error(RuntimeError("test error"), run_id=run_id)

        traces = aegis_local.local_store.recent_traces()
        assert len(traces) == 1
        assert traces[0]["status"] == "error"

    def test_chain_start_end(self, aegis_local: Aegis) -> None:
        handler = aegis_local.langchain_handler()
        run_id = uuid4()

        handler.on_chain_start(
            {"id": ["RetrievalQA"]},
            {"query": "test"},
            run_id=run_id,
        )
        handler.on_chain_end({"result": "answer"}, run_id=run_id)

        traces = aegis_local.local_store.recent_traces()
        assert len(traces) == 1
        assert "langchain:chain:RetrievalQA" in traces[0]["name"]

    def test_chain_error(self, aegis_local: Aegis) -> None:
        handler = aegis_local.langchain_handler()
        run_id = uuid4()

        handler.on_chain_start({"id": ["Chain"]}, {}, run_id=run_id)
        handler.on_chain_error(ValueError("chain broke"), run_id=run_id)

        traces = aegis_local.local_store.recent_traces()
        assert len(traces) == 1
        assert traces[0]["status"] == "error"

    def test_no_response_tokens(self, aegis_local: Aegis) -> None:
        """Should handle response without token_usage."""
        handler = aegis_local.langchain_handler()
        run_id = uuid4()

        handler.on_llm_start({"kwargs": {}, "id": ["LLM"]}, ["p"], run_id=run_id)

        class MockResponse:
            llm_output = None
            generations = []

        handler.on_llm_end(MockResponse(), run_id=run_id)
        traces = aegis_local.local_store.recent_traces()
        assert len(traces) == 1


# ---------------------------------------------------------------------------
# CrewAI Connector
# ---------------------------------------------------------------------------

class TestCrewAIConnector:
    def test_middleware_creation(self, aegis_local: Aegis) -> None:
        mw = aegis_local.crewai_middleware()
        assert mw is not None

    def test_wrap_agent(self, aegis_local: Aegis) -> None:
        mw = aegis_local.crewai_middleware()

        def my_task(query: str) -> str:
            return f"result for {query}"

        wrapped = mw.wrap_agent("researcher", my_task)
        result = wrapped("test query")
        assert result == "result for test query"

        traces = aegis_local.local_store.recent_traces()
        assert len(traces) == 1
        assert "crewai:researcher" in traces[0]["name"]

    def test_wrap_task_direct(self, aegis_local: Aegis) -> None:
        mw = aegis_local.crewai_middleware()
        result = mw.wrap_task("writer", lambda: "draft", )
        assert result == "draft"

    def test_delegation_chain(self, aegis_local: Aegis) -> None:
        mw = aegis_local.crewai_middleware()
        mw.wrap_task("researcher", lambda: "research")
        mw.wrap_task("writer", lambda: "draft")
        mw.wrap_task("reviewer", lambda: "approved")

        assert mw.delegation_chain == ["researcher", "writer", "reviewer"]

    def test_task_results(self, aegis_local: Aegis) -> None:
        mw = aegis_local.crewai_middleware()
        mw.wrap_task("agent-1", lambda: "ok")

        results = mw.task_results
        assert len(results) == 1
        assert results[0]["agent"] == "agent-1"
        assert results[0]["success"] is True
        assert results[0]["duration_ms"] >= 0

    def test_reset(self, aegis_local: Aegis) -> None:
        mw = aegis_local.crewai_middleware()
        mw.wrap_task("a", lambda: "x")
        mw.reset()
        assert mw.delegation_chain == []
        assert mw.task_results == []

    def test_preserves_function_name(self, aegis_local: Aegis) -> None:
        mw = aegis_local.crewai_middleware()

        def original_fn() -> str:
            return "ok"

        wrapped = mw.wrap_agent("test", original_fn)
        assert wrapped.__name__ == "original_fn"


# ---------------------------------------------------------------------------
# OpenAI Connector
# ---------------------------------------------------------------------------

class TestOpenAIConnector:
    def _mock_openai(self) -> object:
        class Usage:
            prompt_tokens = 50
            completion_tokens = 100
            total_tokens = 150

        class Response:
            usage = Usage()

        class Completions:
            def create(self, **kwargs):
                return Response()

        class Chat:
            completions = Completions()

        class Client:
            chat = Chat()
            api_key = "test"

        return Client()

    def test_wrap_openai(self, aegis_local: Aegis) -> None:
        mock = self._mock_openai()
        wrapped = aegis_local.wrap_openai(mock)
        assert wrapped is not None

    def test_traced_call(self, aegis_local: Aegis) -> None:
        mock = self._mock_openai()
        wrapped = aegis_local.wrap_openai(mock)

        response = wrapped.chat.completions.create(model="gpt-4o-mini")
        assert response.usage.total_tokens == 150

        traces = aegis_local.local_store.recent_traces()
        assert len(traces) == 1
        assert "openai:gpt-4o-mini" in traces[0]["name"]

    def test_proxy_other_attrs(self, aegis_local: Aegis) -> None:
        mock = self._mock_openai()
        wrapped = aegis_local.wrap_openai(mock)
        assert wrapped.api_key == "test"

    def test_no_usage(self, aegis_local: Aegis) -> None:
        class NoUsageResponse:
            usage = None

        class Completions:
            def create(self, **kwargs):
                return NoUsageResponse()

        class Chat:
            completions = Completions()

        class Client:
            chat = Chat()

        wrapped = aegis_local.wrap_openai(Client())
        response = wrapped.chat.completions.create(model="test")
        assert response is not None


# ---------------------------------------------------------------------------
# Anthropic Connector
# ---------------------------------------------------------------------------

class TestAnthropicConnector:
    def _mock_anthropic(self) -> object:
        class Usage:
            input_tokens = 80
            output_tokens = 200

        class Content:
            text = "Hello world"

        class Message:
            usage = Usage()
            content = [Content()]

        class Messages:
            def create(self, **kwargs):
                return Message()

        class Client:
            messages = Messages()
            api_key = "test-key"

        return Client()

    def test_wrap_anthropic(self, aegis_local: Aegis) -> None:
        mock = self._mock_anthropic()
        wrapped = aegis_local.wrap_anthropic(mock)
        assert wrapped is not None

    def test_traced_call(self, aegis_local: Aegis) -> None:
        mock = self._mock_anthropic()
        wrapped = aegis_local.wrap_anthropic(mock)

        msg = wrapped.messages.create(model="claude-sonnet-4-20250514", max_tokens=1024)
        assert msg.content[0].text == "Hello world"

        traces = aegis_local.local_store.recent_traces()
        assert len(traces) == 1
        assert "anthropic:claude-sonnet" in traces[0]["name"]

    def test_proxy_other_attrs(self, aegis_local: Aegis) -> None:
        mock = self._mock_anthropic()
        wrapped = aegis_local.wrap_anthropic(mock)
        assert wrapped.api_key == "test-key"

    def test_no_usage(self, aegis_local: Aegis) -> None:
        class Message:
            usage = None
            content = []

        class Messages:
            def create(self, **kwargs):
                return Message()

        class Client:
            messages = Messages()

        wrapped = aegis_local.wrap_anthropic(Client())
        msg = wrapped.messages.create(model="test")
        assert msg is not None


# ---------------------------------------------------------------------------
# OpenTelemetry Connector
# ---------------------------------------------------------------------------

class TestOpenTelemetryConnector:
    def test_exporter_creation(self, aegis_local: Aegis) -> None:
        from aegis.connectors.opentelemetry_connector import AegisSpanExporter

        exporter = AegisSpanExporter(aegis_local, service_name="test-svc")
        assert exporter.service_name == "test-svc"

    def test_to_otel_format(self, aegis_local: Aegis) -> None:
        from aegis.connectors.opentelemetry_connector import AegisSpanExporter

        exporter = AegisSpanExporter(aegis_local)
        span = Span(
            name="test-op",
            workspace="test",
            tenant_id="t1",
            start_time=1000.0,
            end_time=1000.5,
        )
        span.set_attribute("model", "claude")

        otel = exporter.to_otel_format(span)
        assert otel["name"] == "test-op"
        assert otel["status"]["code"] == 1  # OK
        assert len(otel["attributes"]) >= 1
        assert otel["resource"]["attributes"][0]["value"]["stringValue"] == "aegis-x5"

    def test_export_span(self, aegis_local: Aegis) -> None:
        from aegis.connectors.opentelemetry_connector import AegisSpanExporter

        exporter = AegisSpanExporter(aegis_local)
        span = Span(name="op", start_time=1000.0, end_time=1000.1)
        otel = exporter.export_span(span)
        assert len(exporter.exported) == 1
        assert otel["name"] == "op"

    def test_export_batch(self, aegis_local: Aegis) -> None:
        from aegis.connectors.opentelemetry_connector import AegisSpanExporter

        exporter = AegisSpanExporter(aegis_local)
        spans = [Span(name=f"op-{i}", start_time=1000.0, end_time=1000.1) for i in range(5)]
        results = exporter.export_batch(spans)
        assert len(results) == 5
        assert len(exporter.exported) == 5

    def test_flush(self, aegis_local: Aegis) -> None:
        from aegis.connectors.opentelemetry_connector import AegisSpanExporter

        exporter = AegisSpanExporter(aegis_local)
        exporter.export_span(Span(name="op", start_time=1000.0, end_time=1000.1))
        flushed = exporter.flush()
        assert len(flushed) == 1
        assert len(exporter.exported) == 0

    def test_error_span(self, aegis_local: Aegis) -> None:
        from aegis.connectors.opentelemetry_connector import AegisSpanExporter

        exporter = AegisSpanExporter(aegis_local)
        span = Span(name="err", status=SpanStatus.ERROR, error="boom", start_time=1000.0, end_time=1000.1)
        otel = exporter.to_otel_format(span)
        assert otel["status"]["code"] == 2  # ERROR
        assert otel["status"]["message"] == "boom"

    def test_span_with_events(self, aegis_local: Aegis) -> None:
        from aegis.connectors.opentelemetry_connector import AegisSpanExporter

        exporter = AegisSpanExporter(aegis_local)
        span = Span(name="op", start_time=1000.0, end_time=1000.1)
        span.add_event("checkpoint", step=1)
        otel = exporter.to_otel_format(span)
        assert "events" in otel
        assert len(otel["events"]) == 1

    def test_shutdown(self, aegis_local: Aegis) -> None:
        from aegis.connectors.opentelemetry_connector import AegisSpanExporter

        exporter = AegisSpanExporter(aegis_local)
        exporter.export_span(Span(name="op", start_time=1000.0, end_time=1000.1))
        exporter.shutdown()
        assert len(exporter.exported) == 0


# ---------------------------------------------------------------------------
# Webhook Connector
# ---------------------------------------------------------------------------

class TestWebhookConnector:
    def test_create_router(self, aegis_local: Aegis) -> None:
        try:
            router = aegis_local.webhook_endpoint()
            assert router is not None
        except ImportError:
            pytest.skip("FastAPI not installed")

    def test_webhook_trace_endpoint(self, aegis_local: Aegis) -> None:
        try:
            from fastapi import FastAPI
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("FastAPI not installed")

        app = FastAPI()
        app.include_router(aegis_local.webhook_endpoint())
        client = TestClient(app)

        r = client.post("/webhook/trace", json={
            "agent": "node-agent",
            "model": "gpt-4o",
            "tokens": 500,
            "metadata": {"lang": "javascript"},
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["agent"] == "node-agent"

    def test_webhook_missing_agent(self, aegis_local: Aegis) -> None:
        try:
            from fastapi import FastAPI
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("FastAPI not installed")

        app = FastAPI()
        app.include_router(aegis_local.webhook_endpoint())
        client = TestClient(app)

        r = client.post("/webhook/trace", json={})
        assert r.status_code == 422

    def test_webhook_validate(self, aegis_local: Aegis) -> None:
        try:
            from fastapi import FastAPI
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("FastAPI not installed")

        app = FastAPI()
        app.include_router(aegis_local.webhook_endpoint())
        client = TestClient(app)

        # Clean content
        r = client.post("/webhook/validate", json={"output": "This is safe content."})
        assert r.status_code == 200
        assert r.json()["passed"] is True

        # PII content
        r = client.post("/webhook/validate", json={"output": "Email: john@test.com"})
        assert r.status_code == 200
        assert r.json()["passed"] is False

    def test_webhook_stores_locally(self, aegis_local: Aegis) -> None:
        try:
            from fastapi import FastAPI
            from fastapi.testclient import TestClient
        except ImportError:
            pytest.skip("FastAPI not installed")

        app = FastAPI()
        app.include_router(aegis_local.webhook_endpoint())
        client = TestClient(app)

        client.post("/webhook/trace", json={"agent": "ext-agent", "tokens": 100})
        traces = aegis_local.local_store.recent_traces()
        assert len(traces) == 1
        assert "webhook:ext-agent" in traces[0]["name"]


# ---------------------------------------------------------------------------
# Aegis client connector methods
# ---------------------------------------------------------------------------

class TestAegisConnectorMethods:
    def test_wrap_openai_method(self, aegis_local: Aegis) -> None:
        class MockChat:
            class completions:
                @staticmethod
                def create(**kw):
                    return type("R", (), {"usage": None})()
        class MockClient:
            chat = MockChat()
        wrapped = aegis_local.wrap_openai(MockClient())
        assert wrapped is not None

    def test_wrap_anthropic_method(self, aegis_local: Aegis) -> None:
        class MockMessages:
            def create(self, **kw):
                return type("R", (), {"usage": None, "content": []})()
        class MockClient:
            messages = MockMessages()
        wrapped = aegis_local.wrap_anthropic(MockClient())
        assert wrapped is not None

    def test_langchain_handler_method(self, aegis_local: Aegis) -> None:
        handler = aegis_local.langchain_handler()
        assert hasattr(handler, "on_llm_start")
        assert hasattr(handler, "on_llm_end")

    def test_crewai_middleware_method(self, aegis_local: Aegis) -> None:
        mw = aegis_local.crewai_middleware()
        assert hasattr(mw, "wrap_agent")
        assert hasattr(mw, "wrap_task")
