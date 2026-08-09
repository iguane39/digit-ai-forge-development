"""Gate affordances (loi 1, TF-0010) : DÉLÈGUE au pan `interface` de forge-tests — ce test
verrouille que le gate lit fidèlement son rapport réel, sans le réimplémenter (aucune logique
de câblage HTML ici, seulement la traduction JSON → GateVerdict)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from conductor.gates.affordances_gate import main, run_affordances_gate


class _FakeRunner:
    def __init__(self, report: dict[str, Any]) -> None:
        self.report = report
        self.seen: list[tuple[Path, Path]] = []

    def run_interface_pan(self, forge_tests_path: Path, repo_path: Path) -> dict[str, Any]:
        self.seen.append((forge_tests_path, repo_path))
        return self.report


# Rapport réel observé (forme) via `python -m forge_tests <fixture> --pans interface --json`.
_REPORT_VERT = {
    "couverture_par_pan": {
        "interface": {
            "inventorie": 2,
            "exerce": 2,
            "ratio": 1.0,
            "seuil": 1.0,
            "elements_exerces": ["interface:index.html:8:a", "interface:index.html:10:button"],
            "elements_non_exerces": [],
        }
    }
}

_REPORT_ROUGE = {
    "couverture_par_pan": {
        "interface": {
            "inventorie": 2,
            "exerce": 1,
            "ratio": 0.5,
            "seuil": 1.0,
            "elements_exerces": ["interface:index.html:8:a"],
            "elements_non_exerces": ["interface:index.html:10:button"],
        }
    }
}


def test_ratio_1_passe(tmp_path: Path) -> None:
    """Fixture verte : ratio de couverture interface = 1.0 → PASS, findings vides."""
    forge_tests = tmp_path / "forge-tests"
    forge_tests.mkdir()
    runner = _FakeRunner(_REPORT_VERT)
    verdict = run_affordances_gate(forge_tests, tmp_path / "repo", runner=runner)
    assert verdict.passed is True
    assert verdict.findings == []
    assert runner.seen == [(forge_tests, tmp_path / "repo")]


def test_affordance_inerte_echoue(tmp_path: Path) -> None:
    """Fixture rouge : un élément dans `elements_non_exerces` fait échouer le gate, et est nommé."""
    forge_tests = tmp_path / "forge-tests"
    forge_tests.mkdir()
    runner = _FakeRunner(_REPORT_ROUGE)
    verdict = run_affordances_gate(forge_tests, tmp_path / "repo", runner=runner)
    assert verdict.passed is False
    assert verdict.findings == [{"element": "interface:index.html:10:button"}]


def test_forge_tests_introuvable_est_skip_trace(tmp_path: Path) -> None:
    """P-06 : forge-tests (dépôt frère) introuvable → skip tracé, jamais un échec implicite."""
    verdict = run_affordances_gate(tmp_path / "absent", tmp_path / "repo")
    assert verdict.passed is True
    assert "skipped" in verdict.findings[0]


def test_pan_absent_du_rapport_est_skip_trace(tmp_path: Path) -> None:
    """Do-no-harm : le pan interface n'a pas tourné (absent du rapport) → skip, pas d'échec."""
    forge_tests = tmp_path / "forge-tests"
    forge_tests.mkdir()
    verdict = run_affordances_gate(
        forge_tests, tmp_path / "repo", runner=_FakeRunner({"couverture_par_pan": {}})
    )
    assert verdict.passed is True
    assert "skipped" in verdict.findings[0]


def test_cli_main_pass_et_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import conductor.gates.affordances_gate as mod

    forge_tests = tmp_path / "forge-tests"
    forge_tests.mkdir()

    monkeypatch.setattr(mod, "SubprocessInterfacePanRunner", lambda: _FakeRunner(_REPORT_ROUGE))
    assert main([str(forge_tests), str(tmp_path / "repo")]) == 1

    monkeypatch.setattr(mod, "SubprocessInterfacePanRunner", lambda: _FakeRunner(_REPORT_VERT))
    assert main([str(forge_tests), str(tmp_path / "repo")]) == 0
