"""Entrée CLI du shim : émet stdout/stderr avec newline final et propage le code de sortie."""

from __future__ import annotations

import pytest

from conductor.harness.gh_shim import __main__ as shim_main
from conductor.harness.gh_shim.translate import ShimResult


def test_main_writes_stdout_and_returns_code(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(shim_main, "SubprocessAzBackend", lambda cwd: object())
    monkeypatch.setattr(
        shim_main, "translate", lambda args, backend: ShimResult(stdout="hello", returncode=8)
    )
    code = shim_main.main(["pr", "checks", "1"])
    assert code == 8
    out = capsys.readouterr().out
    assert out == "hello\n"  # newline final ajouté


def test_main_does_not_double_newline(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(shim_main, "SubprocessAzBackend", lambda cwd: object())
    monkeypatch.setattr(
        shim_main, "translate", lambda args, backend: ShimResult(stdout="x\n")
    )
    shim_main.main(["pr", "list"])
    assert capsys.readouterr().out == "x\n"
