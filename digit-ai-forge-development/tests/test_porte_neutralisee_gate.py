"""Gate porte neutralisée (TF-1040) : un contrôle qualifié de porte n'en est plus une si son
code de sortie est neutralisé dans la chaîne CI."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.gates.porte_neutralisee_gate import (
    main,
    relever_controles_neutralises,
    run_porte_neutralisee_gate,
)


def _ecrire_workflow(tmp_path: Path, contenu: str, nom: str = "ci.yml") -> Path:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    fichier = workflows / nom
    fichier.write_text(contenu, encoding="utf-8")
    return fichier


# --- Fixture ROUGE (mesure fondatrice, Produit-11 RT-59) ----------------------


def test_controle_neutralise_par_ou_true_est_un_ECHEC(tmp_path: Path) -> None:
    """`|| true` sur une commande de lint : le contrôle ne peut plus faire échouer la chaîne."""
    _ecrire_workflow(tmp_path, "jobs:\n  code:\n    steps:\n"
                      "      - name: Ruff (lint)\n        run: uv run ruff check . || true\n")
    verdict = run_porte_neutralisee_gate(tmp_path)
    assert verdict.passed is False
    assert verdict.findings[0]["ligne"] == "5"
    assert "ruff check" in verdict.findings[0]["issue"]


def test_controle_neutralise_par_continue_on_error_est_un_ECHEC(tmp_path: Path) -> None:
    """Neutralisation déclarative (GitHub Actions/Azure Pipelines) : même défaut, autre syntaxe."""
    _ecrire_workflow(tmp_path, "jobs:\n  code:\n    steps:\n"
                      "      - name: Pytest\n        continue-on-error: true\n"
                      "        run: uv run pytest\n")
    verdict = run_porte_neutralisee_gate(tmp_path)
    assert verdict.passed is False
    assert any("continue-on-error" in f["issue"] for f in verdict.findings)


def test_six_controles_verts_par_construction_sont_tous_NOMMES(tmp_path: Path) -> None:
    """Mesure fondatrice (RT-59) : plusieurs contrôles neutralisés dans le même fichier sont
    TOUS relevés, pas seulement le premier — un total anonyme ne dirait pas COMBIEN sont morts."""
    _ecrire_workflow(tmp_path, "jobs:\n  code:\n    steps:\n"
                      "      - name: Lint\n        run: eslint . || true\n"
                      "      - name: Test\n        run: npm test || exit 0\n"
                      "      - name: Check types\n        continue-on-error: true\n"
                      "        run: tsc --noEmit\n")
    verdict = run_porte_neutralisee_gate(tmp_path)
    assert verdict.passed is False
    assert len(verdict.findings) == 3


# --- Fixture VERTE -------------------------------------------------------------


def test_controle_qui_bloque_reellement_passe(tmp_path: Path) -> None:
    """Même commande, sans neutralisation : la porte peut dire non, le gate est vert."""
    _ecrire_workflow(tmp_path, "jobs:\n  code:\n    steps:\n"
                      "      - name: Ruff (lint)\n        run: uv run ruff check .\n")
    assert run_porte_neutralisee_gate(tmp_path).passed is True


def test_neutralisation_hors_controle_ne_declenche_rien(tmp_path: Path) -> None:
    """`|| true` sur une commande qui n'a rien d'un contrôle (ex. nettoyage best-effort) n'est
    pas une porte neutralisée : l'accusation resterait fausse."""
    _ecrire_workflow(tmp_path, "jobs:\n  clean:\n    steps:\n"
                      "      - name: Nettoyage cache\n        run: rm -rf .cache || true\n")
    assert run_porte_neutralisee_gate(tmp_path).passed is True


def test_sans_fichier_de_chaine_est_SKIP_trace(tmp_path: Path) -> None:
    """P-06 : aucun .github/workflows → SKIP, jamais un FAIL implicite."""
    verdict = run_porte_neutralisee_gate(tmp_path)
    assert verdict.passed is True
    assert verdict.findings == [
        {"skipped": "aucun fichier de chaîne CI (.github/workflows/*.yml)"}
    ]


def test_racine_absente_est_SKIP_trace(tmp_path: Path) -> None:
    verdict = run_porte_neutralisee_gate(tmp_path / "absent")
    assert verdict.passed is True
    assert "skipped" in verdict.findings[0]


# --- relever_controles_neutralises (fonction pure) -----------------------------


def test_relever_lit_plusieurs_fichiers_de_chaine(tmp_path: Path) -> None:
    _ecrire_workflow(tmp_path, "jobs:\n  a:\n    steps:\n"
                      "      - name: Lint\n        run: ruff check . || true\n", nom="a.yml")
    _ecrire_workflow(tmp_path, "jobs:\n  b:\n    steps:\n"
                      "      - name: Test\n        run: pytest || true\n", nom="b.yml")
    findings = relever_controles_neutralises(tmp_path)
    assert {f["file"] for f in findings} == {
        str(tmp_path / ".github" / "workflows" / "a.yml"),
        str(tmp_path / ".github" / "workflows" / "b.yml"),
    }


# --- CLI ------------------------------------------------------------------------


def test_cli_pass_et_fail(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(tmp_path)]) == 0
    assert "PASS" in capsys.readouterr().out

    _ecrire_workflow(tmp_path, "jobs:\n  code:\n    steps:\n"
                      "      - name: Lint\n        run: ruff check . || true\n")
    assert main([str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "FAIL" in err
    assert ":5]" in err


def test_cli_nombre_arguments_invalide(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    assert "usage" in capsys.readouterr().err
