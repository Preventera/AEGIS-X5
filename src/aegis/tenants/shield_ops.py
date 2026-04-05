"""SHIELD-OPS-X5 — first production tenant of AEGIS-X5.

Configures the SHIELD-OPS-X5 deployment with 21 AgenticX5 platforms
and 500+ agents governed through the HSE template.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# Platform definition
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Platform:
    """A registered AgenticX5 platform within SHIELD-OPS-X5."""

    name: str
    code: str
    agent_count: int
    status: str  # "live" | "prototype" | "planned"
    guard_level: str  # "N1" .. "N4"
    modules: list[str]
    description: str = ""

    @property
    def is_live(self) -> bool:
        return self.status == "live"


# ---------------------------------------------------------------------------
# ShieldOpsTenant
# ---------------------------------------------------------------------------

_AGENTS_YAML = Path(__file__).parent / "shield_ops_agents.yaml"


class ShieldOpsTenant:
    """SHIELD-OPS-X5 tenant configuration — 21 platforms, 500+ agents.

    Usage::

        tenant = ShieldOpsTenant()
        for p in tenant.platforms:
            print(p.name, p.agent_count, p.status)

        print(tenant.total_agents)       # 512
        print(tenant.live_platforms)      # [Platform(...), ...]
        print(tenant.coverage_matrix())   # {platform: {module: bool}}
    """

    WORKSPACE = "shield-ops-x5"
    TEMPLATE = "hse"

    def __init__(self, agents_path: str | Path | None = None) -> None:
        self._path = Path(agents_path) if agents_path else _AGENTS_YAML
        self._platforms: list[Platform] = []
        self._load()

    def _load(self) -> None:
        """Load platform registry from YAML."""
        if not self._path.exists():
            return
        text = self._path.read_text(encoding="utf-8")
        data = yaml.safe_load(text) or {}
        for entry in data.get("platforms", []):
            self._platforms.append(Platform(
                name=entry["name"],
                code=entry["code"],
                agent_count=entry.get("agent_count", 0),
                status=entry.get("status", "planned"),
                guard_level=entry.get("guard_level", "N2"),
                modules=entry.get("modules", ["observe"]),
                description=entry.get("description", ""),
            ))

    @property
    def platforms(self) -> list[Platform]:
        return list(self._platforms)

    @property
    def total_agents(self) -> int:
        return sum(p.agent_count for p in self._platforms)

    @property
    def total_platforms(self) -> int:
        return len(self._platforms)

    @property
    def live_platforms(self) -> list[Platform]:
        return [p for p in self._platforms if p.is_live]

    @property
    def prototype_platforms(self) -> list[Platform]:
        return [p for p in self._platforms if p.status == "prototype"]

    def get_platform(self, code: str) -> Platform | None:
        """Lookup a platform by its short code."""
        for p in self._platforms:
            if p.code == code:
                return p
        return None

    def coverage_matrix(self) -> dict[str, dict[str, bool]]:
        """Return module coverage matrix per platform.

        Returns a dict: {platform_code: {module_name: enabled}}.
        """
        all_modules = ["observe", "guard", "evaluate", "collect", "remember", "predict", "loops"]
        matrix: dict[str, dict[str, bool]] = {}
        for p in self._platforms:
            matrix[p.code] = {m: m in p.modules for m in all_modules}
        return matrix

    def summary(self) -> dict[str, Any]:
        """Return a summary dict suitable for dashboard/API display."""
        return {
            "workspace": self.WORKSPACE,
            "template": self.TEMPLATE,
            "total_platforms": self.total_platforms,
            "total_agents": self.total_agents,
            "live": len(self.live_platforms),
            "prototype": len(self.prototype_platforms),
            "platforms": [
                {
                    "name": p.name,
                    "code": p.code,
                    "agents": p.agent_count,
                    "status": p.status,
                    "guard": p.guard_level,
                }
                for p in self._platforms
            ],
        }
