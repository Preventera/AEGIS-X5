"""Tests for aegis.tenants.shield_ops — SHIELD-OPS-X5 tenant configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from aegis.tenants.shield_ops import Platform, ShieldOpsTenant


# ---------------------------------------------------------------------------
# Platform dataclass
# ---------------------------------------------------------------------------

class TestPlatform:
    def test_basic(self) -> None:
        p = Platform(
            name="Test Platform",
            code="test",
            agent_count=10,
            status="live",
            guard_level="N3",
            modules=["observe", "guard"],
        )
        assert p.name == "Test Platform"
        assert p.code == "test"
        assert p.agent_count == 10
        assert p.is_live is True

    def test_prototype_not_live(self) -> None:
        p = Platform(
            name="Proto", code="proto", agent_count=3,
            status="prototype", guard_level="N2", modules=["observe"],
        )
        assert p.is_live is False

    def test_frozen(self) -> None:
        p = Platform(
            name="X", code="x", agent_count=1,
            status="live", guard_level="N1", modules=[],
        )
        with pytest.raises(AttributeError):
            p.name = "Y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ShieldOpsTenant — loading from YAML
# ---------------------------------------------------------------------------

class TestShieldOpsTenantLoading:
    def test_loads_21_platforms(self) -> None:
        tenant = ShieldOpsTenant()
        assert tenant.total_platforms == 21

    def test_total_agents(self) -> None:
        tenant = ShieldOpsTenant()
        assert tenant.total_agents > 500

    def test_workspace(self) -> None:
        assert ShieldOpsTenant.WORKSPACE == "shield-ops-x5"

    def test_template(self) -> None:
        assert ShieldOpsTenant.TEMPLATE == "hse"

    def test_platforms_are_platform_objects(self) -> None:
        tenant = ShieldOpsTenant()
        for p in tenant.platforms:
            assert isinstance(p, Platform)

    def test_platforms_list_is_copy(self) -> None:
        tenant = ShieldOpsTenant()
        p1 = tenant.platforms
        p2 = tenant.platforms
        assert p1 is not p2


# ---------------------------------------------------------------------------
# Specific platform lookups
# ---------------------------------------------------------------------------

class TestPlatformLookup:
    def setup_method(self) -> None:
        self.tenant = ShieldOpsTenant()

    def test_get_edgy(self) -> None:
        p = self.tenant.get_platform("edgy")
        assert p is not None
        assert p.name == "EDGY — AI Safety & Governance"
        assert p.agent_count == 122
        assert p.status == "live"
        assert p.guard_level == "N4"
        assert "loops" in p.modules

    def test_get_literacia(self) -> None:
        p = self.tenant.get_platform("literacia")
        assert p is not None
        assert p.agent_count == 122
        assert p.guard_level == "N4"

    def test_get_safefleet(self) -> None:
        p = self.tenant.get_platform("safefleet")
        assert p is not None
        assert p.agent_count == 5
        assert "remember" in p.modules

    def test_get_emergencyops(self) -> None:
        p = self.tenant.get_platform("emergencyops")
        assert p is not None
        assert p.agent_count == 61
        assert p.guard_level == "N4"
        assert "loops" in p.modules

    def test_get_nonexistent(self) -> None:
        assert self.tenant.get_platform("nonexistent") is None

    def test_all_codes_unique(self) -> None:
        codes = [p.code for p in self.tenant.platforms]
        assert len(codes) == len(set(codes))


# ---------------------------------------------------------------------------
# Live vs prototype classification
# ---------------------------------------------------------------------------

class TestPlatformClassification:
    def setup_method(self) -> None:
        self.tenant = ShieldOpsTenant()

    def test_live_platforms_count(self) -> None:
        live = self.tenant.live_platforms
        assert len(live) >= 18

    def test_prototype_platforms_count(self) -> None:
        proto = self.tenant.prototype_platforms
        assert len(proto) >= 3

    def test_live_plus_prototype_equals_total(self) -> None:
        live = len(self.tenant.live_platforms)
        proto = len(self.tenant.prototype_platforms)
        assert live + proto == self.tenant.total_platforms

    def test_all_live_are_live(self) -> None:
        for p in self.tenant.live_platforms:
            assert p.is_live is True

    def test_all_prototypes_not_live(self) -> None:
        for p in self.tenant.prototype_platforms:
            assert p.is_live is False


# ---------------------------------------------------------------------------
# Coverage matrix
# ---------------------------------------------------------------------------

class TestCoverageMatrix:
    def setup_method(self) -> None:
        self.tenant = ShieldOpsTenant()
        self.matrix = self.tenant.coverage_matrix()

    def test_all_platforms_in_matrix(self) -> None:
        assert len(self.matrix) == 21

    def test_edgy_all_modules(self) -> None:
        edgy = self.matrix["edgy"]
        assert all(edgy.values()), "EDGY should have all modules enabled"

    def test_ergosense_limited_modules(self) -> None:
        ergo = self.matrix["ergosense"]
        assert ergo["observe"] is True
        assert ergo["guard"] is True
        assert ergo["loops"] is False
        assert ergo["predict"] is False

    def test_matrix_has_all_modules(self) -> None:
        expected = {"observe", "guard", "evaluate", "collect", "remember", "predict", "loops"}
        for coverage in self.matrix.values():
            assert set(coverage.keys()) == expected


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

class TestSummary:
    def test_summary_structure(self) -> None:
        tenant = ShieldOpsTenant()
        s = tenant.summary()
        assert s["workspace"] == "shield-ops-x5"
        assert s["template"] == "hse"
        assert s["total_platforms"] == 21
        assert s["total_agents"] > 500
        assert len(s["platforms"]) == 21

    def test_summary_platform_entries(self) -> None:
        tenant = ShieldOpsTenant()
        s = tenant.summary()
        for entry in s["platforms"]:
            assert "name" in entry
            assert "code" in entry
            assert "agents" in entry
            assert "status" in entry
            assert "guard" in entry


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_missing_yaml(self, tmp_path: Path) -> None:
        tenant = ShieldOpsTenant(agents_path=tmp_path / "nonexistent.yaml")
        assert tenant.total_platforms == 0
        assert tenant.total_agents == 0

    def test_custom_yaml(self, tmp_path: Path) -> None:
        yaml_content = """
platforms:
  - name: Test
    code: test
    agent_count: 5
    status: live
    guard_level: N2
    modules: [observe]
"""
        custom = tmp_path / "custom.yaml"
        custom.write_text(yaml_content)
        tenant = ShieldOpsTenant(agents_path=custom)
        assert tenant.total_platforms == 1
        assert tenant.total_agents == 5
