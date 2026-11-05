"""Gate « erreurs de formulaire » (TF-2172) — la treizième discipline devient oracle exécutable.

Convention documentée dans `../../docs/run-playbook.md` § « Produit livrable — disciplines de
production » : **une saisie refusée se dit sous son champ**. Le cas d'origine (Produit-86,
05/11/2026) : un refus « Refusé : CIBLE_INVALIDE » affiché en bandeau en tête de page, sans champ
désigné, sans forme attendue, seulement à l'envoi. Aucune porte de la forge ne l'a vu : le design
lint juge le DESIGN.md, les gates statiques lisent le code, aucun n'envoie une valeur fausse.

Ce gate DÉLÈGUE, ne duplique pas (même posture que ``affordances_gate``) : il lance
`oracle-erreurs-formulaire.mjs` de forge-design (dépôt frère, lecture seule) sur l'instance
SERVIE de l'application et traduit son rapport. L'oracle saisit une valeur fausse par champ,
quitte le champ, tente l'envoi, et juge cinq règles : EF1 champ désigné (``aria-invalid`` +
message relié), EF2 message près du champ, EF3 saisie reprise ou forme attendue, EF4 envoi
retenu, EF5 vérification à la sortie du champ. Le composant de référence qui les tient est
``corpus/composants/saisie-erreurs.js`` de forge-design.

Ce qu'il ne fait PAS, et dit : il ne sert pas l'application (l'instance est fournie), et il ne
voit jamais un refus venu du SERVEUR, puisque l'oracle intercepte et refuse les requêtes
d'écriture pour ne rien créer chez l'instance. Un refus du serveur rendu sous son champ
(``SaisieErreurs.refuser`` du composant) est exigé à la construction par le playbook, et se juge
à la main.

P-06 : ce que la porte ne peut pas juger — pas de formulaire, pas d'instance servie, oracle ou
outillage de rendu indisponible — elle le DIT (constat « skipped », verdict ``non_juge`` « gate
entier », CLI « SKIP »), jamais un PASS muet.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from conductor.contracts import GateVerdict
from conductor.process import ProcessRunner, SubprocessProcessRunner, ToolNotFound

# Marque d'un constat « skipped » qui couvre le gate ENTIER (rien n'a été jugé) : le CLI rend
# alors SKIP, distinct de PASS (même convention que static_cache_gate, TF-2059).
_GATE_ENTIER = "gate entier"

ORACLE = Path("oracles") / "oracle-erreurs-formulaire.mjs"
COMPOSANT = "corpus/composants/saisie-erreurs.js"

# Gabarits et composants où un formulaire s'écrit. Même posture heuristique que les autres gates
# statiques : une coïncidence de chaîne (`<form`, `<Form`), pas une analyse du DOM.
_SUFFIXES = (".html", ".htm", ".jinja", ".jinja2", ".j2", ".tsx", ".jsx", ".vue", ".svelte")
_FORMULAIRE = re.compile(r"<form\b", re.IGNORECASE)
# Hors périmètre : suites de tests, dépendances tierces, environnements virtuels.
_EXCLUDED_PARTS = ("test", "tests", "node_modules", ".venv", "venv", "vendor", ".git")

#: Gravités qui font échouer l'oracle (``majeur`` et ``bloquant``) ; l'avertissement est rendu
#: mais ne bloque pas.
_DURES = ("bloquant", "majeur")

#: Le remède de chaque règle : le message d'un refus propose une correction, la recette la joue
#: (TF-1013) — le formulaire bâti avec le composant passe la porte.
REMEDES: dict[str, str] = {
    "EF0": (
        "servir l'écran jugé à l'adresse fournie, sans redirection (connexion : fournir "
        "--etat-connexion)"
    ),
    "EF1": (
        'désigner le champ : aria-invalid="true" et un message neuf, visible, relié par '
        f"aria-describedby, posé sous le champ ; composant de référence {COMPOSANT} de "
        "forge-design, ou un équivalent qui tient EF1 à EF5"
    ),
    "EF2": (
        "poser le message à 120 px au plus du champ et dans la fenêtre, jamais en bandeau en "
        "tête de page"
    ),
    "EF3": (
        "le message reprend la saisie et donne la forme attendue (data-exemple du champ) : "
        "« costcontrol » n'est pas un domaine complet, écris-le ainsi : "
        "costcontrol.domaine-du-client.fr (E-19 du plancher d'écriture)"
    ),
    "EF4": (
        "retenir l'envoi (preventDefault, pas de requête ni de navigation) tant qu'un champ "
        "est invalide"
    ),
    "EF5": (
        "vérifier à la sortie du champ (focusout) et effacer l'erreur dès que la valeur est "
        "corrigée"
    ),
}
_REMEDE_PAR_DEFAUT = f"voir {COMPOSANT} de forge-design et le playbook (treizième discipline)"


class OracleIllisible(RuntimeError):
    """L'oracle n'a rendu aucun rapport JSON exploitable (crash, sortie vide ou tronquée)."""


class OracleErreursFormulaireRunner(Protocol):
    """Exécute l'oracle sur des instances servies et renvoie son rapport JSON complet."""

    def run_oracle(
        self, oracle_path: Path, instances: Sequence[str], options: Sequence[str]
    ) -> dict[str, Any]: ...


def _path_sans_venv() -> str:
    """Le ``PATH`` courant privé de l'environnement virtuel de l'appelant.

    Joué par ``uv run``, le gate a le ``python`` du projet en tête de ``PATH``, qui n'importe pas
    playwright : l'oracle choisit alors cet interpréteur et rend SKIP « outillage de rendu
    indisponible » alors que le poste le porte. Retirer l'environnement du projet lui laisse
    chercher l'interpréteur du poste, comme s'il était lancé à la main.
    """
    venv = os.environ.get("VIRTUAL_ENV")
    chemin = os.environ.get("PATH", "")
    if not venv:
        return chemin
    exclus = {os.path.normcase(os.path.join(venv, d)) for d in ("Scripts", "bin")}
    gardes = [
        p
        for p in chemin.split(os.pathsep)
        if os.path.normcase(p.rstrip("/\\")) not in exclus
    ]
    return os.pathsep.join(gardes)


class SubprocessOracleRunner:
    """Runner de prod : ``node <oracle> <instance>… --json-only [options]``.

    L'oracle rend 0 (PASS), 1 (FAIL) ou 2 (SKIP) et écrit son rapport sur stdout dans les trois
    cas : le code de sortie n'est pas lu, le verdict l'est (même règle que le gate design).
    """

    def __init__(self, runner: ProcessRunner | None = None) -> None:
        self._runner: ProcessRunner = runner or SubprocessProcessRunner(
            env_overlay={"PATH": _path_sans_venv()}
        )

    def run_oracle(
        self, oracle_path: Path, instances: Sequence[str], options: Sequence[str]
    ) -> dict[str, Any]:
        args = ["node", str(oracle_path), *instances, "--json-only", *options]
        result = self._runner.run(args, timeout_s=600)
        try:
            rapport = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            reste = (result.stderr.strip().splitlines() or ["aucune sortie d'erreur"])[-1]
            raise OracleIllisible(
                f"sortie illisible (code {result.returncode}) : {reste}"
            ) from exc
        if not isinstance(rapport, dict) or "verdict" not in rapport:
            raise OracleIllisible(f"rapport sans verdict (code {result.returncode})")
        return rapport


def _is_excluded(path: Path, racine: Path) -> bool:
    return any(part.lower() in _EXCLUDED_PARTS for part in path.relative_to(racine).parts)


def formulaires_de_l_application(repo_path: Path) -> list[Path]:
    """Fichiers de l'application (hors tests et dépendances) qui portent un ``<form``."""
    trouves: list[Path] = []
    for path in sorted(repo_path.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _SUFFIXES:
            continue
        if _is_excluded(path, repo_path):
            continue
        if _FORMULAIRE.search(path.read_text(encoding="utf-8", errors="ignore")):
            trouves.append(path)
    return trouves


def _non_juge(raison: str, **extra: str) -> GateVerdict:
    return GateVerdict(
        gate="formulaire-erreurs",
        passed=True,
        findings=[{"skipped": raison, "non_juge": _GATE_ENTIER, **extra}],
    )


def _raisons_du_skip(rapport: dict[str, Any], instances: Sequence[str]) -> str:
    """Pourquoi l'oracle n'a rien jugé : ses motifs propres aux cibles, sinon le dernier."""
    non_juge = [str(x) for x in rapport.get("non_juge", [])]
    motifs = [x for x in non_juge if any(u in x for u in instances)]
    motifs += [
        str(f.get("msg", "")) for f in rapport.get("findings", []) if f.get("regle") == "EF0"
    ]
    if not motifs and non_juge:
        motifs = [non_juge[-1]]
    return " ; ".join(motifs) if motifs else "aucun motif rendu par l'oracle"


def _verdict_from_report(
    rapport: dict[str, Any], instances: Sequence[str], *, log_ref: str
) -> GateVerdict:
    verdict_oracle = str(rapport.get("verdict"))
    if verdict_oracle == "SKIP":
        suite = _non_juge(
            "oracle-erreurs-formulaire n'a rien jugé : " + _raisons_du_skip(rapport, instances)
        )
        return suite.model_copy(update={"log_ref": log_ref})
    if verdict_oracle not in ("PASS", "FAIL"):
        return _non_juge(f"oracle-erreurs-formulaire : verdict inconnu « {verdict_oracle} »")
    findings: list[dict[str, str]] = []
    for f in rapport.get("findings", []):
        gravite = str(f.get("sev", ""))
        if gravite == "info":
            continue
        regle = str(f.get("regle", ""))
        findings.append(
            {
                "regle": regle,
                "gravite": gravite,
                "issue": str(f.get("msg", "")),
                "ecran": str(f.get("where", "")),
                "remede": REMEDES.get(regle, _REMEDE_PAR_DEFAUT),
            }
        )
    if verdict_oracle == "PASS":
        findings.insert(0, {"champs_eprouves": str(rapport.get("champs_eprouves", 0))})
    return GateVerdict(
        gate="formulaire-erreurs",
        passed=verdict_oracle == "PASS",
        findings=findings,
        log_ref=log_ref,
    )


def run_formulaire_erreurs_gate(
    repo_path: Path,
    instances: Sequence[str],
    forge_design_path: Path | None,
    *,
    runner: OracleErreursFormulaireRunner | None = None,
    options: Sequence[str] = (),
) -> GateVerdict:
    """Joue ``oracle-erreurs-formulaire`` sur l'instance servie quand l'application a un formulaire.

    ``instances`` : adresses http(s) des écrans qui portent les formulaires, servis par le run.
    ``options`` : options de l'oracle transmises telles quelles (``--accepter-certificat-local``,
    ``--etat-connexion <fichier>``).
    """
    if not repo_path.exists():
        return _non_juge(f"arborescence de l'application absente : {repo_path}")
    formulaires = formulaires_de_l_application(repo_path)
    if not formulaires:
        return _non_juge(
            "aucun formulaire dans l'application (aucun <form dans ses gabarits ni ses "
            "composants) : rien à éprouver"
        )
    if not instances:
        noms = ", ".join(str(p.relative_to(repo_path)) for p in formulaires[:5])
        reste = f" (+{len(formulaires) - 5})" if len(formulaires) > 5 else ""
        return _non_juge(
            f"{len(formulaires)} fichier(s) portent un formulaire ({noms}{reste}) mais aucune "
            "instance servie n'est fournie : l'oracle juge l'écran rendu, pas le code — servir "
            "l'application puis rejouer le gate avec l'adresse de chaque écran à formulaire"
        )
    oracle = forge_design_path / ORACLE if forge_design_path is not None else None
    if oracle is None or not oracle.is_file():
        return _non_juge(
            f"forge-design introuvable ou sans {ORACLE.as_posix()} : oracle non exécuté"
        )
    try:
        rapport = (runner or SubprocessOracleRunner()).run_oracle(oracle, instances, options)
    except (ToolNotFound, RuntimeError) as exc:
        return _non_juge(f"oracle non exécutable : {exc}")
    return _verdict_from_report(rapport, instances, log_ref=str(repo_path))


# Options de l'oracle que le CLI transmet : (nom, prend une valeur).
_OPTIONS_TRANSMISES = {"--accepter-certificat-local": False, "--etat-connexion": True}


def _lire_argv(argv: Sequence[str]) -> tuple[list[str], list[str]] | None:
    """Sépare les positionnels des options transmises ; ``None`` si une option est inconnue."""
    positionnels: list[str] = []
    options: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in _OPTIONS_TRANSMISES:
            options.append(arg)
            if _OPTIONS_TRANSMISES[arg]:
                if i + 1 >= len(argv):
                    return None
                options.append(argv[i + 1])
                i += 1
        elif arg.startswith("--"):
            return None
        else:
            positionnels.append(arg)
        i += 1
    return positionnels, options


def main(
    argv: Sequence[str] | None = None, *, runner: OracleErreursFormulaireRunner | None = None
) -> int:
    """Entrée CLI.

    ``python -m conductor.gates.formulaire_erreurs_gate <repo> <forge-design> [<url>…]
    [--accepter-certificat-local] [--etat-connexion <fichier>]``
    """
    lu = _lire_argv(sys.argv[1:] if argv is None else argv)
    if lu is None or len(lu[0]) < 2:
        print(
            "usage: python -m conductor.gates.formulaire_erreurs_gate <repo> <forge-design> "
            "[<url>…] [--accepter-certificat-local] [--etat-connexion <fichier>]",
            file=sys.stderr,
        )
        return 2
    positionnels, options = lu
    verdict = run_formulaire_erreurs_gate(
        Path(positionnels[0]),
        positionnels[2:],
        Path(positionnels[1]),
        runner=runner,
        options=options,
    )
    if verdict.passed:
        non_juges = [f["skipped"] for f in verdict.findings if f.get("non_juge") == _GATE_ENTIER]
        if non_juges:
            # P-06 : SKIP tracé, exit 0 (jamais un échec implicite) — mais jamais écrit « PASS ».
            print(f"formulaire-erreurs gate: SKIP (non jugé) — {' ; '.join(non_juges)}")
        else:
            champs = verdict.findings[0].get("champs_eprouves", "0")
            print(
                f"formulaire-erreurs gate: PASS — {champs} champ(s) éprouvé(s) ; le refus du "
                "serveur n'est pas éprouvé (l'oracle n'envoie rien), à juger à la main"
            )
        return 0
    durs = [f for f in verdict.findings if f.get("gravite") in _DURES]
    print(f"formulaire-erreurs gate: FAIL ({len(durs)} constat(s))", file=sys.stderr)
    for f in durs:
        print(f"  - [{f['regle']}] {f['ecran']} : {f['issue']}", file=sys.stderr)
        print(f"      remède : {f['remede']}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
