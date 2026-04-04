"""Configuration loading — YAML files + environment variables, multi-workspace."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base* (neither is mutated)."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a YAML file if it exists; return empty dict otherwise.

    Uses PyYAML when available, falls back to a minimal inline parser
    so the SDK works without heavy dependencies.
    """
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    try:
        import yaml  # type: ignore[import-untyped]

        return yaml.safe_load(text) or {}
    except ImportError:
        return _parse_simple_yaml(text)


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Minimal flat-key YAML parser (key: value per line, no nesting)."""
    result: dict[str, Any] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        if value.lower() in ("true", "yes"):
            result[key.strip()] = True
        elif value.lower() in ("false", "no"):
            result[key.strip()] = False
        elif value.isdigit():
            result[key.strip()] = int(value)
        else:
            result[key.strip()] = value
    return result


# ---------------------------------------------------------------------------
# Environment variable prefix — AEGIS_<KEY>
# ---------------------------------------------------------------------------
_ENV_PREFIX = "AEGIS_"


def _collect_env_overrides() -> dict[str, str]:
    """Return all ``AEGIS_*`` env vars as a flat dict with the prefix stripped.

    Keys are lower-cased and ``__`` is converted to ``.`` so that
    ``AEGIS_WORKSPACE`` → ``workspace`` and
    ``AEGIS_API__KEY`` → ``api.key``.
    """
    overrides: dict[str, str] = {}
    for key, value in os.environ.items():
        if key.startswith(_ENV_PREFIX):
            clean = key[len(_ENV_PREFIX) :].lower().replace("__", ".")
            overrides[clean] = value
    return overrides


# ---------------------------------------------------------------------------
# AegisConfig — immutable config object
# ---------------------------------------------------------------------------

_VALID_MODULES = frozenset(
    ["observe", "guard", "evaluate", "collect", "remember", "predict", "loops"]
)

_VALID_AUTONOMY = frozenset(["monitor", "semi-auto", "full-auto"])


@dataclass(frozen=True)
class AegisConfig:
    """Resolved, immutable configuration for one workspace."""

    workspace: str
    api_key: str = ""
    modules: tuple[str, ...] = ("observe",)
    autonomy: str = "monitor"
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.workspace:
            raise ValueError("workspace must be a non-empty string")
        bad = set(self.modules) - _VALID_MODULES
        if bad:
            raise ValueError(f"Unknown modules: {bad}")
        if self.autonomy not in _VALID_AUTONOMY:
            raise ValueError(
                f"autonomy must be one of {sorted(_VALID_AUTONOMY)}, got {self.autonomy!r}"
            )


# ---------------------------------------------------------------------------
# Public API — load_config
# ---------------------------------------------------------------------------


def load_config(
    *,
    workspace: str | None = None,
    api_key: str | None = None,
    modules: list[str] | None = None,
    autonomy: str | None = None,
    config_path: str | Path | None = None,
) -> AegisConfig:
    """Build an :class:`AegisConfig` by merging (lowest → highest priority):

    1. YAML file (``config_path`` or ``./aegis.yaml``)
    2. Environment variables (``AEGIS_*``)
    3. Explicit keyword arguments

    Parameters are intentionally all optional so callers can supply only the
    overrides they care about.
    """
    # 1 — YAML file
    yaml_path = Path(config_path) if config_path else Path("aegis.yaml")
    file_data = _load_yaml_file(yaml_path)

    # 2 — Env vars
    env_data = _collect_env_overrides()

    # 3 — Merge: file < env < explicit kwargs
    merged: dict[str, Any] = {}
    merged = _deep_merge(merged, file_data)
    merged = _deep_merge(merged, env_data)

    if workspace is not None:
        merged["workspace"] = workspace
    if api_key is not None:
        merged["api_key"] = api_key
    if modules is not None:
        merged["modules"] = modules
    if autonomy is not None:
        merged["autonomy"] = autonomy

    # Normalise modules to a tuple of strings
    raw_modules = merged.get("modules", ["observe"])
    if isinstance(raw_modules, str):
        raw_modules = [m.strip() for m in raw_modules.split(",")]

    # Pull known keys; everything else goes into extra
    known = {"workspace", "api_key", "modules", "autonomy"}
    extra = {k: v for k, v in merged.items() if k not in known}

    return AegisConfig(
        workspace=merged.get("workspace", ""),
        api_key=merged.get("api_key", ""),
        modules=tuple(raw_modules),
        autonomy=merged.get("autonomy", "monitor"),
        extra=extra,
    )
