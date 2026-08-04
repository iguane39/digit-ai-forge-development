"""ProcessRunner cross-platform (P-07) : which + list[str] + shell=False + ToolNotFound."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.process import SubprocessProcessRunner, ToolNotFound


def test_tool_not_found_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("conductor.process.shutil.which", lambda _n: None)
    with pytest.raises(ToolNotFound, match="introuvable"):
        SubprocessProcessRunner().run(["npx", "--version"])


def test_empty_args_raises() -> None:
    with pytest.raises(ValueError, match="vide"):
        SubprocessProcessRunner().run([])


def test_resolves_binary_and_never_uses_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}
    monkeypatch.setattr("conductor.process.shutil.which", lambda n: "/resolved/" + n)

    class _Proc:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(args: object, **kw: object) -> _Proc:
        seen["args"] = args
        seen["shell_absent"] = "shell" not in kw
        return _Proc()

    monkeypatch.setattr("conductor.process.subprocess.run", fake_run)
    res = SubprocessProcessRunner().run(["npx", "lint"], cwd=Path("/x"))
    assert res.returncode == 0 and res.stdout == "ok"
    assert seen["args"] == ["/resolved/npx", "lint"]  # binaire résolu, list conservée
    assert seen["shell_absent"] is True  # jamais shell=True
