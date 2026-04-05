# Module Reference

AEGIS-X5 is organized into 7 modules that can be activated independently.

```python
aegis = Aegis(modules=["observe", "guard", "evaluate"])
```

---

## Observe

Real-time telemetry, tracing, and behavioral analytics.

### Usage

```python
@aegis.observe("operation-name")
def my_function(input):
    return result

# Or as a context manager
with aegis.trace("manual-span") as span:
    span.set_attribute("model", "claude-sonnet")
    result = do_something()
```

### Components

| Component | Description |
|-----------|-------------|
| `Tracer` | Universal sync/async tracer with automatic parent-child span tracking |
| `TokenUsage` | Extracts token counts from LLM responses |
| `CostCalculator` | Computes cost per model per call |
| `SlidingWindowMetrics` | Real-time latency statistics (p50, p95, p99) |
| `SpanExporter` | OTLP-compatible span export |

### Configuration

```yaml
# aegis.yaml
modules:
  - observe
```

---

## Guard

Policy enforcement with N1-N4 severity levels and HITL gates.

### Usage

```python
@aegis.protect("safety-check", level="N3")
def critical_function(data):
    return processed

# Or via pipeline
from aegis.guard.pipeline import GuardPipeline
from aegis.guard.validators import PIIDetector, InjectionDetector

pipeline = GuardPipeline()
pipeline.add(PIIDetector()).add(InjectionDetector())
result = pipeline.run("content to validate")
```

### Guard Levels

| Level | Action | Use Case |
|-------|--------|----------|
| N1 | Log only | Informational warnings |
| N2 | Warn + HITL | Requires human approval if configured |
| N3 | Block | Stops execution, returns blocked result |
| N4 | Kill | Stops execution, optionally raises exception |

### Built-in Validators

| Validator | Detects |
|-----------|---------|
| `PIIDetector` | Email, phone, SSN, credit card patterns |
| `InjectionDetector` | Prompt injection attempts |
| `HallucinationDetector` | Hedging phrases, ground truth mismatches |

---

## Evaluate

Continuous quality assessment with drift detection.

### Usage

```python
from aegis.evaluate.runner import EvalRunner, TestCase
from aegis.evaluate.metrics import Relevancy, Faithfulness

runner = EvalRunner()
runner.add_metric(Relevancy()).add_metric(Faithfulness())

cases = [
    TestCase(name="q1", query="What is X?", response="X is...", context=["X is defined as..."]),
]
report = runner.run(cases)
print(report.pass_rate)
```

### Built-in Metrics

| Metric | Measures |
|--------|----------|
| `Relevancy` | Query-response alignment |
| `Faithfulness` | Response grounding in context |
| `ContextPrecision` | Context relevance to query |

### Drift Detection

```python
from aegis.evaluate.drift import DriftDetector

detector = DriftDetector(warning_threshold=0.1, critical_threshold=0.25)
detector.set_baseline({"faithfulness": 0.95})
alerts = detector.check({"faithfulness": 0.82})
```

---

## Collect

Structured feedback ingestion from web sources and internal systems.

### Usage

```python
from aegis.collect.sources import WebSource
from aegis.collect.registry import SourceRegistry

registry = SourceRegistry()
registry.register(WebSource(name="docs", domain="docs.example.com", search_fn=my_search))
items = registry.collect_all()
```

### Components

| Component | Description |
|-----------|-------------|
| `Source` | Abstract base for data sources |
| `WebSource` | Web search integration with configurable search function |
| `SourceRegistry` | Central registry for all collection sources |
| `ScheduledCollector` | Cron-like scheduled polling |

---

## Remember

Memory management with provenance tracking and regulatory compliance.

### Usage

```python
from aegis.remember.agent_memory import AgentMemory
from aegis.remember.store import InMemoryStore

store = InMemoryStore()
memory = AgentMemory(store=store, namespace="agent-1")
memory.remember("user_preference", {"theme": "dark"})
value = memory.recall("user_preference")
```

### Components

| Component | Description |
|-----------|-------------|
| `AgentMemory` | Per-agent memory with namespace isolation |
| `InMemoryStore` | Fast in-memory storage (dev/test) |
| `ProvenanceTracker` | PROV-O compatible audit trail |
| `ErasureManager` | GDPR/CCPA compliant data erasure |

---

## Predict

ML predictive analytics using only Python stdlib.

### Health Score

```python
from aegis.predict.health_score import HealthScore

hs = HealthScore()
snap = hs.compute("agent-1", {
    "latency_p95": 350.0,
    "error_rate": 0.02,
    "faithfulness": 0.95,
    "guard_blocks": 1,
})
print(snap.score, snap.status)  # 87.3 healthy
```

### Drift Prediction

```python
from aegis.predict.drift import DriftPredictor

pred = DriftPredictor(critical_threshold=0.85)
# Add historical data points
for ts, value in historical_data:
    pred.add_point("faithfulness", ts, value)

prediction = pred.predict("faithfulness", horizon_hours=48)
if prediction.time_to_threshold_hours:
    print(f"Will breach in {prediction.time_to_threshold_hours:.0f}h")
```

### Cost Forecasting

```python
from aegis.predict.cost import CostForecaster

fc = CostForecaster(daily_budget=50.0)
# Add daily cost history
for day_ts, cost in cost_history:
    fc.add_daily_cost("agent-1", day_ts, cost)

result = fc.forecast("agent-1")
print(result.weekly_total, result.budget_alert)
```

### Anomaly Detection

```python
from aegis.predict.anomaly import AnomalyDetector

detector = AnomalyDetector(z_threshold=3.0, method="ensemble")
detector.add_batch("latency", historical_latencies)

result = detector.check("latency", current_value)
if result.is_anomaly:
    print(f"Anomaly! {result.direction} (score={result.score:.1f})")
```

---

## Loops

Autonomous closed-loop control with HITL approval gates.

### Available Loops

| Loop | Trigger | Action |
|------|---------|--------|
| `DriftAutoCorrect` | Faithfulness drift detected | Triggers retraining pipeline |
| `GuardAutoTune` | Guard false positive rate high | Adjusts thresholds |
| `LatencyAutoScale` | p95 latency above threshold | Applies model fallback |

### Orchestrator

```python
from aegis.loops import LoopOrchestrator

orch = LoopOrchestrator(autonomy="semi-auto")
orch.register(drift_loop, high_risk=True)
orch.register(latency_loop, high_risk=False)
results = orch.run_all()
```
