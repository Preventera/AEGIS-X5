"""Example: LangChain with AEGIS-X5 connector — automatic tracing.

Usage::

    pip install aegis-x5 langchain-anthropic
    python examples/langchain_with_connector.py
"""

from aegis import Aegis

aegis = Aegis()

# Get the callback handler — works with any LangChain LLM
handler = aegis.langchain_handler()

# In production with real LangChain:
#
#   from langchain_anthropic import ChatAnthropic
#
#   llm = ChatAnthropic(
#       model="claude-sonnet-4-20250514",
#       callbacks=[handler],
#   )
#   response = llm.invoke("Explain OSHA 1910 requirements.")

# --- Simulation (no real LangChain needed) ---

from uuid import uuid4


class MockLLMOutput:
    llm_output = {"token_usage": {"prompt_tokens": 150, "completion_tokens": 300, "total_tokens": 450}}
    generations = [[type("G", (), {"text": "OSHA 1910 covers general industry safety standards."})()]]


# Simulate LangChain callback lifecycle
run_id = uuid4()
handler.on_llm_start(
    {"kwargs": {"model": "claude-sonnet"}, "id": ["ChatAnthropic"]},
    ["Explain OSHA 1910 requirements."],
    run_id=run_id,
)
handler.on_llm_end(MockLLMOutput(), run_id=run_id)

print("LangChain trace captured via AEGIS connector.")
print("Run `aegis status` to see the trace.")
