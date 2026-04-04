# AEGIS-X5

## Project Overview
AEGIS-X5 is a **commercial SaaS platform** (NOT open-source) for Autonomous Agent Governance.
It provides observe, guard, evaluate, collect, remember, predict, and autonomous loop capabilities for AI agent fleets.

## Architecture
- **Package**: `aegis-x5` (Python, src layout under `src/aegis/`)
- **Modules**: observe, guard, evaluate, collect, remember, predict, loops, templates
- **Client**: `from aegis import Aegis` — main entry point
- **Autonomy modes**: monitor, semi-auto, full-auto
- **Multi-tenant**: workspace-based isolation

## Development
- Python 3.11+
- Package manager: pip / pyproject.toml
- Tests: pytest (`tests/`)
- Linting: ruff

## Conventions
- Each module lives in `src/aegis/<module>/` with its own `__init__.py`
- Module development is phased — skeleton first, implementation later
- Commercial product — no open-source license, proprietary code
- Remote: https://github.com/Preventera/AEGIS-X5.git
