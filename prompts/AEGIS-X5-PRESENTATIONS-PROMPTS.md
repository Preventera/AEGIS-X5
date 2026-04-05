# AEGIS-X5 — Presentation Deck Prompts

5 prompts for generating slide decks. Use with Claude, ChatGPT, or Gamma.app.

---

## Prompt 1: Commercial Deck — 15 Slides

> Create a 15-slide commercial presentation deck for AEGIS-X5.
>
> **Slide structure:**
> 1. Title: "AEGIS-X5 — Govern Your AI Agents Before They Govern You"
> 2. The Problem: AI agents are proliferating, governance is not (stat: 73% have no framework)
> 3. The Cost of No Governance: $50K bad recommendations, blocked operations, regulatory fines
> 4. AEGIS-X5 Solution: One SDK, 7 modules, full lifecycle governance
> 5. Governance Lifecycle: Observe > Guard > Evaluate > Collect > Remember > Predict > Loops
> 6. Two Lines to Start: code snippet showing @aegis.observe + @aegis.protect
> 7. Guard Rails: N1-N4 severity levels, PII/injection/hallucination detection, HITL gates
> 8. ML Predictive: Health Score 0-100, drift prediction 48h, cost forecasting 7 days
> 9. Autonomous Loops: Detect-correct-validate-learn, 3 autonomy modes
> 10. Dashboard: 5 views screenshot description (Overview, Agents, Guard, Predictions, Traces)
> 11. HSE Template: 4 validators, CNESST/ISO 45001/OSHA compliance, 97% faithfulness
> 12. SHIELD-OPS-X5: 22 platforms, 512 agents, production proven
> 13. Framework Support: Anthropic, OpenAI, LangChain, CrewAI, Webhook, OTEL
> 14. Pricing: Free (local) / $499/mo (Pro) / $2,500/mo (Enterprise)
> 15. Call to Action: Request a Demo — contact@preventera.com
>
> **Design:** Dark theme, gold/cyan accents, minimal text per slide, data-driven.
> **Audience:** CTOs, VP Engineering, Safety Directors.
> **Duration:** 12 minutes.

## Prompt 2: Technical Deck — 10 Slides

> Create a 10-slide technical architecture presentation for AEGIS-X5.
>
> **Slide structure:**
> 1. Title: "AEGIS-X5 — Technical Architecture Deep Dive"
> 2. Architecture Overview: src layout diagram (core, observe, guard, evaluate, collect, remember, predict, loops, connectors, templates, api, dashboard)
> 3. Core SDK: Multi-tenant via contextvars, SpanContext, 3-tier config (YAML < env < explicit)
> 4. Tracing System: Span parent-child tracking, TraceCollector, local SQLite + PostgreSQL
> 5. Guard Pipeline: Sequential validators, N1-N4 severity, HITL callback, raise_on_block
> 6. Predict Module: Linear regression + exponential smoothing, Z-score + IQR ensemble, zero deps
> 7. Closed Loops: ClosedLoop ABC (detect/correct/validate/learn), LoopOrchestrator, autonomy modes
> 8. Connectors: Duck-typed callbacks (LangChain), transparent wrappers (OpenAI/Anthropic), webhook protocol
> 9. Deployment: Docker Compose (PostgreSQL 16 + Redis 7 + FastAPI + Dashboard), CI/CD GitHub Actions
> 10. API Surface: 12+ REST endpoints, API key auth, OTLP-compatible export
>
> **Audience:** Senior engineers, platform architects.
> **Include:** Code snippets, architecture diagrams (text-based), performance numbers (748 tests, <100ms overhead).

## Prompt 3: Investor Pitch — 10 Slides

> Create a 10-slide investor pitch deck for Preventera / AEGIS-X5.
>
> 1. Title + tagline
> 2. Problem: $2.3B lost annually to ungoverned AI agent errors (projected)
> 3. Market: AI governance TAM $8B by 2028, growing 45% CAGR
> 4. Solution: AEGIS-X5 — the Datadog for AI agents
> 5. Product: 7 modules, autonomous loops, industry templates
> 6. Traction: 748 tests, 22 platforms, 512 agents governed, HSE template in production
> 7. Business Model: SaaS $499-$2,500/mo, 85%+ gross margin, land-and-expand
> 8. Competitive Moat: Only platform with observe + guard + predict + autonomous loops in one SDK
> 9. Team: Preventera founding team + GenAISafety + ReadinessX5 brand
> 10. Ask: Seed round for enterprise GTM, first 50 customers, 3 industry templates

## Prompt 4: HSE Safety Presentation — 12 Slides

> Create a 12-slide presentation for HSE professionals about AI safety governance.
>
> 1. Title: "Governing AI in Occupational Safety — AEGIS-X5 HSE Template"
> 2. The Risk: AI agents giving safety advice without governance
> 3. Real Example: "Aucun risque" — when an AI tells a worker asbestos is safe
> 4. The 4 HSE Validators: SSTFactCheck, EPIValidator, CNESSTCompliance, HazardMinimizer
> 5. Guard Level N4: What it means — immediate block, no exceptions
> 6. Regulatory Compliance: CNESST RSST, ISO 45001, OSHA 1910/1926, Loi 25, EU AI Act
> 7. Golden Set: 20 test cases (10 correct, 10 dangerous) — continuous validation
> 8. Collection Sources: CNESST, IRSST, APSAM, CCHST, ISO, OSHA with confidence scoring
> 9. Production Results: 127 dangerous assertions blocked in month 1
> 10. Dashboard: Guard view showing blocked events in real-time
> 11. Integration: 2 lines of code, works with any AI framework
> 12. Next Steps: Deploy in your organization — contact@preventera.com

## Prompt 5: Board Report — 8 Slides

> Create an 8-slide quarterly board report for AEGIS-X5 / Preventera.
>
> 1. Title: Q1 2026 Board Report — AEGIS-X5
> 2. Product Milestones: Phase 1-9 completed, 748 tests, 9 modules, 6 connectors
> 3. Technical Metrics: 512 agents governed, 22 platforms, <100ms overhead, 99.9% uptime
> 4. Customer Pipeline: SHIELD-OPS-X5 production, 3 enterprise prospects, 2 pilot deployments
> 5. Revenue: $0 (pre-revenue) / projected $180K ARR by Q4 2026
> 6. Competitive Position: Only full-lifecycle governance platform, HSE template unique advantage
> 7. Key Risks: Sales cycle length, framework adoption speed, regulatory timing
> 8. Q2 Priorities: First paying customer, healthcare template, Netlify deployment
