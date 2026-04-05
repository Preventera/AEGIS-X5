"""aegis.tenants — Pre-configured tenant profiles.

Contains tenant definitions for production deployments,
including SHIELD-OPS-X5 as the reference first tenant.
"""

from aegis.tenants.shield_ops import ShieldOpsTenant

__all__ = ["ShieldOpsTenant"]
