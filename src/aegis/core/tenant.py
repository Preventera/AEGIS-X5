"""Multi-tenancy — workspace isolation and tenant context propagation."""

from __future__ import annotations

import contextvars
import uuid
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Tenant context — thread/async-safe via contextvars
# ---------------------------------------------------------------------------

_current_tenant: contextvars.ContextVar[Tenant | None] = contextvars.ContextVar(
    "aegis_current_tenant", default=None
)


@dataclass(frozen=True)
class Tenant:
    """Represents an isolated workspace tenant.

    Every trace, span, and event produced while a Tenant is active
    carries its ``workspace`` and ``tenant_id``.
    """

    workspace: str
    tenant_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.workspace:
            raise ValueError("workspace must be a non-empty string")


# ---------------------------------------------------------------------------
# Context helpers
# ---------------------------------------------------------------------------


def set_current_tenant(tenant: Tenant) -> contextvars.Token[Tenant | None]:
    """Activate *tenant* for the current context (thread / async task).

    Returns a reset token that can be passed to :func:`reset_tenant`.
    """
    return _current_tenant.set(tenant)


def get_current_tenant() -> Tenant | None:
    """Return the active tenant, or ``None`` if none is set."""
    return _current_tenant.get()


def reset_tenant(token: contextvars.Token[Tenant | None]) -> None:
    """Restore the previous tenant using a token from :func:`set_current_tenant`."""
    _current_tenant.reset(token)


class TenantContext:
    """Context manager that activates a :class:`Tenant` for a block of code.

    Usage::

        tenant = Tenant(workspace="acme")
        with TenantContext(tenant):
            # all traces emitted here carry tenant.workspace / tenant.tenant_id
            ...
    """

    def __init__(self, tenant: Tenant) -> None:
        self._tenant = tenant
        self._token: contextvars.Token[Tenant | None] | None = None

    def __enter__(self) -> Tenant:
        self._token = set_current_tenant(self._tenant)
        return self._tenant

    def __exit__(self, *exc: object) -> None:
        if self._token is not None:
            reset_tenant(self._token)
            self._token = None
