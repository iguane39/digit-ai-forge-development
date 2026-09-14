"""Recette locale du job `code` — rejoue TOUTES les étapes, même après un échec (TF-1101).

============================================================================================
POURQUOI (TF-1072, TF-1101)
============================================================================================

La séquence documentée par `README.md` § « Avant de pousser » (TF-1072) était une liste de
commandes séparées par des retours à la ligne — un développeur qui les copie-colle telles
quelles, ou les enchaîne par `&&`, s'ARRÊTE À LA PREMIÈRE ROUGE : exactement l'inverse de ce
qu'une recette de pré-push doit faire. Le job `code` hébergé, lui, exécute chaque étape même
si une précédente a échoué (chaque `step` GitHub Actions est indépendant) — la séquence locale
mentait donc sur son propre comportement dès la deuxième étape.

CE QUE CE MODULE FAIT : il rejoue les mêmes commandes que le job `code` de
`../.github/workflows/double-gate.yml`, dans le même ordre, CHACUNE INDÉPENDAMMENT DES AUTRES
— un échec n'empêche jamais la suivante de s'exécuter — puis récapitule TOUTES les étapes,
vertes et rouges, en fin de course. Le développeur voit en une fois tout ce qui bloquerait le
push, pas seulement le premier symptôme.

CE QUE CE MODULE NE FAIT PAS : il ne relâche aucune règle des outils qu'il invoque (ruff, mypy,
pytest, les deux gates) — leur configuration et leur plafond restent ceux du dépôt, inchangés ;
ce module ne fait qu'ORDONNANCER leur exécution et RÉCAPITULER leur verdict.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# Racine du produit (digit-ai-forge-development/digit-ai-forge-development) : ce fichier vit
# dans conductor/, donc un niveau sous cette racine.
RACINE_PRODUIT = Path(__file__).resolve().parent.parent
# Racine de la forge (un niveau au-dessus du produit) : c'est là que vit .github/workflows/ —
# même repère que celui vérifié en dogfooding par porte_neutralisee_gate (TF-1040).
RACINE_FORGE = RACINE_PRODUIT.parent


@dataclass(frozen=True)
class Etape:
    """Une étape de la recette : son nom (affiché au récapitulatif), sa commande, son cwd."""

    nom: str
    commande: tuple[str, ...]
    cwd: Path


# Même ordre, mêmes commandes et configuration que le job `code` de
# `../.github/workflows/double-gate.yml` (TF-1072) — une divergence entre les deux listes
# ferait mentir la recette locale sur ce qu'elle prétend rejouer.
ETAPES: tuple[Etape, ...] = (
    Etape("ruff", ("uv", "run", "ruff", "check", "."), RACINE_PRODUIT),
    Etape("mypy", ("uv", "run", "mypy"), RACINE_PRODUIT),
    Etape("pytest", ("uv", "run", "python", "-m", "pytest"), RACINE_PRODUIT),
    Etape(
        "ai-antipatterns",
        ("uv", "run", "python", "-m", "conductor.gates.ai_antipatterns_gate",
         "conductor", "pyproject.toml"),
        RACINE_PRODUIT,
    ),
    Etape(
        "porte-neutralisee",
        ("uv", "run", "python", "-m", "conductor.gates.porte_neutralisee_gate", ".."),
        RACINE_PRODUIT,
    ),
)


class ExecuteurEtape(Protocol):
    def __call__(self, etape: Etape) -> subprocess.CompletedProcess[str]: ...


def _executeur_defaut(etape: Etape) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(etape.commande), cwd=etape.cwd, capture_output=True, text=True, timeout=600
    )


def rejouer(
    etapes: tuple[Etape, ...] = ETAPES, *, executeur: ExecuteurEtape | None = None
) -> list[dict[str, str]]:
    """Joue CHAQUE étape, quel que soit le verdict des précédentes — jamais un arrêt au premier
    rouge. Rend une entrée par étape : nom, code de retour (str, pour rester JSON-simple), et
    sortie combinée (stdout+stderr, tronquée) pour diagnostic."""
    ex = executeur or _executeur_defaut
    resultats: list[dict[str, str]] = []
    for etape in etapes:
        r = ex(etape)
        sortie = ((r.stdout or "") + (r.stderr or ""))[-2000:]
        resultats.append({"nom": etape.nom, "code": str(r.returncode), "sortie": sortie})
    return resultats


def recapituler(resultats: list[dict[str, str]]) -> str:
    """Un récapitulatif qui NOMME chaque étape rouge — jamais un total anonyme qui forcerait à
    rejouer une par une pour savoir laquelle a bloqué."""
    echecs = [r for r in resultats if r["code"] != "0"]
    lignes = [f"  [{'OK   ' if r['code'] == '0' else 'ECHEC'}] {r['nom']}" for r in resultats]
    entete = f"recette locale : {len(resultats) - len(echecs)}/{len(resultats)} etape(s) verte(s)"
    if echecs:
        entete += f" — echec(s) : {', '.join(r['nom'] for r in echecs)}"
    return "\n".join([entete, *lignes])


def main(argv: list[str] | None = None) -> int:
    """Entrée CLI : ``uv run python -m conductor.recette_locale`` (aucun argument)."""
    args = sys.argv[1:] if argv is None else argv
    if args:
        print("usage : uv run python -m conductor.recette_locale (aucun argument)",
              file=sys.stderr)
        return 2
    resultats = rejouer()
    print(recapituler(resultats))
    for r in resultats:
        if r["code"] != "0" and r["sortie"].strip():
            print(f"\n--- sortie de « {r['nom']} » ---\n{r['sortie']}", file=sys.stderr)
    return 1 if any(r["code"] != "0" for r in resultats) else 0


if __name__ == "__main__":
    raise SystemExit(main())
