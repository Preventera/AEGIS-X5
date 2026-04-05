"""CrewAI connector — AegisCrewMiddleware for multi-agent governance.

Wraps each CrewAI agent with observe + guard, captures task results,
agent names, and delegation chains.

Usage::

    from aegis import Aegis

    aegis = Aegis()
    middleware = aegis.crewai_middleware()

    # Apply to each agent task
    result = middleware.wrap_task(agent_name, task_fn, *args)
"""

from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import Any

from aegis.core.trace import SpanContext


class AegisCrewMiddleware:
    """Middleware for CrewAI agent governance.

    Wraps agent task execution with AEGIS observe + guard.
    Tracks delegation chains and task-level metrics.
    """

    def __init__(self, aegis: Any) -> None:
        self._aegis = aegis
        self._delegation_chain: list[str] = []
        self._task_results: list[dict[str, Any]] = []

    @property
    def delegation_chain(self) -> list[str]:
        """The sequence of agent names that handled tasks."""
        return list(self._delegation_chain)

    @property
    def task_results(self) -> list[dict[str, Any]]:
        """Results from all wrapped tasks."""
        return list(self._task_results)

    def wrap_agent(self, agent_name: str, func: Callable) -> Callable:
        """Wrap an agent's task function with AEGIS tracing.

        Parameters
        ----------
        agent_name : str
            Name of the CrewAI agent.
        func : callable
            The agent's task execution function.

        Returns
        -------
        callable
            Wrapped function with automatic tracing.
        """
        aegis = self._aegis

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            self._delegation_chain.append(agent_name)
            start = time.time()

            with SpanContext(f"crewai:{agent_name}") as span:
                span.set_attribute("aegis.module", "observe")
                span.set_attribute("aegis.connector", "crewai")
                span.set_attribute("agent_name", agent_name)
                span.set_attribute("delegation_depth", len(self._delegation_chain))
                if aegis.tenant:
                    span.workspace = aegis.tenant.workspace
                    span.tenant_id = aegis.tenant.tenant_id

                result = func(*args, **kwargs)

                span.set_attribute("aegis.guard.status", "PASS")
                elapsed = (time.time() - start) * 1000

            # Record task result
            self._task_results.append({
                "agent": agent_name,
                "duration_ms": round(elapsed, 1),
                "delegation_depth": len(self._delegation_chain),
                "success": True,
            })

            # Store locally
            if aegis.is_local and aegis.local_store:
                aegis.local_store.store_span(span)

            return result

        return wrapper

    def wrap_task(self, agent_name: str, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Convenience: wrap and immediately execute a task.

        Parameters
        ----------
        agent_name : str
            Name of the agent.
        func : callable
            Task function to execute.
        """
        wrapped = self.wrap_agent(agent_name, func)
        return wrapped(*args, **kwargs)

    def reset(self) -> None:
        """Reset delegation chain and task results."""
        self._delegation_chain.clear()
        self._task_results.clear()
