"""Example: Anthropic with AEGIS-X5 connector — transparent wrapping.

Usage::

    pip install aegis-x5 anthropic
    export ANTHROPIC_API_KEY=sk-ant-...
    python examples/anthropic_with_connector.py
"""

from aegis import Aegis

aegis = Aegis()

# In production with real Anthropic:
#
#   from anthropic import Anthropic
#
#   client = aegis.wrap_anthropic(Anthropic())
#   message = client.messages.create(
#       model="claude-sonnet-4-20250514",
#       max_tokens=1024,
#       messages=[{"role": "user", "content": "Explain confined space entry."}],
#   )
#   print(message.content[0].text)

# --- Simulation (no real Anthropic SDK needed) ---


class MockUsage:
    input_tokens = 120
    output_tokens = 350


class MockContent:
    text = "Confined space entry requires a permit, atmospheric testing, ventilation, and a standby person."


class MockMessage:
    usage = MockUsage()
    content = [MockContent()]


class MockMessages:
    def create(self, **kwargs):
        return MockMessage()


class MockAnthropic:
    messages = MockMessages()


client = aegis.wrap_anthropic(MockAnthropic())
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Explain confined space entry."}],
)

print(f"Response: {message.content[0].text}")
print("Trace captured via AEGIS Anthropic connector.")
print("Run `aegis status` to see the trace.")
