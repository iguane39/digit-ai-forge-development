"""ClaudeCliBadRunner : overlay PATH du shim gh→az calculé ssi Azure DevOps (non-régression GH)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest

from conductor.harness import bad_runner
from conductor.harness.bad_runner import ClaudeCliBadRunner


class _SpyCli:
    """Capture l'``env_overlay`` reçu par SubprocessClaudeCli lors de la construction paresseuse."""

    last_overlay: Mapping[str, str] | None = None

    def __init__(
        self, *, skip_permissions: bool = False, env_overlay: Mapping[str, str] | None = None
    ) -> None:
        _SpyCli.last_overlay = env_overlay

    def run(self, prompt: str, cwd: Path) -> str:
        return ""


class _FakeCli:
    def run(self, prompt: str, cwd: Path) -> str:
        return ""


def test_azure_devops_prefixes_shim_overlay(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _SpyCli.last_overlay = None
    monkeypatch.setattr(bad_runner, "detect_provider", lambda p: "azure-devops")
    monkeypatch.setattr(bad_runner, "path_overlay", lambda: {"PATH": "SHIM_BIN::rest"})
    monkeypatch.setattr(bad_runner, "SubprocessClaudeCli", _SpyCli)
    ClaudeCliBadRunner()._cli_for(tmp_path)
    assert _SpyCli.last_overlay == {"PATH": "SHIM_BIN::rest"}


def test_github_has_no_overlay(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _SpyCli.last_overlay = {"sentinel": "unset"}
    monkeypatch.setattr(bad_runner, "detect_provider", lambda p: "github")
    monkeypatch.setattr(bad_runner, "SubprocessClaudeCli", _SpyCli)
    ClaudeCliBadRunner()._cli_for(tmp_path)
    assert _SpyCli.last_overlay is None  # PATH normal, gh réel


def test_injected_cli_is_used_verbatim(tmp_path: Path) -> None:
    cli = _FakeCli()
    assert ClaudeCliBadRunner(cli=cli)._cli_for(tmp_path) is cli
