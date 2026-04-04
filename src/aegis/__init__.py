"""
AEGIS-X5 — Autonomous Agent Governance

Unified platform to observe, guard, evaluate, and autonomously govern
AI agent fleets at scale.

Usage::

    from aegis import Aegis

    aegis = Aegis(workspace="my-org", api_key="ak_...")

    @aegis.observe("process-query")
    def process(query):
        ...

    @aegis.protect("pii-filter", level="N3")
    def handle_data(data):
        ...

    with aegis.trace("my-operation") as span:
        span.set_attribute("model", "claude-sonnet")
        ...
"""

from __future__ import annotations

import functools
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from aegis.core.config import AegisConfig, load_config
from aegis.core.guard_levels import GuardLevel, GuardResult, GuardViolation
from aegis.core.tenant import Tenant, TenantContext, set_current_tenant
from aegis.core.trace import Span, SpanContext, SpanStatus, get_collector

__version__ = "0.1.0"
__all__ = [
    "Aegis",
    "AegisConfig",
    "AutonomyMode",
    "GuardLevel",
    "GuardResult",
    "GuardViolation",
    "Span",
    "SpanStatus",
]


class AutonomyMode(str, Enum):
    """Three autonomy levels for agent governance."""

    MONITOR = "monitor"
    SEMI_AUTO = "semi-auto"
    FULL_AUTO = "full-auto"


_VALID_MODULES = frozenset(
    ["observe", "guard", "evaluate", "collect", "remember", "predict", "loops"]
)


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
        Modules to activate.
    autonomy : str | AutonomyMode
        Autonomy level: ``"monitor"``, ``"semi-auto"``, or ``"full-auto"``.
    config_path : str | None
        Optional path to an ``aegis.yaml`` configuration file.
    """

    workspace: str
    api_key: str = ""
    modules: list[str] = field(default_factory=lambda: ["observe"])
    autonomy: str | AutonomyMode = AutonomyMode.MONITOR
    config_path: str | None = field(default=None, repr=False)

    # -- internal state (not part of the public API) --
    _config: AegisConfig = field(init=False, repr=False)
    _tenant: Tenant = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # Validate modules
        bad = set(self.modules) - _VALID_MODULES
        if bad:
            raise ValueError(f"Unknown modules: {bad}")

        # Normalise autonomy
        if isinstance(self.autonomy, str):
            self.autonomy = AutonomyMode(self.autonomy)

        # Build resolved config (YAML < env < explicit)
        self._config = load_config(
            workspace=self.workspace,
            api_key=self.api_key,
            modules=self.modules,
            autonomy=self.autonomy.value,
            config_path=self.config_path,
        )

        # Activate tenant for this workspace
        self._tenant = Tenant(workspace=self.workspace)
        set_current_tenant(self._tenant)

    # -- properties --

    @property
    def config(self) -> AegisConfig:
        return self._config

    @property
    def tenant(self) -> Tenant:
        return self._tenant

    @property
    def tenant_id(self) -> str:
        return self._tenant.tenant_id

    # -- decorators --

    def observe(self, name: str | None = None, **attributes: Any) -> Callable:
        """Decorator: trace every call with a span.

        Usage::

            @aegis.observe("llm-call")
            def call_model(prompt):
                ...

        The decorated function's calls are wrapped in a :class:`Span` that
        records duration, status, tenant context, and custom attributes.
        """
        tenant = self._tenant

        def decorator(func: Callable) -> Callable:
            span_name = name or func.__qualname__

            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                with SpanContext(span_name, **attributes) as span:
                    span.workspace = tenant.workspace
                    span.tenant_id = tenant.tenant_id
                    span.set_attribute("aegis.module", "observe")
                    result = func(*args, **kwargs)
                    return result

            return wrapper

        return decorator

    def protect(
        self,
        name: str | None = None,
        level: str | GuardLevel = GuardLevel.N2,
        **attributes: Any,
    ) -> Callable:
        """Decorator: guard function output with policy enforcement.

        Usage::

            @aegis.protect("pii-filter", level="N3")
            def process(data):
                ...

        Parameters
        ----------
        name : str | None
            Guard rule name (defaults to function qualname).
        level : str | GuardLevel
            Guard level: ``"N1"``–``"N4"`` or a :class:`GuardLevel` enum.
        """
        if isinstance(level, str):
            level = GuardLevel[level]
        tenant = self._tenant

        def decorator(func: Callable) -> Callable:
            rule_name = name or func.__qualname__

            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                with SpanContext(f"guard:{rule_name}", **attributes) as span:
                    span.workspace = tenant.workspace
                    span.tenant_id = tenant.tenant_id
                    span.set_attribute("aegis.module", "guard")
                    span.set_attribute("aegis.guard.level", level.name)
                    span.set_attribute("aegis.guard.rule", rule_name)
                    result = func(*args, **kwargs)
                    # TODO: Phase Guard — run actual policy checks on `result`
                    return result

            return wrapper

        return decorator

    # -- context manager --

    def trace(self, name: str, **attributes: Any) -> SpanContext:
        """Context manager: create a traced span.

        Usage::

            with aegis.trace("embedding-lookup") as span:
                span.set_attribute("model", "text-embedding-3")
                ...
        """
        return SpanContext(name, **attributes)
