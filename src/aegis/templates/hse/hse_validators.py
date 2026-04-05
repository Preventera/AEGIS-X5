"""HSE-specific Guard validators for occupational safety governance.

Four specialized validators:
- SSTFactCheck: detects safety minimization and dangerous assertions
- EPIValidator: validates PPE recommendations coherence
- CNESSTCompliance: checks Quebec regulatory compliance
- HazardMinimizer: detects when an agent downplays real hazards
"""

from __future__ import annotations

import re
from typing import Any

from aegis.core.guard_levels import GuardLevel, GuardResult
from aegis.guard.validators import BaseValidator

# ---------------------------------------------------------------------------
# SSTFactCheck — detects dangerous safety assertions
# ---------------------------------------------------------------------------

_SST_DANGER_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"100\s*%\s*s[uû]r", re.IGNORECASE), "absolute safety claim"),
    (re.compile(r"aucun\s+risque", re.IGNORECASE), "no risk claim"),
    (re.compile(r"no\s+risk", re.IGNORECASE), "no risk claim"),
    (re.compile(r"completely\s+safe", re.IGNORECASE), "absolute safety claim"),
    (re.compile(r"perfectly\s+safe", re.IGNORECASE), "absolute safety claim"),
    (re.compile(r"zero\s+risk", re.IGNORECASE), "zero risk claim"),
    (re.compile(r"pas\s+besoin\s+d['\u2019]?\s*[EÉeé]\.?[Pp]\.?[Ii]\.?", re.IGNORECASE), "PPE dismissal"),
    (re.compile(r"no\s+need\s+for\s+ppe", re.IGNORECASE), "PPE dismissal"),
    (re.compile(r"don'?t\s+need\s+(?:any\s+)?(?:ppe|protective)", re.IGNORECASE), "PPE dismissal"),
    (re.compile(r"ignorer?\s+la\s+proc[eé]dure", re.IGNORECASE), "procedure bypass"),
    (re.compile(r"ignore\s+(?:the\s+)?(?:safety\s+)?procedure", re.IGNORECASE), "procedure bypass"),
    (re.compile(r"skip\s+(?:the\s+)?(?:safety\s+)?(?:procedure|protocol|check)", re.IGNORECASE), "procedure bypass"),
    (re.compile(r"pas\s+(?:la\s+peine|n[eé]cessaire)\s+de\s+(?:v[eé]rifier|inspecter)", re.IGNORECASE), "inspection bypass"),
    (re.compile(r"(?:won'?t|can'?t|doesn'?t)\s+(?:hurt|harm|injure)", re.IGNORECASE), "harm dismissal"),
    (re.compile(r"(?:ne|n')\s+(?:peut|va)\s+pas\s+(?:blesser|causer)", re.IGNORECASE), "harm dismissal"),
]


class SSTFactCheck(BaseValidator):
    """Detects dangerous safety assertions: absolute claims, PPE dismissal,
    procedure bypass, and any minimization of occupational hazards.

    Flags at N4 (kill) by default — safety misinformation is critical.
    """

    def __init__(
        self,
        *,
        extra_patterns: list[tuple[re.Pattern[str], str]] | None = None,
        level: GuardLevel = GuardLevel.N4,
    ) -> None:
        super().__init__(name="sst-fact-check", level=level)
        self._patterns = list(_SST_DANGER_PATTERNS)
        if extra_patterns:
            self._patterns.extend(extra_patterns)

    def validate(self, content: str, *, context: dict[str, Any] | None = None) -> GuardResult:
        violations: list[dict[str, str]] = []
        for pattern, category in self._patterns:
            match = pattern.search(content)
            if match:
                violations.append({
                    "category": category,
                    "matched": match.group(),
                })

        if violations:
            categories = list({v["category"] for v in violations})
            return GuardResult(
                passed=False,
                level=self.level,
                rule=self.name,
                message=f"SST safety violation: {', '.join(categories)}",
                metadata={"violations": violations, "count": len(violations)},
            )
        return GuardResult(passed=True, level=self.level, rule=self.name)


# ---------------------------------------------------------------------------
# EPIValidator — PPE recommendation coherence
# ---------------------------------------------------------------------------

# Mapping: hazard context keyword → required PPE items
_EPI_REQUIREMENTS: dict[str, list[str]] = {
    "chantier": ["casque", "hard hat", "bottes", "safety boots", "dossard", "high-vis"],
    "construction": ["casque", "hard hat", "bottes", "safety boots", "dossard", "high-vis"],
    "soudage": ["lunettes", "safety glasses", "masque", "welding mask", "gants", "gloves"],
    "welding": ["lunettes", "safety glasses", "masque", "welding mask", "gants", "gloves"],
    "chimique": ["gants", "gloves", "lunettes", "goggles", "respirateur", "respirator"],
    "chemical": ["gants", "gloves", "lunettes", "goggles", "respirateur", "respirator"],
    "hauteur": ["harnais", "harness", "ligne de vie", "lifeline"],
    "height": ["harnais", "harness", "ligne de vie", "lifeline"],
    "bruit": ["bouchons", "ear plugs", "coquilles", "ear muffs", "protecteurs auditifs"],
    "noise": ["bouchons", "ear plugs", "coquilles", "ear muffs", "hearing protection"],
    "espace confin\u00e9": ["d\u00e9tecteur de gaz", "gas detector", "ventilation", "harnais", "harness"],
    "confined space": ["gas detector", "ventilation", "harness"],
    "amiante": ["combinaison", "coverall", "respirateur", "respirator", "masque"],
    "asbestos": ["coverall", "respirator", "mask"],
}


class EPIValidator(BaseValidator):
    """Validates that PPE/EPI recommendations are coherent with the hazard context.

    Checks if the response mentions appropriate PPE for the detected hazard.
    """

    def __init__(
        self,
        *,
        requirements: dict[str, list[str]] | None = None,
        level: GuardLevel = GuardLevel.N3,
    ) -> None:
        super().__init__(name="epi-validator", level=level)
        self._requirements = requirements or dict(_EPI_REQUIREMENTS)

    def validate(self, content: str, *, context: dict[str, Any] | None = None) -> GuardResult:
        lower = content.lower()
        ctx = context or {}
        hazard_context = ctx.get("hazard", "")

        # Detect hazard from context or content
        detected_hazards: list[str] = []
        for hazard_key in self._requirements:
            if hazard_key in lower or hazard_key in hazard_context.lower():
                detected_hazards.append(hazard_key)

        if not detected_hazards:
            return GuardResult(passed=True, level=self.level, rule=self.name)

        # Check if appropriate PPE is mentioned
        missing_ppe: list[dict[str, Any]] = []
        for hazard in detected_hazards:
            required = self._requirements[hazard]
            # At least one PPE item from the list should be mentioned
            found_any = any(epi.lower() in lower for epi in required)
            if not found_any:
                missing_ppe.append({
                    "hazard": hazard,
                    "required_ppe": required,
                })

        if missing_ppe:
            hazards_str = ", ".join(m["hazard"] for m in missing_ppe)
            return GuardResult(
                passed=False,
                level=self.level,
                rule=self.name,
                message=f"Missing PPE recommendations for: {hazards_str}",
                metadata={"missing_ppe": missing_ppe},
            )
        return GuardResult(passed=True, level=self.level, rule=self.name)


# ---------------------------------------------------------------------------
# CNESSTCompliance — Quebec regulatory compliance
# ---------------------------------------------------------------------------

_CNESST_REQUIRED_REFERENCES: list[str] = [
    "cnesst",
    "rsst",
    "code de s\u00e9curit\u00e9",
    "r\u00e8glement",
    "lsst",
    "loi sur la sant\u00e9 et la s\u00e9curit\u00e9",
]

_CNESST_TOPICS: list[str] = [
    "droit de refus",
    "right to refuse",
    "comit\u00e9 de sant\u00e9 et s\u00e9curit\u00e9",
    "repr\u00e9sentant \u00e0 la pr\u00e9vention",
    "d\u00e9claration d'accident",
    "incident report",
    "programme de pr\u00e9vention",
    "prevention program",
]


class CNESSTCompliance(BaseValidator):
    """Validates Quebec occupational safety regulatory compliance.

    Checks that responses about safety topics reference appropriate
    CNESST regulations and include required compliance elements.
    """

    def __init__(
        self,
        *,
        required_refs: list[str] | None = None,
        level: GuardLevel = GuardLevel.N3,
    ) -> None:
        super().__init__(name="cnesst-compliance", level=level)
        self._refs = required_refs or list(_CNESST_REQUIRED_REFERENCES)

    def validate(self, content: str, *, context: dict[str, Any] | None = None) -> GuardResult:
        lower = content.lower()
        ctx = context or {}

        # Only enforce compliance if topic is regulatory
        is_regulatory = ctx.get("regulatory", False)
        if not is_regulatory:
            # Auto-detect if the content discusses regulatory topics
            is_regulatory = any(topic in lower for topic in _CNESST_TOPICS)

        if not is_regulatory:
            return GuardResult(passed=True, level=self.level, rule=self.name)

        # Check for regulatory references
        has_reference = any(ref in lower for ref in self._refs)

        if not has_reference:
            return GuardResult(
                passed=False,
                level=self.level,
                rule=self.name,
                message="Regulatory topic without CNESST/RSST reference",
                metadata={"expected_refs": self._refs},
            )
        return GuardResult(passed=True, level=self.level, rule=self.name)


# ---------------------------------------------------------------------------
# HazardMinimizer — detects risk downplaying
# ---------------------------------------------------------------------------

_MINIMIZATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?:c'est|it'?s)\s+(?:pas|not)\s+(?:si|that)\s+(?:grave|dangerous|serious)", re.IGNORECASE), "severity downplay"),
    (re.compile(r"(?:don'?t|ne)\s+(?:worry|t'?inqui[eè]te)", re.IGNORECASE), "worry dismissal"),
    (re.compile(r"(?:peu|low|minor|mineur)\s+(?:de\s+)?(?:risque|risk|danger)", re.IGNORECASE), "risk minimization"),
    (re.compile(r"(?:rarement|rarely|seldom)\s+(?:dangereux|dangereuse?s?|dangerous|fatal[es]?|mortell?e?s?)", re.IGNORECASE), "frequency downplay"),
    (re.compile(r"(?:exag[eé]r|overstat|overblown|exaggerat)", re.IGNORECASE), "concern dismissal"),
    (re.compile(r"(?:pas\s+(?:vraiment|r[eé]ellement)|not\s+really)\s+(?:dangereux|dangerous|risqu[eé]|risky)", re.IGNORECASE), "danger dismissal"),
    (re.compile(r"(?:juste|just)\s+(?:un\s+petit|a\s+(?:small|little|minor))\s+(?:risque|risk)", re.IGNORECASE), "risk trivialization"),
]


class HazardMinimizer(BaseValidator):
    """Detects when an agent minimizes a real occupational hazard.

    Catches language patterns that downplay severity, dismiss concerns,
    or trivialize workplace risks.
    """

    def __init__(
        self,
        *,
        extra_patterns: list[tuple[re.Pattern[str], str]] | None = None,
        level: GuardLevel = GuardLevel.N4,
    ) -> None:
        super().__init__(name="hazard-minimizer", level=level)
        self._patterns = list(_MINIMIZATION_PATTERNS)
        if extra_patterns:
            self._patterns.extend(extra_patterns)

    def validate(self, content: str, *, context: dict[str, Any] | None = None) -> GuardResult:
        violations: list[dict[str, str]] = []
        for pattern, category in self._patterns:
            match = pattern.search(content)
            if match:
                violations.append({
                    "category": category,
                    "matched": match.group(),
                })

        if violations:
            categories = list({v["category"] for v in violations})
            return GuardResult(
                passed=False,
                level=self.level,
                rule=self.name,
                message=f"Hazard minimization detected: {', '.join(categories)}",
                metadata={"violations": violations, "count": len(violations)},
            )
        return GuardResult(passed=True, level=self.level, rule=self.name)
