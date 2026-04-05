"""Tests for aegis.templates.loader — template loading system."""

from __future__ import annotations

import pytest

from aegis.templates.loader import (
    TemplateConfig,
    available_templates,
    load_template,
)

# ---------------------------------------------------------------------------
# HSE template loading
# ---------------------------------------------------------------------------

class TestLoadHSETemplate:
    def test_loads_successfully(self) -> None:
        tpl = load_template("hse")
        assert isinstance(tpl, TemplateConfig)
        assert tpl.name == "hse"

    def test_has_config_data(self) -> None:
        tpl = load_template("hse")
        assert "workspace" in tpl.config_data
        assert "guard" in tpl.config_data
        assert "evaluate" in tpl.config_data

    def test_config_faithfulness_threshold(self) -> None:
        tpl = load_template("hse")
        assert tpl.config_data["evaluate"]["faithfulness_threshold"] >= 0.97

    def test_config_guard_level_n4(self) -> None:
        tpl = load_template("hse")
        assert tpl.config_data["guard"]["level"] == "N4"

    def test_has_validators(self) -> None:
        tpl = load_template("hse")
        assert len(tpl.validators) == 4
        names = [v.name for v in tpl.validators]
        assert "sst-fact-check" in names
        assert "epi-validator" in names
        assert "cnesst-compliance" in names
        assert "hazard-minimizer" in names

    def test_has_golden_set(self) -> None:
        tpl = load_template("hse")
        assert "cases" in tpl.golden_set
        cases = tpl.golden_set["cases"]
        assert len(cases) == 20

    def test_golden_set_balance(self) -> None:
        tpl = load_template("hse")
        cases = tpl.golden_set["cases"]
        passing = [c for c in cases if c["expected_pass"]]
        failing = [c for c in cases if not c["expected_pass"]]
        assert len(passing) == 10
        assert len(failing) == 10

    def test_has_sources(self) -> None:
        tpl = load_template("hse")
        assert "sources" in tpl.sources
        sources = tpl.sources["sources"]
        assert len(sources) >= 5
        domains = [s["domain"] for s in sources]
        assert "cnesst.gouv.qc.ca" in domains
        assert "irsst.qc.ca" in domains

    def test_has_regulations(self) -> None:
        tpl = load_template("hse")
        assert len(tpl.regulations) >= 5
        reg_names = [r["name"] for r in tpl.regulations]
        assert "ISO 45001" in reg_names
        assert "CNESST RSST" in reg_names

    def test_sources_confidence_scoring(self) -> None:
        tpl = load_template("hse")
        for source in tpl.sources["sources"]:
            assert 0.0 < source["confidence"] <= 1.0

    def test_sources_have_keywords(self) -> None:
        tpl = load_template("hse")
        for source in tpl.sources["sources"]:
            assert "keywords" in source
            assert len(source["keywords"]) >= 1


# ---------------------------------------------------------------------------
# Template loader edge cases
# ---------------------------------------------------------------------------

class TestTemplateLoaderEdgeCases:
    def test_unknown_template(self) -> None:
        with pytest.raises(ValueError, match="not found"):
            load_template("nonexistent")

    def test_available_templates(self) -> None:
        templates = available_templates()
        assert "hse" in templates
        assert isinstance(templates, list)

    def test_template_config_dataclass(self) -> None:
        tpl = TemplateConfig(name="test")
        assert tpl.name == "test"
        assert tpl.validators == []
        assert tpl.config_data == {}
        assert tpl.golden_set == {}


# ---------------------------------------------------------------------------
# HSE golden set validation with actual validators
# ---------------------------------------------------------------------------

class TestHSEGoldenSetValidation:
    """Run HSE validators against the golden set to verify calibration."""

    def test_passing_cases_pass_sst_factcheck(self) -> None:
        tpl = load_template("hse")
        from aegis.templates.hse.hse_validators import SSTFactCheck

        v = SSTFactCheck()
        passing = [c for c in tpl.golden_set["cases"] if c["expected_pass"]]
        for case in passing:
            result = v.validate(case["response"])
            assert result.passed, f"Case {case['name']} should pass SSTFactCheck but failed: {result.message}"

    def test_dangerous_cases_fail_sst_factcheck(self) -> None:
        tpl = load_template("hse")
        from aegis.templates.hse.hse_validators import SSTFactCheck

        v = SSTFactCheck()
        dangerous = [
            c for c in tpl.golden_set["cases"]
            if not c["expected_pass"] and c.get("category") == "dangerous_claim"
        ]
        for case in dangerous:
            result = v.validate(case["response"])
            assert not result.passed, f"Case {case['name']} should fail SSTFactCheck"

    def test_minimization_cases_fail_hazard_minimizer(self) -> None:
        tpl = load_template("hse")
        from aegis.templates.hse.hse_validators import HazardMinimizer

        v = HazardMinimizer()
        minimization = [
            c for c in tpl.golden_set["cases"]
            if not c["expected_pass"] and c.get("category") == "minimization"
        ]
        for case in minimization:
            result = v.validate(case["response"])
            assert not result.passed, f"Case {case['name']} should fail HazardMinimizer"
