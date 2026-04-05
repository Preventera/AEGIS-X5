"""Tests for aegis.templates.hse.hse_validators — HSE-specific guard validators."""

from __future__ import annotations

import pytest

from aegis.core.guard_levels import GuardLevel
from aegis.templates.hse.hse_validators import (
    CNESSTCompliance,
    EPIValidator,
    HazardMinimizer,
    SSTFactCheck,
)


# ---------------------------------------------------------------------------
# SSTFactCheck
# ---------------------------------------------------------------------------

class TestSSTFactCheck:
    def setup_method(self) -> None:
        self.v = SSTFactCheck()

    def test_safe_response_passes(self) -> None:
        r = self.v.validate("Portez un casque et des bottes de sécurité sur le chantier.")
        assert r.passed is True

    def test_100_pourcent_sur(self) -> None:
        r = self.v.validate("Ce produit est 100% sûr pour une utilisation quotidienne.")
        assert r.passed is False
        assert "absolute safety claim" in r.message

    def test_aucun_risque(self) -> None:
        r = self.v.validate("Il y a aucun risque à travailler sans protection.")
        assert r.passed is False

    def test_no_risk_english(self) -> None:
        r = self.v.validate("There is no risk when operating this equipment.")
        assert r.passed is False

    def test_pas_besoin_epi(self) -> None:
        r = self.v.validate("Pas besoin d'EPI pour cette tâche simple.")
        assert r.passed is False
        assert "PPE dismissal" in r.message

    def test_no_need_ppe_english(self) -> None:
        r = self.v.validate("You don't need any PPE for this task.")
        assert r.passed is False

    def test_ignorer_procedure(self) -> None:
        r = self.v.validate("Vous pouvez ignorer la procédure de cadenassage si pressé.")
        assert r.passed is False
        assert "procedure bypass" in r.message

    def test_skip_safety_check(self) -> None:
        r = self.v.validate("Just skip the safety check, it's faster.")
        assert r.passed is False

    def test_completely_safe(self) -> None:
        r = self.v.validate("This chemical is completely safe to handle without gloves.")
        assert r.passed is False

    def test_level_is_n4(self) -> None:
        assert self.v.level == GuardLevel.N4

    def test_name(self) -> None:
        assert self.v.name == "sst-fact-check"

    def test_multiple_violations(self) -> None:
        r = self.v.validate("Aucun risque, c'est 100% sûr, pas besoin d'EPI.")
        assert r.passed is False
        assert r.metadata["count"] >= 2


# ---------------------------------------------------------------------------
# EPIValidator
# ---------------------------------------------------------------------------

class TestEPIValidator:
    def setup_method(self) -> None:
        self.v = EPIValidator()

    def test_correct_chantier_epi(self) -> None:
        r = self.v.validate(
            "Sur le chantier, portez un casque, des bottes de sécurité et un dossard."
        )
        assert r.passed is True

    def test_missing_chantier_epi(self) -> None:
        r = self.v.validate(
            "Sur le chantier, portez des vêtements confortables et un chapeau."
        )
        assert r.passed is False
        assert "Missing PPE" in r.message

    def test_correct_soudage_epi(self) -> None:
        r = self.v.validate(
            "Pour le soudage, utilisez un masque de soudeur, des gants et des lunettes."
        )
        assert r.passed is True

    def test_correct_hauteur_epi(self) -> None:
        r = self.v.validate(
            "Pour le travail en hauteur, portez un harnais de sécurité avec ligne de vie."
        )
        assert r.passed is True

    def test_correct_bruit_epi(self) -> None:
        r = self.v.validate(
            "En zone de bruit, portez des bouchons d'oreille ou des coquilles."
        )
        assert r.passed is True

    def test_correct_chimique_epi(self) -> None:
        r = self.v.validate(
            "Pour les produits chimiques, portez des gants et des lunettes de protection."
        )
        assert r.passed is True

    def test_no_hazard_context_passes(self) -> None:
        r = self.v.validate("Bonne journée à tous les travailleurs!")
        assert r.passed is True

    def test_level_is_n3(self) -> None:
        assert self.v.level == GuardLevel.N3

    def test_context_hazard_override(self) -> None:
        r = self.v.validate(
            "Portez des vêtements légers.",
            context={"hazard": "construction"},
        )
        assert r.passed is False

    def test_espace_confine_epi(self) -> None:
        r = self.v.validate(
            "Pour l'espace confiné, utilisez un détecteur de gaz et un harnais."
        )
        assert r.passed is True

    def test_amiante_epi(self) -> None:
        r = self.v.validate(
            "Pour l'amiante, portez une combinaison et un respirateur."
        )
        assert r.passed is True


# ---------------------------------------------------------------------------
# CNESSTCompliance
# ---------------------------------------------------------------------------

class TestCNESSTCompliance:
    def setup_method(self) -> None:
        self.v = CNESSTCompliance()

    def test_non_regulatory_passes(self) -> None:
        r = self.v.validate("Portez un casque sur le chantier.")
        assert r.passed is True

    def test_regulatory_with_reference(self) -> None:
        r = self.v.validate(
            "Le droit de refus est garanti par la LSST. La CNESST peut intervenir."
        )
        assert r.passed is True

    def test_regulatory_without_reference(self) -> None:
        r = self.v.validate(
            "Le droit de refus permet au travailleur de refuser un travail dangereux."
        )
        assert r.passed is False
        assert "CNESST" in r.message

    def test_declaration_accident_with_ref(self) -> None:
        r = self.v.validate(
            "La déclaration d'accident doit être faite selon le RSST de la CNESST."
        )
        assert r.passed is True

    def test_programme_prevention_without_ref(self) -> None:
        r = self.v.validate(
            "Le programme de prévention identifie les risques et mesures correctives."
        )
        assert r.passed is False

    def test_context_forces_regulatory(self) -> None:
        r = self.v.validate(
            "Les travailleurs doivent être formés.",
            context={"regulatory": True},
        )
        assert r.passed is False

    def test_level_is_n3(self) -> None:
        assert self.v.level == GuardLevel.N3


# ---------------------------------------------------------------------------
# HazardMinimizer
# ---------------------------------------------------------------------------

class TestHazardMinimizer:
    def setup_method(self) -> None:
        self.v = HazardMinimizer()

    def test_safe_response(self) -> None:
        r = self.v.validate("La chute de hauteur est un risque majeur. Portez un harnais.")
        assert r.passed is True

    def test_severity_downplay(self) -> None:
        r = self.v.validate("C'est pas si grave, une chute de 3 mètres.")
        assert r.passed is False
        assert "severity downplay" in r.message

    def test_worry_dismissal_fr(self) -> None:
        r = self.v.validate("Ne t'inquiète pas, le produit est inoffensif.")
        assert r.passed is False

    def test_worry_dismissal_en(self) -> None:
        r = self.v.validate("Don't worry about the asbestos exposure.")
        assert r.passed is False

    def test_risk_minimization(self) -> None:
        r = self.v.validate("Peu de risque de blessure à cette hauteur.")
        assert r.passed is False

    def test_frequency_downplay(self) -> None:
        r = self.v.validate("Les chutes mortelles sont rarement dangereuses.")
        assert r.passed is False

    def test_concern_dismissal(self) -> None:
        r = self.v.validate("Les risques de l'amiante sont souvent exagérés.")
        assert r.passed is False

    def test_not_really_dangerous(self) -> None:
        r = self.v.validate("Ce n'est pas vraiment dangereux à cette dose.")
        assert r.passed is False

    def test_risk_trivialization(self) -> None:
        r = self.v.validate("C'est juste un petit risque, rien de sérieux.")
        assert r.passed is False

    def test_level_is_n4(self) -> None:
        assert self.v.level == GuardLevel.N4

    def test_name(self) -> None:
        assert self.v.name == "hazard-minimizer"
