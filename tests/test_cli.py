"""Tests for aegis.cli — CLI commands."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from aegis.cli import main, cmd_init, cmd_status, cmd_test


@pytest.fixture(autouse=True)
def _restore_cwd() -> None:
    """Restore working directory after each test (cmd_init uses os.chdir)."""
    original = os.getcwd()
    yield  # type: ignore[misc]
    os.chdir(original)


# ---------------------------------------------------------------------------
# aegis init
# ---------------------------------------------------------------------------

class TestCmdInit:
    def test_creates_aegis_yaml(self, tmp_path: Path) -> None:
        os.chdir(tmp_path)
        args = mock.Mock(workspace=None, force=False)
        cmd_init(args)
        cfg = tmp_path / "aegis.yaml"
        assert cfg.exists()
        content = cfg.read_text()
        assert "workspace:" in content
        assert "modules:" in content

    def test_custom_workspace(self, tmp_path: Path) -> None:
        os.chdir(tmp_path)
        args = mock.Mock(workspace="my-org", force=False)
        cmd_init(args)
        content = (tmp_path / "aegis.yaml").read_text()
        assert "workspace: my-org" in content

    def test_no_overwrite_without_force(self, tmp_path: Path) -> None:
        os.chdir(tmp_path)
        (tmp_path / "aegis.yaml").write_text("existing")
        args = mock.Mock(workspace=None, force=False)
        with pytest.raises(SystemExit):
            cmd_init(args)

    def test_overwrite_with_force(self, tmp_path: Path) -> None:
        os.chdir(tmp_path)
        (tmp_path / "aegis.yaml").write_text("old")
        args = mock.Mock(workspace="new-ws", force=True)
        cmd_init(args)
        content = (tmp_path / "aegis.yaml").read_text()
        assert "workspace: new-ws" in content


# ---------------------------------------------------------------------------
# aegis status
# ---------------------------------------------------------------------------

class TestCmdStatus:
    def test_status_empty(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        args = mock.Mock(workspace=None, limit=20, db=str(tmp_path / "test.db"))
        cmd_status(args)
        out = capsys.readouterr().out
        assert "No traces recorded" in out

    def test_status_with_traces(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from aegis.core.trace import Span
        from aegis.local.store import LocalStore

        db_path = tmp_path / "test.db"
        store = LocalStore(db_path=db_path)
        span = Span(name="test-op", workspace="demo")
        span.start_time = 1000.0
        span.end_time = 1000.05
        store.store_span(span)

        args = mock.Mock(workspace=None, limit=20, db=str(db_path))
        cmd_status(args)
        out = capsys.readouterr().out
        assert "demo" in out
        assert "Total traces:" in out
        assert "test-op" in out


# ---------------------------------------------------------------------------
# aegis test
# ---------------------------------------------------------------------------

class TestCmdTest:
    def test_missing_golden_set(self, tmp_path: Path) -> None:
        os.chdir(tmp_path)
        args = mock.Mock(golden_set="nonexistent.yaml")
        with pytest.raises(SystemExit):
            cmd_test(args)

    def test_all_passing(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        golden = tmp_path / "golden.yaml"
        golden.write_text(
            "- name: case-1\n  expected: hello\n  actual: hello\n"
            "- name: case-2\n  expected: world\n  actual: world\n"
        )
        args = mock.Mock(golden_set=str(golden))
        cmd_test(args)
        out = capsys.readouterr().out
        assert "2 passed, 0 failed" in out

    def test_with_failures(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        golden = tmp_path / "golden.yaml"
        golden.write_text(
            "- name: case-1\n  expected: hello\n  actual: wrong\n"
        )
        args = mock.Mock(golden_set=str(golden))
        with pytest.raises(SystemExit):
            cmd_test(args)
        out = capsys.readouterr().out
        assert "FAIL" in out


# ---------------------------------------------------------------------------
# main() entry point
# ---------------------------------------------------------------------------

class TestMainEntryPoint:
    def test_no_command_shows_help(self, capsys: pytest.CaptureFixture) -> None:
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 0

    def test_version(self, capsys: pytest.CaptureFixture) -> None:
        with pytest.raises(SystemExit):
            main(["--version"])
        out = capsys.readouterr().out
        assert "0.3.0" in out

    def test_init_via_main(self, tmp_path: Path) -> None:
        os.chdir(tmp_path)
        main(["init", "--workspace", "test-ws"])
        assert (tmp_path / "aegis.yaml").exists()

    def test_status_via_main(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        db = str(tmp_path / "test.db")
        main(["status", "--db", db])
        out = capsys.readouterr().out
        assert "AEGIS-X5 Status" in out
