"""aegis.core — SDK universel.

Composants fondamentaux : configuration, multi-tenant, tracing, guard levels.
"""

from aegis.core.config import AegisConfig, load_config
from aegis.core.guard_levels import GuardLevel, GuardResult, GuardViolation
from aegis.core.tenant import Tenant, TenantContext, get_current_tenant
from aegis.core.trace import Span, SpanContext, SpanStatus, TraceCollector, get_collector

__all__ = [
    "AegisConfig",
    "GuardLevel",
    "GuardResult",
    "GuardViolation",
    "Span",
    "SpanContext",
    "SpanStatus",
    "Tenant",
    "TenantContext",
    "TraceCollector",
    "get_collector",
    "get_current_tenant",
    "load_config",
]
