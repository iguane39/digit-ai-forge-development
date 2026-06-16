"""Vérifie le gate code : passed = (exit 0 du harness délégué), via runner factice."""

from __future__ import annotations

from pathlib import Path

from conductor.gates.code_gate import run_code_gate


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
