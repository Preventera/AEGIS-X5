"""
AEGIS-X5 — Autonomous Agent Governance

Unified platform to observe, guard, evaluate, and autonomously govern
AI agent fleets at scale.

Usage:
    from aegis import Aegis

    aegis = Aegis(
        workspace="my-org",
        api_key="ak_...",
        modules=["observe", "guard", "evaluate"],
        autonomy="semi-auto",
    )

    @aegis.observe()
    def my_agent_task(input):
        ...

    @aegis.protect()
    def critical_operation(data):
        ...
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

__version__ = "0.1.0"
__all__ = ["Aegis", "AutonomyMode"]


class AutonomyMode(str, Enum):
    """Three autonomy levels for agent governance."""

    MONITOR = "monitor"       # Observe and alert only
    SEMI_AUTO = "semi-auto"   # Automated suggestions, human approval gates
    FULL_AUTO = "full-auto"   # Fully autonomous closed-loop control


@dataclass
class Aegis:
    """Main AEGIS-X5 client.

    Parameters
    ----------
    workspace : str
        Workspace identifier for multi-tenant isolation.
    api_key : str
        API key for authentication.
    modules : list[str]
        Modules to activate (observe, guard, evaluate, collect, remember, predict, loops).
    autonomy : str | AutonomyMode
        Autonomy level: "monitor", "semi-auto", or "full-auto".
    """

    workspace: str
    api_key: str
    modules: list[str] = field(default_factory=lambda: ["observe"])
    autonomy: str | AutonomyMode = AutonomyMode.MONITOR

    # -- internal state --
    _initialized: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        if isinstance(self.autonomy, str):
            self.autonomy = AutonomyMode(self.autonomy)
        self._initialized = True

    # -- decorators --

    def observe(self, **options: Any) -> Callable:
        """Decorator: wrap a function with observability (tracing, metrics).

        Usage:
            @aegis.observe(tags=["critical"])
            def my_func(...):
                ...
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                # TODO: Phase Observe — emit span, collect metrics
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def protect(self, **options: Any) -> Callable:
        """Decorator: wrap a function with guard rails (policy checks, safety).

        Usage:
            @aegis.protect(policy="pii-filter")
            def handle_data(...):
                ...
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                # TODO: Phase Guard — run policy checks before execution
                return func(*args, **kwargs)

            return wrapper

        return decorator
