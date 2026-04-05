# AEGIS-X5 — NotebookLM Prompts

8 prompts for generating deep-dive audio/text content with Google NotebookLM.
Upload the AEGIS-X5 README, whitepapers, and CHANGELOG as sources.

---

## Prompt 1: Platform Overview Podcast

> Create a 10-minute podcast episode explaining AEGIS-X5 to a CTO audience. Cover: what the governance gap is, why existing tools (LangSmith, Arize) fall short, how AEGIS-X5 solves it with 7 modules, and the autonomous closed-loop architecture. Use the whitepaper "State of AI Agent Governance 2026" as the primary source. Tone: authoritative but accessible, like a16z podcast.

## Prompt 2: HSE Deep Dive

> Generate a deep-dive explainer on AEGIS-X5's HSE template for occupational safety professionals. Cover: the 4 specialized validators (SSTFactCheck, EPIValidator, CNESSTCompliance, HazardMinimizer), why guard level N4 is critical for safety, the 97% faithfulness threshold, and real-world examples of blocked dangerous assertions. Reference CNESST, ISO 45001, and OSHA standards. Audience: HSE directors and safety officers.

## Prompt 3: Technical Architecture

> Create a technical overview of AEGIS-X5's architecture for senior engineers. Cover: the src layout, how SpanContext propagates tenant context via contextvars, the 3-tier config cascade (YAML < env < explicit), the guard pipeline with N1-N4 severity levels, and how the predict module uses linear regression + exponential smoothing without PyTorch/sklearn. Include code snippets from the README.

## Prompt 4: Closed-Loop Governance

> Using the "Closed-Loop Governance Architecture" whitepaper, create an explainer on the detect-correct-validate-learn cycle. Cover: the 3 autonomy modes, HITL approval gates, how DriftAutoCorrect triggers retraining, how LatencyAutoScale applies model fallback, and the provenance tracking for audit compliance. Explain why "autonomy is earned, not assumed."

## Prompt 5: Developer Experience Story

> Tell the story of a developer who discovers AEGIS-X5. Walk through: pip install, aegis init, adding 2 lines to their Claude agent, seeing the first trace in the terminal, launching aegis dashboard, and exploring the 5-view dashboard. Emphasize: zero-config local mode, SQLite storage, no Docker needed. Compare to the friction of setting up LangSmith or Weights & Biases.

## Prompt 6: SHIELD-OPS-X5 Case Study

> Create a case study narrative about SHIELD-OPS-X5: 22 platforms, 512 agents, all governed by AEGIS-X5 with the HSE template. Cover: EDGY (122 agents, AI safety), LiteraCIA (122 agents, intelligence), EmergencyOps (61 agents, crisis response). Explain the coverage matrix (observe/guard/evaluate/collect/remember/predict/loops per platform). Include the simulator generating 1400+ traces for the demo dashboard.

## Prompt 7: Competitive Analysis

> Compare AEGIS-X5 against the current landscape: LangSmith (observability), Arize (monitoring), Braintrust (evaluation), Guardrails AI (safety). For each competitor, explain what they do well and what they miss. Then show how AEGIS-X5 uniquely combines all capabilities in one SDK with autonomous closed loops. Use the pricing comparison: $499/mo vs enterprise-only competitors.

## Prompt 8: Regulatory Compliance Briefing

> Create a compliance briefing for legal/regulatory teams. Cover: how AEGIS-X5 addresses EU AI Act requirements (risk assessment, human oversight, audit trails), Quebec Loi 25 (data provenance, erasure), GDPR/CCPA (ErasureManager), and ISO 45001 (safety management records). Explain the PROV-O provenance tracking and how every guard decision is auditable.
