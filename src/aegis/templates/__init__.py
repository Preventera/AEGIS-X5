"""aegis.templates — Industry governance templates.

Pre-configured profiles for HSE, Health, Finance, Legal, and General.

Usage::

    from aegis.templates.loader import load_template
    tpl = load_template("hse")
"""

from aegis.templates.loader import TemplateConfig, available_templates, load_template

__all__ = ["TemplateConfig", "available_templates", "load_template"]
