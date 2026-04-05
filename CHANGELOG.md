# Changelog

All notable changes to AEGIS-X5 are documented here.

---

## [0.3.0] - 2026-04-05

### Phase 5 — Industry Templates + Infrastructure

- **HSE Template**: 4 specialized validators (SSTFactCheck, EPIValidator, CNESSTCompliance, HazardMinimizer), 20-case golden set, 6 collection sources, regulatory references (ISO 45001, OSHA, CNESST, Loi 25, EU AI Act)
- **Template Loader**: `load_template("hse")` auto-loads config, validators, sources, golden set
- **REST API**: 7 endpoints (trace, guard/validate, health, agents, predictions, stats, traces) with API key authentication
- **Docker Compose**: PostgreSQL 16, Redis 7, FastAPI backend, Dashboard, Makefile
- **CI/CD**: GitHub Actions (lint, typecheck, test, coverage), Dependabot, pre-commit hooks

### Phase 4 — ML Predictive Analytics

- **HealthScore**: 0-100 score per agent with 7 weighted inputs, trend analysis
- **DriftPredictor**: 48h forecast using linear regression + exponential smoothing
- **CostForecaster**: 7-day cost projection with spike detection and budget alerts
- **AnomalyDetector**: Z-score + IQR ensemble on sliding windows
- **PredictionEngine**: Orchestrates all predictors with calibration tracking (MAE, RMSE)
- **Predictive Loop Integration**: Bridges predictions to autonomous loops for preventive action

### Phase 3 — Developer Experience

- **CLI**: `aegis init`, `aegis status`, `aegis dashboard`, `aegis test`
- **Standalone Mode**: `Aegis()` without API key works locally with SQLite storage
- **Auto-Detection**: Detects installed frameworks (LangChain, CrewAI, OpenAI, Anthropic)
- **Terminal Summary**: One-line trace output (tokens, cost, latency, guard status)
- **Mini Dashboard**: Single-page dark-themed HTML dashboard on port 4005
- **5 Examples**: Claude, LangChain RAG, CrewAI, OpenAI, FastAPI

---

## [0.2.0] - 2026-04-04

### Phase 2 — Autonomous Closed Loops

- **ClosedLoop ABC**: 4-phase cycle (detect, correct, validate, learn)
- **DriftAutoCorrect**: Detects faithfulness drift, triggers retraining
- **GuardAutoTune**: Adjusts guard thresholds based on false positive rates
- **LatencyAutoScale**: Applies model fallback when p95 latency exceeds threshold
- **LoopOrchestrator**: Autonomy modes (monitor, semi-auto, full-auto) with HITL gates

### Phase 1C — Evaluate + Collect + Remember

- **EvalRunner**: Test case execution with pluggable metrics
- **Built-in Metrics**: Relevancy, Faithfulness, ContextPrecision
- **DriftDetector**: Baseline vs current score comparison with alerts
- **SourceRegistry**: Dynamic source registration with domain filtering
- **ScheduledCollector**: Cron-like collection scheduling
- **AgentMemory**: Per-agent memory with namespace isolation
- **ProvenanceTracker**: PROV-O compatible audit trail
- **ErasureManager**: GDPR/CCPA compliant data erasure

---

## [0.1.0] - 2026-04-04

### Phase 1A — Core SDK

- **Aegis Client**: Main entry point with workspace, API key, modules, autonomy modes
- **AegisConfig**: 3-tier config loading (YAML < env < explicit)
- **Multi-Tenant**: Workspace-based isolation with contextvars propagation
- **Tracing**: Span, SpanContext, parent-child tracking, in-memory collector
- **Guard Levels**: N1-N4 severity system

### Phase 1B — Observe + Guard

- **Universal Tracer**: Sync/async auto-detection with token/cost enrichment
- **CostCalculator**: Per-model cost computation
- **SlidingWindowMetrics**: Real-time p50/p95/p99 latency stats
- **GuardPipeline**: Sequential validator execution with HITL gate
- **Built-in Validators**: PIIDetector, InjectionDetector, HallucinationDetector
