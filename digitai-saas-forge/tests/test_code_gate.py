"""Vérifie le gate code : passed = (exit 0 du harness délégué), via runner factice."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from conductor.gates.code_gate import run_code_gate
from conductor.profiles import FASTAPI_SAAS, TargetProfile


class FakeRunner:
    def __init__(self, rc: int) -> None:
        self.rc = rc
        self.calls: list[tuple[str, Path]] = []

    def run(self, command: str, cwd: Path) -> int:
        self.calls.append((command, cwd))
        return self.rc


def test_code_gate_passes_on_zero(tmp_path: Path) -> None:
    verdict = run_code_gate(tmp_path, runner=FakeRunner(0))
    assert verdict.gate == "code"
    assert verdict.passed is True
    assert verdict.findings == []


def test_code_gate_fails_on_nonzero(tmp_path: Path) -> None:
    verdict = run_code_gate(tmp_path, runner=FakeRunner(1))
    assert verdict.passed is False
    assert verdict.findings  # remonte la commande + le code de sortie


def test_code_gate_delegates_default_harness(tmp_path: Path) -> None:
    runner = FakeRunner(0)
    run_code_gate(tmp_path, runner=runner)
    assert runner.calls[0][0] == "uv run pytest"  # délégué, pas réimplémenté


def test_code_gate_uses_profile_code_check(tmp_path: Path) -> None:
    runner = FakeRunner(0)
    profile = TargetProfile(name="node-ts", code_check="npm test", has_ui=True)
    run_code_gate(tmp_path, profile=profile, runner=runner)
    assert runner.calls[0][0] == "npm test"  # commande issue du profil


def test_code_gate_profile_fastapi_runs_pytest(tmp_path: Path) -> None:
    runner = FakeRunner(0)
    run_code_gate(tmp_path, profile=FASTAPI_SAAS, runner=runner)
    assert runner.calls[0][0] == "uv run pytest"


def test_subprocess_runner_splits_command_no_shell(tmp_path: Path) -> None:
    """P-08 : le runner de prod découpe en list[str] et passe par le ProcessRunner (shell=False)."""
    from conductor.gates.code_gate import SubprocessRunner
    from conductor.process import ProcessResult

    seen: dict[str, object] = {}

    class _FakeProc:
        def run(
            self, args: Sequence[str], *, cwd: Path | None = None, timeout_s: int = 300
        ) -> ProcessResult:
            seen["args"] = list(args)
            seen["cwd"] = cwd
            return ProcessResult(0, "", "")

    rc = SubprocessRunner(runner=_FakeProc()).run("uv run pytest", tmp_path)
    assert rc == 0
    assert seen["args"] == ["uv", "run", "pytest"]  # list[str], pas de chaîne shell
    assert seen["cwd"] == tmp_path
