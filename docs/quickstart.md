# Quick Start

Get your first agent governed by AEGIS-X5 in under 2 minutes.

## Installation

```bash
pip install aegis-x5
```

For the dashboard and API:

```bash
pip install aegis-x5[dashboard]
```

## Initialize Your Project

```bash
aegis init --workspace my-project
```

This creates an `aegis.yaml` configuration file in your project directory.

## Instrument Your Agent

### Claude Agent

```python
from aegis import Aegis

aegis = Aegis()  # local mode - zero config

@aegis.observe("claude-agent")
@aegis.protect("content-safety", level="N2")
def ask_claude(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text

answer = ask_claude("Explain quantum computing.")
```

### LangChain RAG

```python
from aegis import Aegis

aegis = Aegis(modules=["observe", "evaluate"])

@aegis.observe("rag-retrieve")
def retrieve(query: str) -> list[str]:
    # your retrieval logic
    return docs

@aegis.observe("rag-generate")
def generate(query: str, context: list[str]) -> str:
    # your LLM generation
    return response
```

### CrewAI Team

```python
from aegis import Aegis

aegis = Aegis(modules=["observe", "guard"])

@aegis.protect("researcher-guard", level="N2")
@aegis.observe("researcher")
def researcher(topic: str) -> str:
    return research_results

@aegis.protect("writer-guard", level="N3")
@aegis.observe("writer")
def writer(research: str) -> str:
    return draft
```

## Launch the Dashboard

```bash
aegis dashboard
```

Open [http://localhost:4005](http://localhost:4005) to see:

- **Total traces** and throughput
- **Average and max latency**
- **Guard blocks** count
- **Recent traces** with status, latency, and workspace

The dashboard auto-refreshes every 5 seconds.

## Check Status from CLI

```bash
aegis status
```

Output:

```
=== AEGIS-X5 Status ===

Workspaces: local

Total traces:   42
Avg latency:    156.3 ms
Max latency:    892.1 ms
Guard blocks:   2

--- Last 20 traces ---
Name                           Status   Latency     Time
claude-agent                   ok        156.3ms  2026-04-05 14:23:01
guard:content-safety           ok          2.1ms  2026-04-05 14:23:01
```

## Terminal Output

In local mode, every trace prints a one-line summary to stderr:

```
  ✓ Trace captured | claude-agent | Tokens: 1,250 | Cost: $0.0040 | Latency: 156ms | Guard: ✓ PASS
```

## Next Steps

- [Module reference](modules.md) — detailed configuration for each module
- [API endpoints](api.md) — REST API for programmatic access
- [Templates](templates.md) — industry-specific governance (HSE, etc.)
