"""Template loader — loads industry governance templates by name.

Usage::

    from aegis.templates.loader import load_template, TemplateConfig

    tpl = load_template("hse")
    # tpl.config_data, tpl.validators, tpl.sources, tpl.golden_set

Or via the Aegis client::

    aegis = Aegis(template="hse")  # auto-loads HSE config + validators
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aegis.guard.validators import BaseValidator


# ---------------------------------------------------------------------------
# Template directory layout convention:
#   src/aegis/templates/<name>/
#       <name>_config.yaml
#       <name>_validators.py     (exports validator classes)
#       <name>_eval_golden_set.json
#       <name>_collect_sources.yaml
# ---------------------------------------------------------------------------

_TEMPLATES_DIR = Path(__file__).parent

_KNOWN_TEMPLATES = {
    "hse": "hse",
    "health": "health",
    "finance": "finance",
    "legal": "legal",
    "general": "general",
}


@dataclass
class TemplateConfig:
    """Loaded template contents."""

    name: str
    config_data: dict[str, Any] = field(default_factory=dict)
    validators: list[BaseValidator] = field(default_factory=list)
    sources: dict[str, Any] = field(default_factory=dict)
    golden_set: dict[str, Any] = field(default_factory=dict)
    regulations: list[dict[str, str]] = field(default_factory=list)


def load_template(name: str) -> TemplateConfig:
    """Load a template by name.

    Parameters
    ----------
    name : str
        Template name (e.g., ``"hse"``).

    Returns
    -------
    TemplateConfig
        Loaded template with config, validators, sources, and golden set.

    Raises
    ------
    ValueError
        If the template name is not recognized or directory not found.
    """
    template_dir = _TEMPLATES_DIR / name
    if not template_dir.is_dir():
        available = [
            d.name for d in _TEMPLATES_DIR.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        ]
        raise ValueError(
            f"Template {name!r} not found. Available: {available}"
        )

    tpl = TemplateConfig(name=name)

    # 1. Load YAML config
    config_path = template_dir / f"{name}_config.yaml"
    if config_path.exists():
        tpl.config_data = _load_yaml(config_path)
        tpl.regulations = tpl.config_data.get("regulations", [])

    # 2. Load validators
    tpl.validators = _load_validators(name)

    # 3. Load golden set
    golden_path = template_dir / f"{name}_eval_golden_set.json"
    if golden_path.exists():
        text = golden_path.read_text(encoding="utf-8")
        tpl.golden_set = json.loads(text)

    # 4. Load collection sources
    sources_path = template_dir / f"{name}_collect_sources.yaml"
    if sources_path.exists():
        tpl.sources = _load_yaml(sources_path)

    return tpl


def available_templates() -> list[str]:
    """Return names of all available templates."""
    return [
        d.name for d in _TEMPLATES_DIR.iterdir()
        if d.is_dir() and not d.name.startswith("_") and not d.name == "__pycache__"
    ]


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML with PyYAML fallback."""
    text = path.read_text(encoding="utf-8")
    try:
        import yaml
        return yaml.safe_load(text) or {}
    except ImportError:
        # Minimal fallback
        from aegis.core.config import _parse_simple_yaml
        return _parse_simple_yaml(text)


def _load_validators(template_name: str) -> list[BaseValidator]:
    """Instantiate all validators for a template."""
    if template_name == "hse":
        from aegis.templates.hse.hse_validators import (
            CNESSTCompliance,
            EPIValidator,
            HazardMinimizer,
            SSTFactCheck,
        )
        return [
            SSTFactCheck(),
            EPIValidator(),
            CNESSTCompliance(),
            HazardMinimizer(),
        ]
    # Future templates: health, finance, legal, general
    return []
