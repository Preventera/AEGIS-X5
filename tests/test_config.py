"""Tests for aegis.core.config — YAML + env var loading, multi-workspace."""

from __future__ import annotations

import textwrap

import pytest

from aegis.core.config import AegisConfig, _deep_merge, _parse_simple_yaml, load_config

# ---------------------------------------------------------------------------
# _deep_merge
# ---------------------------------------------------------------------------


class TestDeepMerge:
    def test_flat_merge(self):
        assert _deep_merge({"a": 1}, {"b": 2}) == {"a": 1, "b": 2}

    def test_override(self):
        assert _deep_merge({"a": 1}, {"a": 99}) == {"a": 99}

    def test_nested(self):
        base = {"x": {"a": 1, "b": 2}}
        over = {"x": {"b": 3, "c": 4}}
        assert _deep_merge(base, over) == {"x": {"a": 1, "b": 3, "c": 4}}

    def test_does_not_mutate(self):
        base = {"a": 1}
        over = {"a": 2}
        _deep_merge(base, over)
        assert base == {"a": 1}


# ---------------------------------------------------------------------------
# _parse_simple_yaml
# ---------------------------------------------------------------------------


class TestParseSimpleYaml:
    def test_key_value(self):
        assert _parse_simple_yaml("workspace: acme") == {"workspace": "acme"}

    def test_booleans(self):
        result = _parse_simple_yaml("enabled: true\ndisabled: false")
        assert result == {"enabled": True, "disabled": False}

    def test_integers(self):
        assert _parse_simple_yaml("port: 8080") == {"port": 8080}

    def test_comments_and_blanks(self):
        text = "# comment\n\nkey: value\n"
        assert _parse_simple_yaml(text) == {"key": "value"}


# ---------------------------------------------------------------------------
# AegisConfig validation
# ---------------------------------------------------------------------------


class TestAegisConfig:
    def test_valid(self):
        cfg = AegisConfig(workspace="acme", modules=("observe", "guard"), autonomy="semi-auto")
        assert cfg.workspace == "acme"
        assert cfg.autonomy == "semi-auto"

    def test_empty_workspace_raises(self):
        with pytest.raises(ValueError, match="workspace"):
            AegisConfig(workspace="")

    def test_unknown_module_raises(self):
        with pytest.raises(ValueError, match="Unknown modules"):
            AegisConfig(workspace="x", modules=("observe", "alien"))

    def test_bad_autonomy_raises(self):
        with pytest.raises(ValueError, match="autonomy"):
            AegisConfig(workspace="x", autonomy="yolo")


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


class TestLoadConfig:
    def test_explicit_kwargs(self):
        cfg = load_config(workspace="org1", api_key="key1", modules=["guard"], autonomy="full-auto")
        assert cfg.workspace == "org1"
        assert cfg.api_key == "key1"
        assert cfg.modules == ("guard",)
        assert cfg.autonomy == "full-auto"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("AEGIS_WORKSPACE", "from-env")
        monkeypatch.setenv("AEGIS_API_KEY", "env-key")
        cfg = load_config()
        assert cfg.workspace == "from-env"
        assert cfg.api_key == "env-key"

    def test_explicit_beats_env(self, monkeypatch):
        monkeypatch.setenv("AEGIS_WORKSPACE", "env-ws")
        cfg = load_config(workspace="explicit-ws")
        assert cfg.workspace == "explicit-ws"

    def test_yaml_file(self, tmp_path):
        yaml_file = tmp_path / "aegis.yaml"
        yaml_file.write_text(
            textwrap.dedent("""\
            workspace: yaml-org
            api_key: yaml-key
            autonomy: semi-auto
            """)
        )
        cfg = load_config(config_path=yaml_file, modules=["observe"])
        assert cfg.workspace == "yaml-org"
        assert cfg.api_key == "yaml-key"
        assert cfg.autonomy == "semi-auto"

    def test_yaml_missing_file(self, tmp_path):
        cfg = load_config(
            config_path=tmp_path / "nope.yaml", workspace="fallback", modules=["observe"]
        )
        assert cfg.workspace == "fallback"

    def test_modules_from_comma_string(self, tmp_path):
        yaml_file = tmp_path / "aegis.yaml"
        yaml_file.write_text("workspace: x\nmodules: observe,guard\n")
        cfg = load_config(config_path=yaml_file)
        assert set(cfg.modules) == {"observe", "guard"}

    def test_default_values(self):
        cfg = load_config(workspace="w")
        assert cfg.modules == ("observe",)
        assert cfg.autonomy == "monitor"
