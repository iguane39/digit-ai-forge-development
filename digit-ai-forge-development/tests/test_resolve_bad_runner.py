"""resolve_bad_runner : ClaudeCliBadRunner si env=1 + claude + gh ; sinon DefaultBadRunner."""

from __future__ import annotations

import pytest

from conductor.harness.bad_runner import ClaudeCliBadRunner
from conductor.harness.resolve import resolve_bad_runner
from conductor.supervisor import DefaultBadRunner


def test_default_is_default_bad_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONDUCTOR_ENABLE_REAL_BAD", raising=False)
    assert isinstance(resolve_bad_runner(), DefaultBadRunner)


def test_env_on_with_tools_is_real(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_ENABLE_REAL_BAD", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: "/usr/bin/x")
    assert isinstance(resolve_bad_runner(), ClaudeCliBadRunner)


def test_env_on_without_tools_is_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_ENABLE_REAL_BAD", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: None)
    assert isinstance(resolve_bad_runner(), DefaultBadRunner)
