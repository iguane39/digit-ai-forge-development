"""resolve_bmad_planner : ClaudeCliBmadPlanner si env=1 + claude ; sinon DefaultBmadPlanner."""

from __future__ import annotations

import pytest

from conductor.bmad_bridge import DefaultBmadPlanner
from conductor.harness.bmad_planner import ClaudeCliBmadPlanner
from conductor.harness.resolve import resolve_bmad_planner


def test_default_is_default_planner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONDUCTOR_ENABLE_REAL_BMAD", raising=False)
    assert isinstance(resolve_bmad_planner(), DefaultBmadPlanner)


def test_env_on_with_claude_is_real(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_ENABLE_REAL_BMAD", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: "/usr/bin/claude")
    assert isinstance(resolve_bmad_planner(), ClaudeCliBmadPlanner)


def test_env_on_without_claude_is_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_ENABLE_REAL_BMAD", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: None)
    assert isinstance(resolve_bmad_planner(), DefaultBmadPlanner)
