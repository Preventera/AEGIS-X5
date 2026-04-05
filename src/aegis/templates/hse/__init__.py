"""HSE (Health, Safety & Environment) industry governance template.

Pre-configured validators, config, evaluation sets, and collection sources
calibrated for occupational health & safety in Quebec/Canadian context.
"""

from aegis.templates.hse.hse_validators import (
    CNESSTCompliance,
    EPIValidator,
    HazardMinimizer,
    SSTFactCheck,
)

__all__ = [
    "CNESSTCompliance",
    "EPIValidator",
    "HazardMinimizer",
    "SSTFactCheck",
]
