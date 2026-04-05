"""aegis.api — REST API for AEGIS-X5 platform.

FastAPI-based API serving traces, guard validation, health scoring,
and predictions. Used in Docker Compose deployment.
"""

from aegis.api.app import create_api

__all__ = ["create_api"]
