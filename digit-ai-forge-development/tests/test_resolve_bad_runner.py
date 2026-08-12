"""resolve_bad_runner : ClaudeCliBadRunner si env=1 + claude + gh + isolation ; sinon stub.

TF-0103.1 : le flag d'effets réels exige une isolation processus détectée — l'ancien
comportement (real dès outils présents) est désormais refusé hors isolation.
"""

from __future__ import annotations

import pytest

from conductor.harness.bad_runner import ClaudeCliBadRunner
from conductor.harness.resolve import resolve_bad_runner
from conductor.sandbox import IsolationRequiredError
from conductor.supervisor import DefaultBadRunner


def test_default_is_default_bad_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONDUCTOR_ENABLE_REAL_BAD", raising=False)
    assert isinstance(resolve_bad_runner(), DefaultBadRunner)


def test_env_on_with_tools_and_isolation_is_real(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture verte : outils présents ET isolation détectée → runner réel."""
    monkeypatch.setenv("CONDUCTOR_ENABLE_REAL_BAD", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: "/usr/bin/x")
    monkeypatch.setattr("conductor.sandbox.is_isolated", lambda: True)
    assert isinstance(resolve_bad_runner(), ClaudeCliBadRunner)


def test_env_on_without_tools_is_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_ENABLE_REAL_BAD", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: None)
    assert isinstance(resolve_bad_runner(), DefaultBadRunner)


def test_env_on_with_tools_sans_isolation_est_refuse(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fixture rouge (TF-0103.1) : outils présents mais isolation absente → refus explicite,
    pas de repli silencieux vers le stub."""
    monkeypatch.setenv("CONDUCTOR_ENABLE_REAL_BAD", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: "/usr/bin/x")
    monkeypatch.setattr("conductor.sandbox.is_isolated", lambda: False)
    with pytest.raises(IsolationRequiredError, match="CONDUCTOR_ENABLE_REAL_BAD"):
        resolve_bad_runner()
