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
        'def test_facture_sans_client_E_001():\n    """E-002 — aussi couverte ici."""\n',
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
        "def test_facture_sans_client_E_001():\n    pass\n", encoding="utf-8"
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
        "def test_facture_sans_client_E_001():\n    pass\n", encoding="utf-8"
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


# --- Lot Produit-83 du 15/10/2026 (TF-1779, TF-1780) ---------------------------------------------
# Le référentiel réel de forge-conception est un OBJET ; un nom de test ne peut pas porter le tiret
# d'un identifiant (SyntaxError) ; un produit full-stack range ses tests dans plusieurs dossiers.


def test_tf1779_referentiel_objet_de_forge_conception_lu(tmp_path: Path) -> None:
    """Forme réelle d'EXIGENCES.json : {projet, …, exigences: [...]} ; la V1 reste hors gate."""
    exigences = tmp_path / "EXIGENCES.json"
    exigences.write_text(
        json.dumps(
            {
                "projet": "Produit-NN",
                "exigences": [
                    {"id": "E-001", "palier": "MVP"},
                    {"id": "E-002", "palier": "MVP"},
                    {"id": "E-090", "palier": "V1"},
                ],
            }
        ),
        encoding="utf-8",
    )
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_a.py").write_text('"""E-001"""\n', encoding="utf-8")

    verdict = run_traceability_gate(exigences, tests_dir)

    assert verdict.passed is False
    assert verdict.findings == [{"id": "E-002", "issue": "jamais citée par un test"}]


def test_tf1780_un_nom_de_test_valide_cite_l_exigence_par_un_souligne(tmp_path: Path) -> None:
    """`test_facture_sans_client_E_042` est un identifiant Python ; il cite E-042."""
    exigences = _write_exigences(tmp_path, [{"id": "E-042", "palier": "MVP"}])
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    source = "def test_facture_sans_client_E_042() -> None:\n    pass\n"
    compile(source, "test_facture.py", "exec")  # le nom prescrit se compile
    (tests_dir / "test_facture.py").write_text(source, encoding="utf-8")

    assert run_traceability_gate(exigences, tests_dir).passed is True


def test_tf1779_plusieurs_dossiers_et_tests_d_interface(tmp_path: Path) -> None:
    """Les tests d'un produit full-stack vivent dans backend/tests, e2e et frontend/src.

    Seuls les fichiers de TEST du frontend comptent : un composant qui cite E-003 dans un
    commentaire ne la teste pas."""
    exigences = _write_exigences(
        tmp_path,
        [
            {"id": "E-001", "palier": "MVP"},
            {"id": "E-002", "palier": "MVP"},
            {"id": "E-003", "palier": "MVP"},
        ],
    )
    back = tmp_path / "backend" / "tests"
    back.mkdir(parents=True)
    (back / "test_api.py").write_text('"""E-001"""\n', encoding="utf-8")
    front = tmp_path / "frontend" / "src"
    front.mkdir(parents=True)
    (front / "Carte.test.tsx").write_text("it('E-002 affiche la carte', () => {})\n", "utf-8")
    (front / "Liste.tsx").write_text("// E-003 : la liste\n", encoding="utf-8")

    verdict = run_traceability_gate(exigences, back, front)

    assert verdict.passed is False
    assert verdict.findings == [{"id": "E-003", "issue": "jamais citée par un test"}]
    assert main([str(exigences), str(back), str(front)]) == 1
