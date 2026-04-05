"""Example: OpenAI with AEGIS-X5 connector — transparent wrapping.

Usage::

    pip install aegis-x5 openai
    export OPENAI_API_KEY=sk-...
    python examples/openai_with_connector.py
"""

from aegis import Aegis

aegis = Aegis()

# In production with real OpenAI:
#
#   from openai import OpenAI
#
#   client = aegis.wrap_openai(OpenAI())
#   response = client.chat.completions.create(
#       model="gpt-4o-mini",
#       messages=[{"role": "user", "content": "What is ISO 45001?"}],
#   )
#   print(response.choices[0].message.content)

# --- Simulation (no real OpenAI needed) ---


class MockUsage:
    prompt_tokens = 80
    completion_tokens = 200
    total_tokens = 280


class MockChoice:
    class message:
        content = "ISO 45001 is the international standard for occupational health and safety."


class MockResponse:
    usage = MockUsage()
    choices = [MockChoice()]


class MockCompletions:
    def create(self, **kwargs):
        return MockResponse()


class MockChat:
    completions = MockCompletions()


class MockOpenAI:
    chat = MockChat()


client = aegis.wrap_openai(MockOpenAI())
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What is ISO 45001?"}],
)

print(f"Response: {response.choices[0].message.content}")
print("Trace captured via AEGIS OpenAI connector.")
print("Run `aegis status` to see the trace.")
