"""Example: OpenAI agent with AEGIS-X5 observe.

Usage::

    pip install aegis-x5 openai
    python examples/openai_agent.py
"""

from aegis import Aegis

aegis = Aegis()


@aegis.observe("openai-chat")
def chat(prompt: str) -> str:
    """Call OpenAI GPT and return the response (traced by AEGIS)."""
    import openai

    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    answer = chat("What is autonomous agent governance?")
    print(f"\nGPT: {answer}")
    print("\nRun `aegis status` to see the trace.")
