"""Example: Claude agent with AEGIS-X5 governance.

Usage::

    pip install aegis-x5 anthropic
    python examples/claude_agent.py
"""

from aegis import Aegis

aegis = Aegis()  # local mode — no API key needed


@aegis.observe("claude-agent")
@aegis.protect("content-safety", level="N2")
def ask_claude(prompt: str) -> str:
    """Call Claude and return the response (governed by AEGIS)."""
    import anthropic

    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


if __name__ == "__main__":
    answer = ask_claude("Explain quantum computing in one paragraph.")
    print(f"\nClaude: {answer}")
