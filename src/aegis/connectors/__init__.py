"""aegis.connectors — Framework connectors and SDK wrappers.

Auto-detection and transparent integration with LangChain, CrewAI,
OpenAI, Anthropic, webhooks, and OpenTelemetry.
"""

from aegis.connectors.langchain_connector import AegisCallbackHandler
from aegis.connectors.crewai_connector import AegisCrewMiddleware
from aegis.connectors.openai_connector import wrap_openai
from aegis.connectors.anthropic_connector import wrap_anthropic
from aegis.connectors.webhook_connector import create_webhook_router
from aegis.connectors.opentelemetry_connector import AegisSpanExporter

__all__ = [
    "AegisCallbackHandler",
    "AegisCrewMiddleware",
    "AegisSpanExporter",
    "create_webhook_router",
    "wrap_anthropic",
    "wrap_openai",
]
