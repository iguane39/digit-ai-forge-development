"""Gate « erreurs de formulaire » (TF-2172) : une saisie refusée se dit sous son champ.

Le cas d'origine (Produit-86, 05/11/2026) : « Refusé : CIBLE_INVALIDE » en bandeau en tête de page,
sans champ désigné, sans forme attendue, seulement à l'envoi. Aucune porte de cette forge ne le
voyait : le gate joue donc `oracle-erreurs-formulaire` (forge-design) sur l'instance servie.

Deux étages de recette :

- la logique du gate, jouée avec un juge factice (aucun navigateur) : verdict, remède nommé,
  SKIP dit au lieu d'un PASS muet ;
- le sens ROUGE puis VERT sur le vrai oracle et une vraie instance servie en local : le même
  formulaire refusé quand son erreur est un bandeau, accepté quand il est bâti avec le composant
  `corpus/composants/saisie-erreurs.js` de forge-design (le remède que le message propose).
  Ces cas sautent, en le disant, si forge-design, Node ou Playwright manquent.
"""

from __future__ import annotations

import functools
import importlib
import importlib.util
import os
import re
import shutil
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

from conductor.gates.formulaire_erreurs_gate import (
    OracleIllisible,
    _path_sans_venv,
    formulaires_de_l_application,
    main,
    run_formulaire_erreurs_gate,
)
from conductor.process import ToolNotFound

_FORMULAIRE = '<form action="/clients" method="post"><input name="domaine" required></form>\n'

_RAPPORT_ROUGE: dict[str, Any] = {
    "oracle": "oracle-erreurs-formulaire",
    "verdict": "FAIL",
    "champs_eprouves": 2,
    "findings": [
        {
            "sev": "bloquant",
            "regle": "EF1",
            "msg": "champ « Domaine du client », valeur fausse « costcontrol » : le champ n'est "
            "pas désigné. Le refus s'affiche ailleurs : « Refusé : CIBLE_INVALIDE », à 595 px.",
            "where": "http://127.0.0.1:8000/clients.html",
        },
        {
            "sev": "majeur",
            "regle": "EF3",
            "msg": "champ « Courriel » : le message « Invalide » ne donne pas la forme attendue",
            "where": "http://127.0.0.1:8000/clients.html",
        },
        {
            "sev": "avertissement",
            "regle": "EF5",
            "msg": "champ « Courriel » : le message n'apparaît qu'à l'envoi",
            "where": "http://127.0.0.1:8000/clients.html",
        },
    ],
    "non_juge": ["a générique", "b générique"],
}

_RAPPORT_VERT: dict[str, Any] = {
    "oracle": "oracle-erreurs-formulaire",
    "verdict": "PASS",
    "champs_eprouves": 2,
    "findings": [{"sev": "info", "regle": "—", "msg": "EF0–EF5 sans écart", "where": "x"}],
    "non_juge": [],
}


class _FauxJuge:
    """Runner factice : rend un rapport (ou lève) et note ce qu'on lui a demandé."""

    def __init__(self, reponse: dict[str, Any] | Exception) -> None:
        self._reponse = reponse
        self.appels: list[tuple[Path, tuple[str, ...], tuple[str, ...]]] = []

    def run_oracle(
        self, oracle_path: Path, instances: Sequence[str], options: Sequence[str]
    ) -> dict[str, Any]:
        self.appels.append((oracle_path, tuple(instances), tuple(options)))
        if isinstance(self._reponse, Exception):
            raise self._reponse
        return self._reponse


def _application(tmp_path: Path, *, contenu: str = _FORMULAIRE) -> Path:
    racine = tmp_path / "application"
    (racine / "templates").mkdir(parents=True)
    (racine / "templates" / "clients.html").write_text(contenu, encoding="utf-8")
    return racine


def _forge_design_factice(tmp_path: Path) -> Path:
    dossier = tmp_path / "forge-design"
    (dossier / "oracles").mkdir(parents=True)
    (dossier / "oracles" / "oracle-erreurs-formulaire.mjs").write_text("// factice\n", "utf-8")
    return dossier


# --- Détection : l'application porte-t-elle un formulaire ? -------------------


def test_un_formulaire_html_est_detecte(tmp_path: Path) -> None:
    racine = _application(tmp_path)
    assert [p.name for p in formulaires_de_l_application(racine)] == ["clients.html"]


@pytest.mark.parametrize(
    ("nom", "contenu"),
    [
        ("Clients.tsx", "export const C = () => <form onSubmit={envoyer}></form>;\n"),
        ("Clients.tsx", "export const C = () => <Form method='post'></Form>;\n"),
        ("clients.jinja", "<FORM action='/x'></FORM>\n"),
        ("Clients.vue", "<template><form @submit.prevent='envoyer'></form></template>\n"),
    ],
)
def test_formulaires_de_gabarits_et_de_composants(tmp_path: Path, nom: str, contenu: str) -> None:
    racine = _application(tmp_path, contenu="<p>rien</p>\n")
    (racine / "src").mkdir()
    (racine / "src" / nom).write_text(contenu, encoding="utf-8")
    assert [p.name for p in formulaires_de_l_application(racine)] == [nom]


def test_fixture_de_test_et_dependances_ne_sont_pas_l_application(tmp_path: Path) -> None:
    racine = _application(tmp_path, contenu="<p>rien</p>\n")
    for dossier in ("tests", "node_modules/paquet", ".venv/lib"):
        (racine / dossier).mkdir(parents=True)
        (racine / dossier / "page.html").write_text(_FORMULAIRE, encoding="utf-8")
    assert formulaires_de_l_application(racine) == []


# --- Le verdict : refus nommé avec son remède, accord sur un oracle vert ------


def test_rouge_un_formulaire_au_bandeau_est_refuse_avec_regle_et_remede(tmp_path: Path) -> None:
    juge = _FauxJuge(_RAPPORT_ROUGE)
    verdict = run_formulaire_erreurs_gate(
        _application(tmp_path),
        ["http://127.0.0.1:8000/clients.html"],
        _forge_design_factice(tmp_path),
        runner=juge,
    )
    assert verdict.passed is False
    assert verdict.gate == "formulaire-erreurs"
    durs = [f for f in verdict.findings if f.get("gravite") in ("bloquant", "majeur")]
    assert [f["regle"] for f in durs] == ["EF1", "EF3"]
    assert "CIBLE_INVALIDE" in durs[0]["issue"], "le texte du bandeau est cité"
    assert "aria-invalid" in durs[0]["remede"], "le remède de EF1 est nommé"
    assert "saisie-erreurs" in durs[0]["remede"], "le composant de référence est cité"
    assert "forme attendue" in durs[1]["remede"], "le remède de EF3 est nommé"


def test_vert_un_formulaire_accepte_par_l_oracle_passe(tmp_path: Path) -> None:
    verdict = run_formulaire_erreurs_gate(
        _application(tmp_path),
        ["http://127.0.0.1:8000/clients.html"],
        _forge_design_factice(tmp_path),
        runner=_FauxJuge(_RAPPORT_VERT),
    )
    assert verdict.passed is True
    assert not [f for f in verdict.findings if "skipped" in f]
    assert verdict.findings[0]["champs_eprouves"] == "2"


def test_l_oracle_recoit_les_instances_et_les_options(tmp_path: Path) -> None:
    juge = _FauxJuge(_RAPPORT_VERT)
    forge_design = _forge_design_factice(tmp_path)
    run_formulaire_erreurs_gate(
        _application(tmp_path),
        ["https://localhost:8443/a", "https://localhost:8443/b"],
        forge_design,
        runner=juge,
        options=["--accepter-certificat-local"],
    )
    oracle, instances, options = juge.appels[0]
    assert oracle == forge_design / "oracles" / "oracle-erreurs-formulaire.mjs"
    assert instances == ("https://localhost:8443/a", "https://localhost:8443/b")
    assert options == ("--accepter-certificat-local",)


# --- Ce que la porte ne peut pas juger, elle le DIT (jamais un PASS muet) -----


def test_sans_formulaire_la_porte_le_dit(tmp_path: Path) -> None:
    juge = _FauxJuge(_RAPPORT_VERT)
    verdict = run_formulaire_erreurs_gate(
        _application(tmp_path, contenu="<p>aucun formulaire</p>\n"),
        ["http://127.0.0.1:8000/"],
        _forge_design_factice(tmp_path),
        runner=juge,
    )
    assert verdict.passed is True
    assert verdict.findings[0]["non_juge"] == "gate entier"
    assert "aucun formulaire" in verdict.findings[0]["skipped"]
    assert juge.appels == [], "rien à éprouver : l'oracle n'est pas lancé"


def test_sans_instance_servie_la_porte_le_dit(tmp_path: Path) -> None:
    juge = _FauxJuge(_RAPPORT_VERT)
    verdict = run_formulaire_erreurs_gate(
        _application(tmp_path), [], _forge_design_factice(tmp_path), runner=juge
    )
    assert verdict.passed is True
    assert verdict.findings[0]["non_juge"] == "gate entier"
    assert "instance" in verdict.findings[0]["skipped"]
    assert "clients.html" in verdict.findings[0]["skipped"], "le formulaire qui reste non jugé"
    assert juge.appels == []


def test_sans_forge_design_la_porte_le_dit(tmp_path: Path) -> None:
    racine = _application(tmp_path)
    for forge_design in (None, tmp_path / "absente", tmp_path):
        verdict = run_formulaire_erreurs_gate(
            racine, ["http://127.0.0.1:8000/"], forge_design, runner=_FauxJuge(_RAPPORT_VERT)
        )
        assert verdict.passed is True
        assert verdict.findings[0]["non_juge"] == "gate entier"
        assert "forge-design" in verdict.findings[0]["skipped"]


def test_application_absente_la_porte_le_dit(tmp_path: Path) -> None:
    verdict = run_formulaire_erreurs_gate(
        tmp_path / "absente",
        ["http://127.0.0.1:8000/"],
        _forge_design_factice(tmp_path),
        runner=_FauxJuge(_RAPPORT_VERT),
    )
    assert verdict.findings[0]["non_juge"] == "gate entier"


@pytest.mark.parametrize(
    "panne", [ToolNotFound("node"), OracleIllisible("sortie illisible"), RuntimeError("timeout")]
)
def test_oracle_en_panne_n_est_jamais_un_pass(tmp_path: Path, panne: Exception) -> None:
    verdict = run_formulaire_erreurs_gate(
        _application(tmp_path),
        ["http://127.0.0.1:8000/clients.html"],
        _forge_design_factice(tmp_path),
        runner=_FauxJuge(panne),
    )
    assert verdict.findings[0]["non_juge"] == "gate entier"
    assert "oracle" in verdict.findings[0]["skipped"]


def test_oracle_skip_est_rendu_comme_non_juge_avec_son_motif(tmp_path: Path) -> None:
    url = "http://127.0.0.1:8000/clients.html"
    rapport = {
        "verdict": "SKIP",
        "findings": [],
        "non_juge": [
            "générique",
            f"{url} : aucun champ éprouvable (aucun formulaire visible)",
            "aucun écran jugé avec un champ éprouvable",
        ],
    }
    verdict = run_formulaire_erreurs_gate(
        _application(tmp_path), [url], _forge_design_factice(tmp_path), runner=_FauxJuge(rapport)
    )
    assert verdict.passed is True
    assert verdict.findings[0]["non_juge"] == "gate entier"
    assert "aucun champ éprouvable" in verdict.findings[0]["skipped"]


# --- CLI -----------------------------------------------------------------------


def _cli(
    tmp_path: Path,
    juge: _FauxJuge,
    capsys: pytest.CaptureFixture[str],
    *,
    instances: Sequence[str] = ("http://x/clients.html",),
) -> tuple[int, str, str]:
    code = main(
        [str(_application(tmp_path)), str(_forge_design_factice(tmp_path)), *instances],
        runner=juge,
    )
    sortie = capsys.readouterr()
    return code, sortie.out, sortie.err


def test_cli_fail_nomme_la_regle_et_le_remede(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, sortie, erreur = _cli(tmp_path, _FauxJuge(_RAPPORT_ROUGE), capsys)
    assert code == 1
    assert "FAIL" in erreur
    assert "EF1" in erreur
    assert "aria-invalid" in erreur, "le remède est dit, pas seulement le constat"
    assert sortie == ""


def test_cli_pass_dit_les_champs_eprouves_et_la_limite_serveur(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, sortie, _ = _cli(tmp_path, _FauxJuge(_RAPPORT_VERT), capsys)
    assert code == 0
    assert sortie.startswith("formulaire-erreurs gate: PASS")
    assert "2 champ(s)" in sortie
    assert "refus du serveur" in sortie, "ce que le PASS ne couvre pas est dit à côté"


def test_cli_sans_instance_dit_skip_pas_pass(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, sortie, _ = _cli(tmp_path, _FauxJuge(_RAPPORT_VERT), capsys, instances=())
    assert code == 0
    assert sortie.startswith("formulaire-erreurs gate: SKIP")
    assert "PASS" not in sortie


def test_cli_usage(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["seul"]) == 2
    assert "usage" in capsys.readouterr().err


def test_cli_transmet_les_options_connues(tmp_path: Path) -> None:
    juge = _FauxJuge(_RAPPORT_VERT)
    main(
        [
            str(_application(tmp_path)),
            str(_forge_design_factice(tmp_path)),
            "https://localhost:8443/",
            "--accepter-certificat-local",
            "--etat-connexion",
            "etat.json",
        ],
        runner=juge,
    )
    _, instances, options = juge.appels[0]
    assert instances == ("https://localhost:8443/",)
    assert options == ("--accepter-certificat-local", "--etat-connexion", "etat.json")


def test_le_gate_joue_sous_uv_run_retire_l_environnement_du_projet_du_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sous `uv run`, le python du projet (sans playwright) masquerait celui du poste à l'oracle."""
    venv = tmp_path / "projet" / ".venv"
    poste = tmp_path / "poste" / "bin"
    monkeypatch.setenv("VIRTUAL_ENV", str(venv))
    monkeypatch.setenv(
        "PATH", os.pathsep.join([str(venv / "Scripts"), str(venv / "bin") + os.sep, str(poste)])
    )
    assert _path_sans_venv().split(os.pathsep) == [str(poste)]
    monkeypatch.delenv("VIRTUAL_ENV")
    assert str(venv / "Scripts") in _path_sans_venv(), "hors environnement virtuel : PATH intact"


# --- Recette DOUBLE SENS sur le vrai oracle et une vraie instance servie --------

_PAGE_BANDEAU = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Clients</title>
<style>
  body { margin: 0; font-family: sans-serif; font-size: 16px; line-height: 24px; }
  .bandeau { padding: 12px 24px; background: #fde8e8; color: #7a1010; }
  main { max-width: 640px; padding: 24px; }
  .espace { height: 480px; }
  .champ { margin: 0 0 16px; }
  label { display: block; font-weight: 600; }
  input { box-sizing: border-box; width: 100%; padding: 8px; font: inherit; }
</style></head><body>
<div class="bandeau" role="alert" id="bandeau" hidden></div>
<main>
  <h1>Ajouter un client</h1>
  <div class="espace"><p>Renseignez le domaine puis le courriel du contact.</p></div>
  <form id="f" action="/clients" method="post" novalidate>
    <div class="champ">
      <label for="domaine">Domaine du client</label>
      <input id="domaine" name="domaine" type="text" required pattern="[a-z0-9]+(\\.[a-z0-9]+)+"
             data-valeur-fausse="costcontrol">
    </div>
    <div class="champ">
      <label for="courriel">Courriel du contact</label>
      <input id="courriel" name="courriel" type="email" required>
    </div>
    <button type="submit">Enregistrer le client</button>
  </form>
</main>
<script>
  document.getElementById('f').addEventListener('submit', function (e) {
    e.preventDefault();
    var b = document.getElementById('bandeau');
    b.textContent = 'Refusé : CIBLE_INVALIDE';
    b.hidden = false;
  });
</script>
</body></html>
"""

# Le même formulaire, bâti avec le composant de forge-design : le remède que le message propose.
_PAGE_COMPOSANT = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Clients</title>
<link rel="stylesheet" href="/static/saisie-erreurs.css">
<style>
  body { margin: 0; font-family: sans-serif; font-size: 16px; line-height: 24px; }
  main { max-width: 640px; padding: 24px; }
  .espace { height: 480px; }
  .champ { margin: 0 0 16px; }
  label { display: block; font-weight: 600; }
  input { box-sizing: border-box; width: 100%; padding: 8px; font: inherit; }
</style></head><body>
<main>
  <h1>Ajouter un client</h1>
  <div class="espace"><p>Renseignez le domaine puis le courriel du contact.</p></div>
  <form data-saisie action="/clients" method="post">
    <div class="champ">
      <label for="domaine">Domaine du client</label>
      <input id="domaine" name="domaine" type="text" required pattern="[a-z0-9]+(\\.[a-z0-9]+)+"
             data-valeur-fausse="costcontrol" data-exemple="costcontrol.client.fr">
    </div>
    <div class="champ">
      <label for="courriel">Courriel du contact</label>
      <input id="courriel" name="courriel" type="email" required
             data-exemple="prenom.nom@client.fr">
    </div>
    <button type="submit">Enregistrer le client</button>
  </form>
</main>
<script src="/static/saisie-erreurs.js"></script>
</body></html>
"""


def _forge_design_reelle() -> Path | None:
    base = os.environ.get("FORGE_ROOT")
    racine = Path(base) if base else Path(__file__).resolve().parents[3]
    candidat = racine / "digit-ai-forge-design"
    oracle = candidat / "oracles" / "oracle-erreurs-formulaire.mjs"
    composant = candidat / "corpus" / "composants" / "saisie-erreurs.js"
    return candidat if oracle.is_file() and composant.is_file() else None


class _Silencieux(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return


@contextmanager
def _servir(dossier: Path) -> Iterator[str]:
    """Sert `dossier` sur une instance locale (port libre) : l'« instance servie » de la porte."""
    gestionnaire = functools.partial(_Silencieux, directory=str(dossier))
    serveur = ThreadingHTTPServer(("127.0.0.1", 0), gestionnaire)
    fil = threading.Thread(target=serveur.serve_forever, daemon=True)
    fil.start()
    try:
        yield f"http://127.0.0.1:{serveur.server_address[1]}"
    finally:
        serveur.shutdown()
        serveur.server_close()
        fil.join(timeout=5)


def _application_servie(tmp_path: Path, page: str, forge_design: Path) -> Path:
    racine = tmp_path / "application"
    (racine / "static").mkdir(parents=True)
    (racine / "clients.html").write_text(page, encoding="utf-8")
    composants = forge_design / "corpus" / "composants"
    for nom in ("saisie-erreurs.js", "saisie-erreurs.css"):
        shutil.copy(composants / nom, racine / "static" / nom)
    return racine


def _juger_pour_de_vrai(racine: Path, forge_design: Path, chemin: str) -> Any:
    with _servir(racine) as base:
        verdict = run_formulaire_erreurs_gate(racine, [base + chemin], forge_design)
    saut = [f for f in verdict.findings if "skipped" in f]
    if saut and "outillage de rendu" in saut[0]["skipped"]:
        pytest.skip(f"rendu indisponible sur ce poste : {saut[0]['skipped']}")
    return verdict


_SANS_FORGE_DESIGN = pytest.mark.skipif(
    _forge_design_reelle() is None or shutil.which("node") is None,
    reason="forge-design (oracle, composant) ou node introuvable : oracle réel non joué",
)


@_SANS_FORGE_DESIGN
def test_rouge_reel_le_formulaire_au_bandeau_ne_passe_plus_la_porte(tmp_path: Path) -> None:
    forge_design = _forge_design_reelle()
    assert forge_design is not None
    racine = _application_servie(tmp_path, _PAGE_BANDEAU, forge_design)
    verdict = _juger_pour_de_vrai(racine, forge_design, "/clients.html")
    assert verdict.passed is False, verdict.findings
    ef1 = [f for f in verdict.findings if f.get("regle") == "EF1"]
    assert len(ef1) == 2, "les deux champs ne sont pas désignés"
    assert "CIBLE_INVALIDE" in ef1[0]["issue"], "le bandeau est cité"
    assert "saisie-erreurs" in ef1[0]["remede"]


@_SANS_FORGE_DESIGN
def test_vert_reel_le_meme_formulaire_au_composant_passe_la_porte(tmp_path: Path) -> None:
    forge_design = _forge_design_reelle()
    assert forge_design is not None
    racine = _application_servie(tmp_path, _PAGE_COMPOSANT, forge_design)
    verdict = _juger_pour_de_vrai(racine, forge_design, "/clients.html")
    assert verdict.passed is True, verdict.findings
    assert not [f for f in verdict.findings if "skipped" in f], verdict.findings
    assert verdict.findings[0]["champs_eprouves"] == "2"


@_SANS_FORGE_DESIGN
def test_reel_la_page_servie_sans_formulaire_est_non_jugee_pas_verte(tmp_path: Path) -> None:
    forge_design = _forge_design_reelle()
    assert forge_design is not None
    racine = _application_servie(tmp_path, _PAGE_COMPOSANT, forge_design)
    (racine / "accueil.html").write_text("<html><body><p>Bienvenue</p></body></html>", "utf-8")
    verdict = _juger_pour_de_vrai(racine, forge_design, "/accueil.html")
    assert verdict.passed is True
    assert verdict.findings[0]["non_juge"] == "gate entier", verdict.findings
    assert "aucun champ éprouvable" in verdict.findings[0]["skipped"]


@_SANS_FORGE_DESIGN
def test_reel_le_cli_refuse_le_bandeau_et_accepte_le_composant(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    forge_design = _forge_design_reelle()
    assert forge_design is not None
    rouge = _application_servie(tmp_path / "rouge", _PAGE_BANDEAU, forge_design)
    vert = _application_servie(tmp_path / "vert", _PAGE_COMPOSANT, forge_design)
    with _servir(rouge) as base:
        code_rouge = main([str(rouge), str(forge_design), base + "/clients.html"])
    err_rouge = capsys.readouterr().err
    with _servir(vert) as base:
        code_vert = main([str(vert), str(forge_design), base + "/clients.html"])
    sortie_vert = capsys.readouterr().out
    if code_vert == 0 and "SKIP" in sortie_vert:
        pytest.skip(f"rendu indisponible sur ce poste : {sortie_vert.strip()}")
    assert code_rouge == 1, err_rouge
    assert "EF1" in err_rouge
    assert code_vert == 0, sortie_vert
    assert sortie_vert.startswith("formulaire-erreurs gate: PASS")


# --- Le playbook prescrit ce que le gate juge ------------------------------------

_PLAYBOOK = Path(__file__).resolve().parents[2] / "docs" / "run-playbook.md"
_REPERE = "Une saisie refusée se dit sous son champ, avec la saisie reprise"


def _discipline() -> str:
    texte = _PLAYBOOK.read_text(encoding="utf-8")
    debut = texte.index(_REPERE)
    return texte[debut : texte.index("## Quand lire les détails", debut)]


def test_le_playbook_exige_le_motif_et_les_cinq_regles_du_juge() -> None:
    discipline = _discipline()
    for regle in ("EF1", "EF2", "EF3", "EF4", "EF5"):
        assert f"**{regle}," in discipline, f"{regle} manque à la consigne de construction"
    assert "corpus/composants/saisie-erreurs.js" in discipline, "composant de référence cité"
    assert "refus du serveur" in discipline, "chaque refus du serveur est rendu sous son champ"
    assert "SaisieErreurs.refuser" in discipline
    assert "E-19" in discipline, "la règle d'écriture est citée à la source"


def test_la_commande_du_playbook_est_celle_du_gate() -> None:
    bloc = _discipline().split("```bash")[1].split("```")[0]
    module = re.search(r"python -m (conductor\.gates\.\w+)", bloc)
    assert module is not None, "le playbook donne la commande du gate"
    assert importlib.util.find_spec(module.group(1)) is not None, "le module cité existe"
    assert module.group(1) == "conductor.gates.formulaire_erreurs_gate"
    for option in ("--accepter-certificat-local", "--etat-connexion"):
        assert option in bloc and option in gate_source(), f"{option} : playbook et gate alignés"


def test_les_treize_disciplines_sont_comptees() -> None:
    texte = _PLAYBOOK.read_text(encoding="utf-8")
    assert "**Treize disciplines à ce jour.**" in texte
    assert "**Douze disciplines à ce jour.**" not in texte


def gate_source() -> str:
    module = importlib.import_module("conductor.gates.formulaire_erreurs_gate")
    return Path(module.__file__ or "").read_text(encoding="utf-8")
