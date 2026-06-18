"""SubprocessClaudeCli : invoque `claude -p … --output-format json`, renvoie `result`."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from conductor.harness.claude_cli import SubprocessClaudeCli


def _completed(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["claude"], returncode=returncode, stdout=stdout, stderr=""
    )


def test_returns_result_field(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "conductor.harness.claude_cli.subprocess.run",
        lambda *a, **k: _completed(json.dumps({"result": "analyse OK"})),
    )
    assert SubprocessClaudeCli().run("prompt", tmp_path) == "analyse OK"


def test_nonzero_exit_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "conductor.harness.claude_cli.subprocess.run", lambda *a, **k: _completed("", returncode=1)
    )
    with pytest.raises(RuntimeError, match="claude"):
        SubprocessClaudeCli().run("p", tmp_path)


def test_invalid_json_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "conductor.harness.claude_cli.subprocess.run", lambda *a, **k: _completed("pas du json")
    )
    with pytest.raises(RuntimeError, match="illisible|JSON"):
        SubprocessClaudeCli().run("p", tmp_path)


def test_missing_result_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "conductor.harness.claude_cli.subprocess.run",
        lambda *a, **k: _completed(json.dumps({"other": 1})),
    )
    with pytest.raises(RuntimeError, match="result"):
        SubprocessClaudeCli().run("p", tmp_path)


def test_timeout_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _boom(*a: object, **k: object) -> object:
        raise subprocess.TimeoutExpired(cmd="claude", timeout=1)

    monkeypatch.setattr("conductor.harness.claude_cli.subprocess.run", _boom)
    with pytest.raises(RuntimeError, match="timeout"):
        SubprocessClaudeCli(timeout_s=1).run("p", tmp_path)


def test_skip_permissions_adds_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, list[str]] = {}

    def _run(cmd: list[str], **k: object) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        return _completed(json.dumps({"result": "ok"}))

    monkeypatch.setattr("conductor.harness.claude_cli.subprocess.run", _run)
    SubprocessClaudeCli(skip_permissions=True).run("p", tmp_path)
    assert "--dangerously-skip-permissions" in captured["cmd"]


def test_default_has_no_skip_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, list[str]] = {}

    def _run(cmd: list[str], **k: object) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        return _completed(json.dumps({"result": "ok"}))

    monkeypatch.setattr("conductor.harness.claude_cli.subprocess.run", _run)
    SubprocessClaudeCli().run("p", tmp_path)
    assert "--dangerously-skip-permissions" not in captured["cmd"]
