"""Gate mutation (TF-0103.2) : politique de seuil sur les stats CI/CD exportées par mutmut.

Ces tests exercent la POLITIQUE (lecture de `mutants/mutmut-cicd-stats.json` + seuil), pas
mutmut lui-même (indisponible nativement sous Windows) — même découplage que
`test_design_gate.py` qui fabrique un `findings.json` de synthèse sans relancer le linter.
"""

from __future__ import annotations

import json
from pathlib import Path

from conductor.gates.mutation_gate import DEFAULT_THRESHOLD, main, run_mutation_gate


def _write_stats(tmp_path: Path, *, killed: int, survived: int, **extra: int) -> Path:
    p = tmp_path / "mutmut-cicd-stats.json"
    data = {
        "killed": killed,
        "survived": survived,
        "total": killed + survived + sum(extra.values()),
        "no_tests": 0,
        "skipped": 0,
        "suspicious": 0,
        "timeout": 0,
        "check_was_interrupted_by_user": 0,
        "segfault": 0,
    }
    data.update(extra)
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_score_au_dessus_du_seuil_passe(tmp_path: Path) -> None:
    """Fixture verte : 80 % tués ≥ seuil 75 % par défaut."""
    stats = _write_stats(tmp_path, killed=80, survived=20)
    verdict = run_mutation_gate(stats)
    assert verdict.passed is True
    assert verdict.findings == []


def test_score_sous_le_seuil_echoue(tmp_path: Path) -> None:
    """Fixture rouge : 60 % tués < seuil 75 % → échec avec le détail chiffré."""
    stats = _write_stats(tmp_path, killed=60, survived=40)
    verdict = run_mutation_gate(stats)
    assert verdict.passed is False
    assert verdict.findings[0]["score"] == "60.0%"
    assert verdict.findings[0]["seuil"] == "75.0%"


def test_seuil_personnalise(tmp_path: Path) -> None:
    stats = _write_stats(tmp_path, killed=60, survived=40)
    assert run_mutation_gate(stats, threshold=0.5).passed is True
    assert run_mutation_gate(stats, threshold=0.9).passed is False


def test_stats_absentes_est_skip_trace(tmp_path: Path) -> None:
    """P-06 : mutmut pas encore lancé (cas normal sous Windows natif) → skip, pas un échec."""
    verdict = run_mutation_gate(tmp_path / "absent.json")
    assert verdict.passed is True
    assert "skipped" in verdict.findings[0]


def test_stats_illisibles_est_skip_trace(tmp_path: Path) -> None:
    p = tmp_path / "corrompu.json"
    p.write_text("{ceci n'est pas du json", encoding="utf-8")
    verdict = run_mutation_gate(p)
    assert verdict.passed is True
    assert "skipped" in verdict.findings[0]


def test_aucun_mutant_juge_est_skip_trace(tmp_path: Path) -> None:
    """killed=survived=0 (tout en no_tests/skipped) : rien à juger, pas un échec implicite."""
    stats = _write_stats(tmp_path, killed=0, survived=0, no_tests=5)
    verdict = run_mutation_gate(stats)
    assert verdict.passed is True
    assert "skipped" in verdict.findings[0]


def test_seuil_par_defaut_est_documente() -> None:
    assert DEFAULT_THRESHOLD == 0.75


def test_cli_main_pass_et_fail(tmp_path: Path) -> None:
    ok = _write_stats(tmp_path, killed=80, survived=20)
    assert main([str(ok)]) == 0
    ko = _write_stats(tmp_path, killed=10, survived=90)
    assert main([str(ko)]) == 1
