"""Gate de traçabilité des exigences (RV-1, TF-0010) : oracle exécutable de la doctrine."""

from __future__ import annotations

import json
from pathlib import Path

from conductor.gates.traceability_gate import main, run_traceability_gate


def _write_exigences(tmp_path: Path, items: list[dict[str, object]]) -> Path:
    path = tmp_path / "EXIGENCES.json"
    path.write_text(json.dumps(items), encoding="utf-8")
    return path


def test_toutes_les_exigences_mvp_citees_passe(tmp_path: Path) -> None:
    """Fixture verte : chaque exigence MVP est citée par au moins un test → PASS."""
    exigences = _write_exigences(
        tmp_path, [{"id": "E-001", "palier": "MVP"}, {"id": "E-002", "palier": "MVP"}]
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_facture.py").write_text(
        'def test_facture_sans_client_E-001():\n    """E-002 — aussi couverte ici."""\n',
        encoding="utf-8",
    )
    verdict = run_traceability_gate(exigences, tests_dir)
    assert verdict.passed is True
    assert verdict.findings == []


def test_exigence_mvp_non_citee_echoue(tmp_path: Path) -> None:
    """Fixture rouge : une exigence MVP jamais citée par un test fait échouer le gate."""
    exigences = _write_exigences(
        tmp_path, [{"id": "E-001", "palier": "MVP"}, {"id": "E-003", "palier": "MVP"}]
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_facture.py").write_text(
        "def test_facture_sans_client_E-001():\n    pass\n", encoding="utf-8"
    )
    verdict = run_traceability_gate(exigences, tests_dir)
    assert verdict.passed is False
    assert verdict.findings == [{"id": "E-003", "issue": "jamais citée par un test"}]


def test_exigences_v1_hors_perimetre_du_grep_mvp(tmp_path: Path) -> None:
    """Une exigence de palier V1 (pas MVP) non citée ne fait PAS échouer le gate."""
    exigences = _write_exigences(
        tmp_path, [{"id": "E-001", "palier": "MVP"}, {"id": "E-099", "palier": "V1"}]
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_facture.py").write_text(
        "def test_facture_sans_client_E-001():\n    pass\n", encoding="utf-8"
    )
    assert run_traceability_gate(exigences, tests_dir).passed is True


def test_referentiel_absent_est_skip_trace(tmp_path: Path) -> None:
    """P-06 : pas de EXIGENCES.json exploitable → skip tracé, jamais un échec implicite."""
    verdict = run_traceability_gate(tmp_path / "absent.json", tmp_path / "tests")
    assert verdict.passed is True
    assert "skipped" in verdict.findings[0]


def test_cli_main_pass_et_fail(tmp_path: Path) -> None:
    exigences = _write_exigences(tmp_path, [{"id": "E-001", "palier": "MVP"}])
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    assert main([str(exigences), str(tests_dir)]) == 1  # E-001 non citée
    (tests_dir / "test_x.py").write_text("# E-001\n", encoding="utf-8")
    assert main([str(exigences), str(tests_dir)]) == 0
