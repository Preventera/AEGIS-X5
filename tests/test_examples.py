"""Tests for examples/ — verify each example imports and basic functions work."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from unittest import mock

import pytest

from aegis import Aegis
from aegis.core.trace import get_collector


@pytest.fixture(autouse=True)
def _clear_collector() -> None:
    get_collector().clear()


# ---------------------------------------------------------------------------
# Example: langchain_rag.py
# ---------------------------------------------------------------------------

class TestLangchainRagExample:
    def test_imports(self) -> None:
        """The example module should import without errors."""
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
        try:
            import langchain_rag  # type: ignore[import-not-found]
        finally:
            sys.path.pop(0)

    def test_retrieve(self) -> None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
        try:
            import langchain_rag

            docs = langchain_rag.retrieve("guard levels")
            assert isinstance(docs, list)
            assert len(docs) > 0
        finally:
            sys.path.pop(0)

    def test_rag_pipeline(self) -> None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
        try:
            import langchain_rag

            result = langchain_rag.rag_pipeline("guard levels")
            assert isinstance(result, str)
            assert len(result) > 0
        finally:
            sys.path.pop(0)


# ---------------------------------------------------------------------------
# Example: crewai_team.py
# ---------------------------------------------------------------------------

class TestCrewaiTeamExample:
    def test_imports(self) -> None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
        try:
            import crewai_team  # type: ignore[import-not-found]
        finally:
            sys.path.pop(0)

    def test_run_crew(self) -> None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
        try:
            import crewai_team

            result = crewai_team.run_crew("test topic")
            assert isinstance(result, str)
            assert "APPROVED" in result
        finally:
            sys.path.pop(0)


# ---------------------------------------------------------------------------
# Example: fastapi_endpoint.py
# ---------------------------------------------------------------------------

class TestFastapiExample:
    def test_process_query(self) -> None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
        try:
            import fastapi_endpoint  # type: ignore[import-not-found]

            result = fastapi_endpoint.process_query("test")
            assert "test" in result
        finally:
            sys.path.pop(0)


# ---------------------------------------------------------------------------
# Example: claude_agent.py (just import — actual Claude calls are mocked)
# ---------------------------------------------------------------------------

class TestClaudeAgentExample:
    def test_imports(self) -> None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
        try:
            import claude_agent  # type: ignore[import-not-found]
        finally:
            sys.path.pop(0)


# ---------------------------------------------------------------------------
# Example: openai_agent.py (just import)
# ---------------------------------------------------------------------------

class TestOpenaiAgentExample:
    def test_imports(self) -> None:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
        try:
            import openai_agent  # type: ignore[import-not-found]
        finally:
            sys.path.pop(0)
