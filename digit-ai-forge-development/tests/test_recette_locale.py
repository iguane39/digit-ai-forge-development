"""Recette locale (TF-1101) : toutes les étapes jouent, même après un échec, et le
récapitulatif nomme chaque étape rouge — jamais un arrêt au premier symptôme."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from conductor.recette_locale import ETAPES, Etape, main, recapituler, rejouer


def _resultat(code: int, sortie: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=sortie, stderr="")


_ETAPES_TEST = (
    Etape("un", ("true",), Path(".")),
    Etape("deux", ("true",), Path(".")),
    Etape("trois", ("true",), Path(".")),
)


# --- Fixture ROUGE : une étape échoue, les suivantes jouent quand même --------------


def test_une_etape_en_echec_n_arrete_pas_les_suivantes() -> None:
    """TF-1101 : le défaut exact corrigé — la première étape rouge stoppait tout avant elle."""
    appels: list[str] = []

    def executeur(etape: Etape) -> subprocess.CompletedProcess[str]:
        appels.append(etape.nom)
        return _resultat(1 if etape.nom == "un" else 0)

    resultats = rejouer(_ETAPES_TEST, executeur=executeur)
    assert appels == ["un", "deux", "trois"], "les trois etapes doivent TOUTES avoir tourne"
    assert [r["code"] for r in resultats] == ["1", "0", "0"]


def test_plusieurs_echecs_sont_TOUS_nommes_au_recapitulatif() -> None:
    def executeur(etape: Etape) -> subprocess.CompletedProcess[str]:
        return _resultat(1 if etape.nom in ("un", "trois") else 0)

    resultats = rejouer(_ETAPES_TEST, executeur=executeur)
    recap = recapituler(resultats)
    assert "un" in recap and "trois" in recap
    assert "deux" not in recap.split("echec(s) :")[1].split("\n")[0]
    assert "3 etape(s)" in recap or "1/3" in recap  # 1 verte sur 3


def test_recapitulatif_liste_chaque_etape_avec_son_verdict() -> None:
    def executeur(etape: Etape) -> subprocess.CompletedProcess[str]:
        return _resultat(1 if etape.nom == "deux" else 0)

    recap = recapituler(rejouer(_ETAPES_TEST, executeur=executeur))
    lignes = recap.splitlines()
    assert any("OK" in ligne and "un" in ligne for ligne in lignes)
    assert any("ECHEC" in ligne and "deux" in ligne for ligne in lignes)
    assert any("OK" in ligne and "trois" in ligne for ligne in lignes)


# --- Fixture VERTE : tout passe -----------------------------------------------------


def test_toutes_les_etapes_vertes_donnent_un_recapitulatif_sans_echec() -> None:
    resultats = rejouer(_ETAPES_TEST, executeur=lambda e: _resultat(0))
    recap = recapituler(resultats)
    assert "echec" not in recap.lower()
    assert "3/3" in recap


# --- ETAPES (contrat avec double-gate.yml, TF-1072) ---------------------------------


def test_etapes_reprend_exactement_les_commandes_du_job_code() -> None:
    """Même ordre, mêmes commandes que le job `code` de double-gate.yml — une divergence ferait
    mentir la recette locale sur ce qu'elle prétend rejouer (contrat écrit dans TF-1072)."""
    noms = [e.nom for e in ETAPES]
    assert noms == ["ruff", "mypy", "pytest", "ai-antipatterns", "porte-neutralisee"]
    assert ETAPES[0].commande == ("uv", "run", "ruff", "check", ".")
    assert ETAPES[1].commande == ("uv", "run", "mypy")


# --- main() / CLI --------------------------------------------------------------------


def test_main_exit_0_si_tout_est_vert(monkeypatch: pytest.MonkeyPatch) -> None:
    import conductor.recette_locale as module

    monkeypatch.setattr(module, "rejouer", lambda: [{"nom": "x", "code": "0", "sortie": ""}])
    assert main([]) == 0


def test_main_exit_1_et_toutes_les_etapes_recapitulees_si_une_echoue(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Preuve rouge/verte bout en bout de TF-1101 : deux étapes, la première rouge — la
    seconde apparaît quand même au récapitulatif (elle a bien tourné), et l'exit code
    global reste 1 (le push doit rester bloqué)."""
    import conductor.recette_locale as module

    monkeypatch.setattr(
        module, "rejouer",
        lambda: [
            {"nom": "ruff", "code": "1", "sortie": "E501 ligne trop longue"},
            {"nom": "mypy", "code": "0", "sortie": ""},
        ],
    )
    assert main([]) == 1
    out = capsys.readouterr().out
    assert "ruff" in out and "mypy" in out, "les DEUX etapes doivent apparaitre au recapitulatif"


def test_main_refuse_un_argument(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--quelque-chose"]) == 2
    assert "usage" in capsys.readouterr().err
