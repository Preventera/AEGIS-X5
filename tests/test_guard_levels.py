"""Tests for aegis.core.guard_levels — N1–N4 levels, result, violation."""

from __future__ import annotations

import pytest

from aegis.core.guard_levels import GuardLevel, GuardResult, GuardViolation


class TestGuardLevel:
    def test_ordering(self):
        assert GuardLevel.N1 < GuardLevel.N2 < GuardLevel.N3 < GuardLevel.N4

    def test_values(self):
        assert GuardLevel.N1 == 1
        assert GuardLevel.N4 == 4

    def test_by_name(self):
        assert GuardLevel["N3"] == GuardLevel.N3


class TestGuardResult:
    def test_passed(self):
        r = GuardResult(passed=True, level=GuardLevel.N1)
        assert r.passed
        assert not r.should_block

    def test_failed_n1_no_block(self):
        r = GuardResult(passed=False, level=GuardLevel.N1, rule="length-check")
        assert not r.should_block

    def test_failed_n2_no_block(self):
        r = GuardResult(passed=False, level=GuardLevel.N2)
        assert not r.should_block

    def test_failed_n3_blocks(self):
        r = GuardResult(passed=False, level=GuardLevel.N3, rule="pii", message="SSN detected")
        assert r.should_block

    def test_failed_n4_blocks(self):
        r = GuardResult(passed=False, level=GuardLevel.N4, rule="kill", message="critical")
        assert r.should_block

    def test_passed_n4_no_block(self):
        r = GuardResult(passed=True, level=GuardLevel.N4)
        assert not r.should_block

    def test_metadata(self):
        r = GuardResult(passed=True, level=GuardLevel.N1, metadata={"score": 0.95})
        assert r.metadata["score"] == 0.95


class TestGuardViolation:
    def test_exception(self):
        result = GuardResult(passed=False, level=GuardLevel.N3, rule="pii", message="SSN found")
        exc = GuardViolation(result)
        assert exc.result is result
        assert "N3" in str(exc)
        assert "pii" in str(exc)

    def test_raise_and_catch(self):
        result = GuardResult(passed=False, level=GuardLevel.N4, rule="kill", message="halt")
        with pytest.raises(GuardViolation) as exc_info:
            raise GuardViolation(result)
        assert exc_info.value.result.level == GuardLevel.N4
