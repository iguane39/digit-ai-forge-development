"""resolve_bmad_planner : ClaudeCliBmadPlanner si env=1 + claude + isolation ; sinon défaut.

TF-0103.1 : le flag d'effets réels exige une isolation processus détectée — l'ancien
comportement (real dès `claude` présent) est désormais refusé hors isolation.
"""

from __future__ import annotations

import pytest

from conductor.bmad_bridge import DefaultBmadPlanner
from conductor.harness.bmad_planner import ClaudeCliBmadPlanner
from conductor.harness.resolve import resolve_bmad_planner
from conductor.sandbox import IsolationRequiredError


def test_default_is_default_planner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONDUCTOR_ENABLE_REAL_BMAD", raising=False)
    assert isinstance(resolve_bmad_planner(), DefaultBmadPlanner)


def test_env_on_with_claude_and_isolation_is_real(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture verte : `claude` présent ET isolation détectée → planner réel."""
    monkeypatch.setenv("CONDUCTOR_ENABLE_REAL_BMAD", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: "/usr/bin/claude")
    monkeypatch.setattr("conductor.sandbox.is_isolated", lambda: True)
    assert isinstance(resolve_bmad_planner(), ClaudeCliBmadPlanner)


def test_env_on_without_claude_is_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_ENABLE_REAL_BMAD", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: None)
    assert isinstance(resolve_bmad_planner(), DefaultBmadPlanner)


def test_env_on_with_claude_sans_isolation_est_refuse(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture rouge (TF-0103.1) : `claude` présent mais isolation absente → refus explicite."""
    monkeypatch.setenv("CONDUCTOR_ENABLE_REAL_BMAD", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: "/usr/bin/claude")
    monkeypatch.setattr("conductor.sandbox.is_isolated", lambda: False)
    with pytest.raises(IsolationRequiredError, match="CONDUCTOR_ENABLE_REAL_BMAD"):
        resolve_bmad_planner()
