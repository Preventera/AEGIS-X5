"""Simple API key authentication for AEGIS-X5 API."""

from __future__ import annotations

import os
from typing import Any


def require_api_key(api_key: str, valid_keys: list[str] | None = None) -> bool:
    """Validate an API key against the allowed list.

    Parameters
    ----------
    api_key : str
        The key to validate.
    valid_keys : list[str] | None
        Allowed keys. Falls back to AEGIS_API_KEYS env var.

    Returns
    -------
    bool
        True if the key is valid.
    """
    if valid_keys is None:
        raw = os.environ.get("AEGIS_API_KEYS", "")
        valid_keys = [k.strip() for k in raw.split(",") if k.strip()]

    if not valid_keys:
        return True  # no keys configured → open access

    return api_key in valid_keys
