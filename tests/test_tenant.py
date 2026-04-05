"""Tests for aegis.core.tenant — multi-tenancy and workspace isolation."""

from __future__ import annotations

import pytest

from aegis.core.tenant import (
    Tenant,
    TenantContext,
    get_current_tenant,
    reset_tenant,
    set_current_tenant,
)


class TestTenant:
    def test_create(self):
        t = Tenant(workspace="acme")
        assert t.workspace == "acme"
        assert len(t.tenant_id) == 16

    def test_custom_tenant_id(self):
        t = Tenant(workspace="acme", tenant_id="custom123")
        assert t.tenant_id == "custom123"

    def test_empty_workspace_raises(self):
        with pytest.raises(ValueError, match="workspace"):
            Tenant(workspace="")

    def test_frozen(self):
        t = Tenant(workspace="x")
        with pytest.raises(AttributeError):
            t.workspace = "y"  # type: ignore[misc]


class TestTenantContextVar:
    def test_set_none_and_get(self):
        # Explicitly set None and verify it sticks
        token = set_current_tenant(None)  # type: ignore[arg-type]
        assert get_current_tenant() is None
        reset_tenant(token)

    def test_set_and_get(self):
        t = Tenant(workspace="org1")
        token = set_current_tenant(t)
        assert get_current_tenant() is t
        reset_tenant(token)

    def test_reset_restores_previous(self):
        t1 = Tenant(workspace="org1")
        t2 = Tenant(workspace="org2")
        tok1 = set_current_tenant(t1)
        tok2 = set_current_tenant(t2)
        assert get_current_tenant() is t2
        reset_tenant(tok2)
        assert get_current_tenant() is t1
        reset_tenant(tok1)


class TestTenantContext:
    def test_context_manager(self):
        t = Tenant(workspace="ctx-org")
        with TenantContext(t) as active:
            assert active is t
            assert get_current_tenant() is t

    def test_restores_after_exit(self):
        original = Tenant(workspace="original")
        nested = Tenant(workspace="nested")
        tok = set_current_tenant(original)
        with TenantContext(nested):
            assert get_current_tenant() is nested
        assert get_current_tenant() is original
        reset_tenant(tok)

    def test_restores_on_exception(self):
        t = Tenant(workspace="err-org")
        before = get_current_tenant()
        with pytest.raises(RuntimeError), TenantContext(t):
            raise RuntimeError("boom")
        assert get_current_tenant() is before
