# AEGIS-X5 — Autonomous Agent Governance Platform

## CONTEXTE PROJET

Tu es l'architecte technique du projet **AEGIS-X5**, une plateforme de gouvernance
agentique autonome qui gouverne les agents IA en boucle fermée.

**5 modules** : OBSERVE · GUARD · EVALUATE · COLLECT · REMEMBER
**3 modes** : Monitor · Semi-auto · Full-auto
**2 modes déploiement** : Local SQLite (zéro config) · Cloud multi-tenant

### Propriétaire
- **Mario Deshaies** — CTO / VP AI, Innoventera Inc. (GenAISafety + AgenticX5)
- **Email** : team@agenticx5.com / mdcoachpro@gmail.com
- **Localisation** : Montréal, Québec, Canada
- **Repo** : https://github.com/Preventera/AEGIS-X5 (public)
- **Site** : https://aegis-x5-site.netlify.app

---

## RÈGLES DE TRAVAIL

1. **Étape par étape** : POINT D'ARRÊT entre chaque livrable
2. **Agnostique d'abord** : Aucune référence AgenticX5 dans le code core
3. **Tests** : Objectif >90% coverage
4. **Pas de code sans OK** : Présenter concept/architecture avant d'écrire
5. **Langue** : Français principal, code/commentaires en anglais
6. **SDK-first** : Le SDK est l'interface principale. Le portail est secondaire.
7. **Conformité native** : Loi 25, RGPD, EU AI Act intégrés dès conception

---

## LIVRABLES EXISTANTS (hérités de SHIELD-OPS-X5)

- ✅ GitHub `Preventera/SHIELD-OPS-X5` — 380 tests, 8 phases, Docker 6 services
- ✅ 5 escouades Python (watch/guard/eval/feed/memory)
- ✅ API REST + Auth JWT + Alerting
- ✅ Dashboard React + FastAPI
- ✅ CI/CD GitHub Actions + Dependabot
- ✅ Docker Compose opérationnel (Langfuse + PostgreSQL + Redis + ClickHouse)
- ✅ Landing page commerciale HTML (aegis-x5-site.netlify.app)
- ✅ Architecture interactive HTML

## LIVRABLES AEGIS-X5 COMPLÉTÉS

- ✅ Nouveau repo GitHub `Preventera/AEGIS-X5` — public, 41+ commits
- ✅ Refactoring core agnostique — src/aegis/ avec modules complets
- ✅ **SDK universel `pip install aegis-x5`** — PyPI v0.3.0 — publié 2026-04-09
- ✅ pyproject.toml — packaging complet, extras optionnels, CLI entry point
- ✅ GitHub Actions `.github/workflows/publish.yml` — workflow TestPyPI + PyPI prod
- ✅ Mode local SQLite (Aegis() sans api_key = zéro infrastructure)
- ✅ Templates industrie (HSE, Finance, Santé, Legal)
- ✅ Site commercial AEGIS-X5 v16 bilingue FR/EN

## À COMPLÉTER

- [ ] Portail multi-tenant (isolation client complète)
- [ ] Backend AEGIS-X5 déployé sur serveur cloud (Railway ou Render)
- [ ] demo-live.html branchée sur backend SHIELD-OPS-X5 réel (voir priorités)
- [ ] SOC2 Type II (Phase 4)
- [ ] `npm install aegis-x5` (Node.js SDK)

---

## COMPTES ET TOKENS PUBLIÉS

| Service | URL | Username |
|---------|-----|----------|
| PyPI prod | https://pypi.org/project/aegis-x5/0.3.0/ | agenticx5 |
| TestPyPI | https://test.pypi.org/project/aegis-x5/0.3.0/ | agenticx5 |

- **Email** : team@agenticx5.com
- **Tokens** : dans `~/.pypirc` — NE JAMAIS COMMITTER
- **2FA** : activé sur les deux comptes (Google Authenticator)

### Pour publier une nouvelle version
```bash
# 1. Mettre à jour version dans pyproject.toml et src/aegis/__init__.py
# 2. Builder
python -m build
twine check dist/*
# 3. Publier
twine upload --repository pypi dist/*
# OU créer une GitHub Release → workflow publish.yml se déclenche automatiquement
```

---

## PRIORITÉS IMMÉDIATES

### PRIORITÉ 1 — Régler facturation GitHub
- Settings → Billing → Update payment method
- Débloque GitHub Actions CI/CD (bloqué depuis le 2026-04-09)
- Coût : ~4 USD/mois (plan Team)

### PRIORITÉ 2 — Brancher demo-live.html sur backend réel
**Objectif** : Remplacer les données simulées dans `aegis-x5-deploy/demo-live.html`
par de vraies traces du backend SHIELD-OPS-X5 déjà déployé.

**Endpoints à brancher** :
```javascript
// Remplacer les données hardcodées par ces appels API
const BASE_URL = "https://[URL-SHIELD-OPS-X5-DEPLOYED]"

// Agents actifs + Health Scores
GET  ${BASE_URL}/api/v1/agents
GET  ${BASE_URL}/api/v1/agents/{id}/health

// Traces en temps réel
GET  ${BASE_URL}/api/v1/traces?limit=20
POST ${BASE_URL}/api/v1/trace

// Guard events
GET  ${BASE_URL}/api/v1/guard/events?limit=10

// Métriques dashboard
GET  ${BASE_URL}/api/v1/metrics/summary
```

**Fichier à modifier** : `aegis-x5-deploy/demo-live.html`
**Pattern** : Remplacer `const DEMO_DATA = {...}` par `fetch()` vers backend réel
**Fallback** : Si le backend ne répond pas → garder les données simulées

### PRIORITÉ 3 — Badge PyPI dans README.md
Ajouter en haut du README, après le titre :
```markdown
[![PyPI version](https://badge.fury.io/py/aegis-x5.svg)](https://pypi.org/project/aegis-x5/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/Preventera/AEGIS-X5/actions/workflows/ci.yml/badge.svg)](https://github.com/Preventera/AEGIS-X5/actions)
```

### PRIORITÉ 4 — Annoncer sur LinkedIn
Post LinkedIn : "`pip install aegis-x5` is live on PyPI"
- Tagline : "Autonomous Agent Governance for regulated industries"
- Lien : https://pypi.org/project/aegis-x5/
- Hashtags : #AgentGovernance #AICompliance #HSE #Python #OpenSource

---

## ARCHITECTURE SDK

### Modes de déploiement
```python
# Mode local (zéro config, SQLite)
aegis = Aegis()

# Mode cloud (multi-tenant)
aegis = Aegis(workspace="mon-org", api_key="ak_...")
```

### Connecteurs supportés
- Python : `@aegis.observe()`, `@aegis.protect()`, `with aegis.trace()`
- LangChain : `aegis.langchain_handler()`
- CrewAI : `aegis.crewai_middleware()`
- OpenAI SDK : `aegis.wrap_openai(client)`
- Anthropic SDK : `aegis.wrap_anthropic(client)`
- REST/Webhook : POST `/v1/trace`
- OpenTelemetry : `AegisSpanExporter`

### Structure repo
```
src/aegis/
├── __init__.py          # Aegis client, AutonomyMode, GuardLevel
├── cli.py               # Commande `aegis` CLI
├── core/                # Config, guard_levels, tenant, trace
├── local/               # SQLite store (mode zéro config)
├── api/                 # FastAPI routes
├── connectors/          # LangChain, CrewAI, OpenAI, Anthropic, webhook
├── dashboard/           # Dashboard React
├── evaluate/            # RAGAS, DeepEval
├── guard/               # Guard pipeline N1-N4
├── collect/             # Veille réglementaire
├── remember/            # PROV-O audit trails
├── predict/             # Health Score, DriftPredictor
├── loops/               # Boucles fermées autonomes
└── templates/           # HSE, Finance, Santé, Legal
```

---

## STACK TECHNIQUE

```
CORE
├── Python 3.12+
├── FastAPI (API REST + WebSocket)
├── Celery + Redis (tâches async)
├── PostgreSQL 16 + TimescaleDB
└── Alembic (migrations)

ML PRÉDICTIF
├── Health Score (XGBoost)
├── DriftPredictor (linear regression + exponential smoothing, 48h)
├── CostForecaster (Z-score, 7j)
└── stdlib Python uniquement (zéro numpy/scipy pour le core)

ÉVALUATION
├── RAGAS (faithfulness RAG)
└── DeepEval (tests unitaires agents)

SÉCURITÉ
├── Guardrails AI
├── NeMo Guardrails
└── JWT + OAuth2 + RBAC

INFRASTRUCTURE
├── Docker Compose (dev)
├── Kubernetes (prod)
├── GitHub Actions CI/CD
└── Netlify (site commercial)
```

---

## CONFORMITÉ NATIVE

| Norme | Module |
|-------|--------|
| Loi 25 (Québec) | REMEMBER (droit à l'oubli) + GUARD (PII) |
| RGPD | REMEMBER namespace isolation + erasure |
| EU AI Act | GUARD (classification risques) + EVALUATE |
| ISO 42001 | OBSERVE + EVALUATE (audit trails) |
| NIST AI RMF | EVALUATE (risk assessment) |
| ISO 45001 | Templates HSE/SST |
