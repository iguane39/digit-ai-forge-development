"""SubprocessClaudeCli : invoque `claude -p … --output-format json`, renvoie `result`."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from conductor.harness.claude_cli import SubprocessClaudeCli
from conductor.process import ProcessResult, ToolNotFound


class _FakeRunner:
    """ProcessRunner factice : renvoie un ProcessResult fixé et capture les args."""

    def __init__(
        self, *, stdout: str = "", returncode: int = 0, exc: Exception | None = None
    ) -> None:
        self._stdout = stdout
        self._returncode = returncode
        self._exc = exc
        self.cmd: list[str] = []
        self.timeout_s: int | None = None

    def run(
        self, args: Sequence[str], *, cwd: Path | None = None, timeout_s: int = 300
    ) -> ProcessResult:
        self.cmd = list(args)
        self.timeout_s = timeout_s
        if self._exc is not None:
            raise self._exc
        return ProcessResult(self._returncode, self._stdout, "")


def test_returns_result_field(tmp_path: Path) -> None:
    runner = _FakeRunner(stdout=json.dumps({"result": "analyse OK"}))
    assert SubprocessClaudeCli(runner=runner).run("prompt", tmp_path) == "analyse OK"


def test_nonzero_exit_raises(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="claude"):
        SubprocessClaudeCli(runner=_FakeRunner(returncode=1)).run("p", tmp_path)


def test_invalid_json_raises(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="illisible|JSON"):
        SubprocessClaudeCli(runner=_FakeRunner(stdout="pas du json")).run("p", tmp_path)


def test_missing_result_raises(tmp_path: Path) -> None:
    runner = _FakeRunner(stdout=json.dumps({"other": 1}))
    with pytest.raises(RuntimeError, match="result"):
        SubprocessClaudeCli(runner=runner).run("p", tmp_path)


def test_timeout_propagates_as_runtimeerror(tmp_path: Path) -> None:
    # Le ProcessRunner convertit déjà TimeoutExpired en RuntimeError("… timeout …").
    runner = _FakeRunner(exc=RuntimeError("claude : timeout après 1s"))
    with pytest.raises(RuntimeError, match="timeout"):
        SubprocessClaudeCli(timeout_s=1, runner=runner).run("p", tmp_path)


def test_tool_not_found_raises_actionable(tmp_path: Path) -> None:
    runner = _FakeRunner(exc=ToolNotFound("Outil introuvable dans le PATH : 'claude'"))
    with pytest.raises(RuntimeError, match="introuvable"):
        SubprocessClaudeCli(runner=runner).run("p", tmp_path)


def test_skip_permissions_adds_flag(tmp_path: Path) -> None:
    runner = _FakeRunner(stdout=json.dumps({"result": "ok"}))
    SubprocessClaudeCli(skip_permissions=True, runner=runner).run("p", tmp_path)
    assert "--dangerously-skip-permissions" in runner.cmd


def test_default_has_no_skip_flag(tmp_path: Path) -> None:
    runner = _FakeRunner(stdout=json.dumps({"result": "ok"}))
    SubprocessClaudeCli(runner=runner).run("p", tmp_path)
    assert "--dangerously-skip-permissions" not in runner.cmd


def test_timeout_from_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_CLAUDE_TIMEOUT_S", "1800")
    runner = _FakeRunner(stdout=json.dumps({"result": "ok"}))
    SubprocessClaudeCli(runner=runner).run("p", tmp_path)
    assert runner.timeout_s == 1800


def test_explicit_timeout_overrides_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_CLAUDE_TIMEOUT_S", "1800")
    runner = _FakeRunner(stdout=json.dumps({"result": "ok"}))
    SubprocessClaudeCli(timeout_s=42, runner=runner).run("p", tmp_path)
    assert runner.timeout_s == 42


def test_default_timeout_when_env_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONDUCTOR_CLAUDE_TIMEOUT_S", raising=False)
    runner = _FakeRunner(stdout=json.dumps({"result": "ok"}))
    SubprocessClaudeCli(runner=runner).run("p", tmp_path)
    assert runner.timeout_s == 300
