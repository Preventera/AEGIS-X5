<p align="center">
  <strong>AEGIS-X5</strong><br>
  <em>Autonomous Agent Governance Platform</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/aegis-x5/"><img src="https://badge.fury.io/py/aegis-x5.svg" alt="PyPI version"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python 3.11+"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://github.com/Preventera/AEGIS-X5/actions"><img src="https://github.com/Preventera/AEGIS-X5/actions/workflows/ci.yml/badge.svg" alt="Tests"></a>
</p>

<p align="center">
  Observe, guard, evaluate, and autonomously govern AI agent fleets — at scale.<br>
  From first trace to full autonomous loops, in under 2 minutes.
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> &middot;
  <a href="#modules">Modules</a> &middot;
  <a href="#cli">CLI</a> &middot;
  <a href="#api">API</a> &middot;
  <a href="#templates">Templates</a> &middot;
  <a href="#request-a-demo">Request a Demo</a>
</p>

---

## Why AEGIS-X5?

Organizations deploying AI agents face a governance gap: once agents are live, there is no unified way to monitor their behaviour, enforce safety policies, detect drift, and respond autonomously.

AEGIS-X5 closes that gap with a single SDK that wraps any agent — Claude, GPT, LangChain, CrewAI — and provides real-time governance from day one.

---

## Quick Start

**1. Install**

```bash
pip install aegis-x5
```

**2. Initialize your project**

```bash
aegis init
```

**3. Add two lines to your agent**

```python
from aegis import Aegis

aegis = Aegis()  # local mode — no API key needed

@aegis.observe("my-agent")
@aegis.protect("safety-check", level="N2")
def my_agent(prompt: str) -> str:
    # your agent logic here
    return result
```

**4. See your first metrics**

```bash
aegis dashboard
# Open http://localhost:4005
```

That's it. Your agent is now governed — traces, latency, cost, and guard status visible in real time.

---

## Modules

| Module | Purpose | Key Features |
|--------|---------|--------------|
| **Observe** | Real-time telemetry | Distributed tracing, token counting, cost calculation, latency metrics |
| **Guard** | Policy enforcement | PII detection, injection prevention, hallucination checks, N1-N4 severity levels |
| **Evaluate** | Quality assessment | Faithfulness, relevancy, context precision, golden set testing, drift detection |
| **Collect** | Feedback ingestion | Structured sources, web collection, confidence scoring, scheduled polling |
| **Remember** | Memory management | Agent memory, provenance tracking (PROV-O), GDPR/CCPA erasure compliance |
| **Predict** | ML predictive analytics | Health Score 0-100, drift prediction 48h ahead, cost forecasting, anomaly detection |
| **Loops** | Autonomous control | Drift auto-correct, guard auto-tune, latency auto-scale, HITL approval gates |

### Autonomy Modes

| Mode | Behaviour |
|------|-----------|
| `monitor` | Observe and alert only — no automated actions |
| `semi-auto` | Auto-correct low-risk; human approval for high-risk |
| `full-auto` | Fully autonomous governance with closed-loop control |

---

## Developer Mode vs Enterprise Mode

AEGIS-X5 operates in two modes depending on configuration:

| | Developer (Local) | Enterprise (Cloud) |
|---|---|---|
| **Setup** | `Aegis()` — zero config | `Aegis(workspace="org", api_key="ak_...")` |
| **Storage** | SQLite (`~/.aegis/local.db`) | PostgreSQL + Redis |
| **Dashboard** | `aegis dashboard` (port 4005) | Hosted platform |
| **Cost** | Free for local use | Commercial license |
| **Scaling** | Single machine | Multi-tenant, multi-workspace |

---

## CLI

```
aegis init          Create aegis.yaml in current project
aegis status        Show agents, traces, and stats
aegis dashboard     Launch local dashboard (port 4005)
aegis test          Run evaluations on golden set
```

---

## API

REST API served on port 4000 (Docker) or embedded.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/trace` | Record a trace span |
| `POST` | `/api/v1/guard/validate` | Validate content through guard pipeline |
| `GET` | `/api/v1/health` | Health check (public) |
| `GET` | `/api/v1/agents` | List agents with health scores |
| `GET` | `/api/v1/predictions` | Active predictions and accuracy |
| `GET` | `/api/v1/stats` | Aggregate trace statistics |
| `GET` | `/api/v1/traces` | Recent traces |

Authentication via `X-API-Key` header. See [docs/api.md](docs/api.md) for details.

---

## ML Predictive Analytics

AEGIS-X5 includes a built-in prediction engine (zero external ML dependencies):

- **Health Score** — 0-100 score per agent combining 7 weighted signals (latency, errors, cost, faithfulness, guard blocks, drift, memory)
- **Drift Predictor** — Predicts metric degradation 48h before critical threshold using linear regression + exponential smoothing
- **Cost Forecaster** — 7-day cost projection with spike detection and budget alerts
- **Anomaly Detector** — Z-score + IQR ensemble detection on sliding windows
- **Calibration Tracking** — Compares predictions vs reality (MAE, RMSE)

---

## Templates

Industry-specific governance profiles that pre-configure validators, thresholds, and evaluation sets.

### HSE (Health, Safety & Environment)

Built for occupational safety agents in Quebec/Canadian regulatory context:

- **4 specialized validators**: SSTFactCheck, EPIValidator, CNESSTCompliance, HazardMinimizer
- **Guard level N4** for safety-critical assertions
- **Faithfulness threshold 97%**
- **20-case golden set** covering PPE, confined spaces, height work, hazardous materials, noise
- **6 pre-configured sources**: CNESST, IRSST, APSAM, CCHST, ISO, OSHA
- **Regulatory references**: ISO 45001, OSHA 1910/1926, CNESST RSST, Loi 25, EU AI Act

```python
from aegis.templates import load_template

tpl = load_template("hse")
# tpl.validators, tpl.golden_set, tpl.sources, tpl.regulations
```

---

## Docker Compose

Full platform deployment with PostgreSQL, Redis, API, and Dashboard:

```bash
cp .env.example .env
make up
```

| Service | Port | Description |
|---------|------|-------------|
| API | 4000 | REST API + Swagger docs |
| Dashboard | 4005 | Real-time monitoring UI |
| PostgreSQL | 5432 | Persistent storage |
| Redis | 6379 | Cache + sessions |

---

## Examples

Ready-to-run examples in [`examples/`](examples/):

- `claude_agent.py` — Claude agent with `@aegis.protect`
- `langchain_rag.py` — RAG pipeline with observe + evaluate
- `crewai_team.py` — Multi-agent team with guard on each agent
- `openai_agent.py` — OpenAI agent with observe
- `fastapi_endpoint.py` — API endpoint protected by guard

---

## Architecture

```
aegis
├── core/        # SDK foundation, config, multi-tenant, tracing
├── observe/     # Telemetry, tokens, cost, latency metrics
├── guard/       # Validator pipeline, PII, injection, hallucination
├── evaluate/    # Metrics, drift detection, eval runner
���── collect/     # Source registry, web collection, scheduler
├── remember/    # Agent memory, provenance, GDPR erasure
├── predict/     # Health score, drift/cost/anomaly prediction
├── loops/       # Autonomous closed loops, orchestrator
├── templates/   # Industry profiles (HSE, ...)
├── dashboard/   # Local web UI
├── api/         # REST API (FastAPI)
├── local/       # SQLite standalone storage
└── cli.py       # CLI entry point
```

---

## Request a Demo

AEGIS-X5 is a commercial platform by **Preventera**.

For enterprise licensing, custom templates, or a guided demo:

**contact@preventera.com**

---

<p align="center">
  &copy; Preventera &middot; GenAISafety &middot; ReadinessX5&trade;
</p>
