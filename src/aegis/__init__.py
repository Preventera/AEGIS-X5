"""
AEGIS-X5 — Autonomous Agent Governance

Unified platform to observe, guard, evaluate, and autonomously govern
AI agent fleets at scale.

Usage (enterprise — cloud mode)::

    from aegis import Aegis

    aegis = Aegis(workspace="my-org", api_key="ak_...")

    @aegis.observe("process-query")
    def process(query):
        ...

Usage (standalone — local mode, zero config)::

    from aegis import Aegis

    aegis = Aegis()  # no api_key → local SQLite, terminal output

    @aegis.observe("my-agent")
    def agent(prompt):
        ...
"""

from __future__ import annotations

import functools
import importlib.util
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from aegis.core.config import AegisConfig, load_config
from aegis.core.guard_levels import GuardLevel, GuardResult, GuardViolation
from aegis.core.tenant import Tenant, set_current_tenant
from aegis.core.trace import Span, SpanContext, SpanStatus

__version__ = "0.3.0"
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


# ---------------------------------------------------------------------------
# Framework auto-detection
# ---------------------------------------------------------------------------

_FRAMEWORK_HOOKS: dict[str, str] = {
    "langchain": "langchain",
    "crewai": "crewai",
    "openai": "openai",
    "anthropic": "anthropic",
}


def _detect_frameworks() -> list[str]:
    """Return names of AI frameworks currently installed."""
    found: list[str] = []
    for pkg, module_name in _FRAMEWORK_HOOKS.items():
        if importlib.util.find_spec(module_name) is not None:
            found.append(pkg)
    return found


# ---------------------------------------------------------------------------
# Terminal summary helpers
# ---------------------------------------------------------------------------

def _print_summary(summary: Any) -> None:
    """Print a one-line trace summary to stderr (non-blocking DX feedback)."""
    guard_icon = "\u2713" if summary.guard_status == "PASS" else "\u2717"
    cost_str = f"${summary.cost:.4f}" if summary.cost else "$0.0000"
    tokens_str = f"{summary.tokens:,}" if summary.tokens else "0"
    line = (
        f"  \u2713 Trace captured | "
        f"{summary.name} | "
        f"Tokens: {tokens_str} | "
        f"Cost: {cost_str} | "
        f"Latency: {summary.duration_ms:.0f}ms | "
        f"Guard: {guard_icon} {summary.guard_status}"
    )
    print(line, file=sys.stderr)


# ---------------------------------------------------------------------------
# Main client
# ---------------------------------------------------------------------------

@dataclass
class Aegis:
    """Main AEGIS-X5 client.

    Parameters
    ----------
    workspace : str
        Workspace identifier for multi-tenant isolation.
        Defaults to ``"local"`` in standalone mode.
    api_key : str
        API key for authentication.
        Empty string → standalone local mode (SQLite).
    modules : list[str]
        Modules to activate.
    autonomy : str | AutonomyMode
        Autonomy level: ``"monitor"``, ``"semi-auto"``, or ``"full-auto"``.
    config_path : str | None
        Optional path to an ``aegis.yaml`` configuration file.
    local_db : str | None
        Path to SQLite database for local mode.
        Defaults to ``~/.aegis/local.db``.
    verbose : bool
        Print trace summaries to terminal in local mode.
    """

    workspace: str = "local"
    api_key: str = ""
    modules: list[str] = field(default_factory=lambda: ["observe"])
    autonomy: str | AutonomyMode = AutonomyMode.MONITOR
    config_path: str | None = field(default=None, repr=False)
    local_db: str | None = field(default=None, repr=False)
    verbose: bool = field(default=True, repr=False)

    # -- internal state (not part of the public API) --
    _config: AegisConfig = field(init=False, repr=False)
    _tenant: Tenant = field(init=False, repr=False)
    _local_store: Any = field(init=False, repr=False, default=None)
    _is_local: bool = field(init=False, repr=False, default=False)
    _detected_frameworks: list[str] = field(init=False, repr=False, default_factory=list)
    _first_trace_done: bool = field(init=False, repr=False, default=False)

    def __post_init__(self) -> None:
        # Validate modules
        bad = set(self.modules) - _VALID_MODULES
        if bad:
            raise ValueError(f"Unknown modules: {bad}")

        # Normalise autonomy
        if isinstance(self.autonomy, str):
            self.autonomy = AutonomyMode(self.autonomy)

        # Determine mode: local (no api_key) vs cloud (api_key provided)
        self._is_local = not self.api_key

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

        # Local mode: init SQLite store
        if self._is_local:
            from aegis.local.store import LocalStore

            self._local_store = LocalStore(db_path=self.local_db)

        # Auto-detect frameworks
        self._detected_frameworks = _detect_frameworks()

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

    @property
    def is_local(self) -> bool:
        """True when running in standalone local mode (no api_key)."""
        return self._is_local

    @property
    def detected_frameworks(self) -> list[str]:
        """AI frameworks detected in the environment."""
        return list(self._detected_frameworks)

    @property
    def local_store(self) -> Any:
        """The local SQLite store (None in cloud mode)."""
        return self._local_store

    # -- internal helpers --

    def _on_span_finished(self, span: Span) -> None:
        """Called when a span completes — persist + print summary in local mode."""
        if self._is_local and self._local_store is not None:
            summary = self._local_store.store_span(span)
            if self.verbose:
                _print_summary(summary)

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

            # Attach post-hook via monkey-patching the SpanContext for local mode
            if self._is_local:
                @functools.wraps(func)
                def local_wrapper(*args: Any, **kwargs: Any) -> Any:
                    with SpanContext(span_name, **attributes) as span:
                        span.workspace = tenant.workspace
                        span.tenant_id = tenant.tenant_id
                        span.set_attribute("aegis.module", "observe")
                        result = func(*args, **kwargs)
                    self._on_span_finished(span)
                    return result

                return local_wrapper

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
            Guard level: ``"N1"``--``"N4"`` or a :class:`GuardLevel` enum.
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
                    span.set_attribute("aegis.guard.status", "PASS")
                    result = func(*args, **kwargs)
                    # TODO: Phase Guard — run actual policy checks on `result`
                if self._is_local:
                    self._on_span_finished(span)
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

        In local mode, the span is automatically stored to SQLite on exit.
        """
        if self._is_local:
            return _LocalSpanContext(name, on_finish=self._on_span_finished, **attributes)
        return SpanContext(name, **attributes)


# ---------------------------------------------------------------------------
# Local-mode SpanContext that calls back on finish
# ---------------------------------------------------------------------------

class _LocalSpanContext(SpanContext):
    """SpanContext subclass that persists the span to local store on exit."""

    def __init__(self, name: str, on_finish: Callable[[Span], None], **attributes: Any) -> None:
        super().__init__(name, **attributes)
        self._on_finish = on_finish

    def __exit__(self, exc_type: type | None, exc_val: BaseException | None, *_: object) -> None:
        super().__exit__(exc_type, exc_val, *_)
        self._on_finish(self._span)
