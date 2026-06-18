"""resolve_analyzer : réel si env=1 ET claude présent ; sinon HeuristicAnalyzer."""

from __future__ import annotations

import pytest

from conductor.harness.analyzer import ClaudeSubagentAnalyzer
from conductor.harness.resolve import resolve_analyzer
from conductor.onramp.analyzer import HeuristicAnalyzer


def test_default_is_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONDUCTOR_USE_CLAUDE_ANALYZER", raising=False)
    assert isinstance(resolve_analyzer(), HeuristicAnalyzer)


def test_env_off_is_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_USE_CLAUDE_ANALYZER", "0")
    assert isinstance(resolve_analyzer(), HeuristicAnalyzer)


def test_env_on_with_claude_is_subagent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_USE_CLAUDE_ANALYZER", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: "/usr/bin/claude")
    assert isinstance(resolve_analyzer(), ClaudeSubagentAnalyzer)


def test_env_on_without_claude_is_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_USE_CLAUDE_ANALYZER", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: None)
    assert isinstance(resolve_analyzer(), HeuristicAnalyzer)
