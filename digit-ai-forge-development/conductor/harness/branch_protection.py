"""Adapter GitHub CLI : lecture SOURCÉE de la protection de branche (constat D-26 (a), TF-0886).

Le lot `digit-ai-forge-development - RETOURS - 20260905b` a mesuré un push ordinaire accepté sur
`main` (`053fdaf`) avec « Bypassed rule violations for refs/heads/main », en nommant deux règles
enfreintes (« Changes must be made through a pull request », « 2 of 2 required status checks are
expected »). Le mandat qui avait ordonné ce push (`input/00-travaux/pilot - TRAVAUX -
20260905f.md`) décrivait pourtant `main` comme « protégée sur GitHub (avance rapide seule) ».
Lue chez l'hébergeur le 06/09/2026 (`gh api repos/iguane39/digit-ai-forge-development/branches
/main/protection`), la protection réellement configurée est tout autre : revue obligatoire
(1 approbation), deux contrôles requis (`code`, `design`, stricts) — et `enforce_admins` vaut
`false`, ce qui permet au compte propriétaire de contourner ces deux règles d'office.

Ce module mécanise l'exigence de la classe (D-26 (a)) : « lire la protection chez l'hébergeur
avant de la décrire ou de la lever, citer ses champs, déclarer tout contournement d'office comme
un constat ». `decrire_protection` ne reformule jamais de mémoire — chaque champ vient d'une clé
nommée de la réponse API — et signale explicitement l'absence d'`enforce_admins` comme un
contournement CONSTATÉ, jamais laissé en silence.

Reste humain, volontairement hors de ce module : décider si la protection doit s'appliquer aux
administrateurs (`enforce_admins`) est un geste sur le dépôt hébergé, jamais une écriture d'agent
(cf. lot 20260905b, table des restes — « la configuration du dépôt hébergé est un geste humain »).
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Any, Protocol

from conductor.harness._text import clip


@dataclass(frozen=True)
class ProtectionDescription:
    """Champs cités de la protection de branche — jamais reformulés de mémoire."""

    revue_requise: bool
    approbations_requises: int
    contextes_requis: tuple[str, ...]
    contexte_strict: bool
    admins_soumis: bool
    force_push_autorise: bool
    constats: tuple[str, ...] = field(default_factory=tuple)

    @property
    def contourne_d_office(self) -> bool:
        """Un compte peut-il pousser sur la branche en ignorant revue + contrôles ?"""
        return not self.admins_soumis


class GhBranchProtectionReader(Protocol):
    def read(self, owner: str, repo: str, branch: str = "main") -> dict[str, Any]: ...


class SubprocessGhBranchProtection:
    """Lit `gh api repos/{owner}/{repo}/branches/{branch}/protection`. Injectable (fake en test)."""

    def __init__(self, *, timeout_s: int = 60) -> None:
        self._timeout_s = timeout_s

    def read(self, owner: str, repo: str, branch: str = "main") -> dict[str, Any]:
        endpoint = f"repos/{owner}/{repo}/branches/{branch}/protection"
        try:
            proc = subprocess.run(
                ["gh", "api", endpoint],
                capture_output=True,
                text=True,
                timeout=self._timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"gh : timeout après {self._timeout_s}s") from exc
        if proc.returncode != 0:
            raise RuntimeError(f"gh a échoué (code {proc.returncode}) : {clip(proc.stderr, 500)}")
        out = proc.stdout.strip()
        if not out:
            raise RuntimeError(f"gh api {endpoint} : réponse vide")
        parsed: dict[str, Any] = json.loads(out)
        return parsed


def decrire_protection(config: dict[str, Any]) -> ProtectionDescription:
    """Transforme la réponse brute `gh api .../protection` en description CITABLE.

    Ne reformule rien : chaque champ vient d'une clé nommée de la réponse — jamais d'une
    supposition ni d'un souvenir de mandat. `enforce_admins.enabled=False` est déclaré d'office
    comme un contournement (constat), jamais laissé en silence (D-26 (a)).
    """
    reviews = config.get("required_pull_request_reviews") or {}
    checks = config.get("required_status_checks") or {}
    admins_soumis = bool((config.get("enforce_admins") or {}).get("enabled", False))
    force_push = bool((config.get("allow_force_pushes") or {}).get("enabled", False))
    contextes = tuple(checks.get("contexts") or [])

    constats: list[str] = []
    if not admins_soumis:
        constats.append(
            "enforce_admins=false : le compte propriétaire/administrateur contourne la revue "
            "et les contrôles requis d'office (constat mesuré, pas une hypothèse)."
        )
    if force_push:
        constats.append("allow_force_pushes=true : l'historique de la branche peut être réécrit.")

    return ProtectionDescription(
        revue_requise=bool(reviews),
        approbations_requises=int(reviews.get("required_approving_review_count", 0)),
        contextes_requis=contextes,
        contexte_strict=bool(checks.get("strict", False)),
        admins_soumis=admins_soumis,
        force_push_autorise=force_push,
        constats=tuple(constats),
    )


def resume_citable(description: ProtectionDescription) -> str:
    """Une ligne citable, champs nommés — jamais « avance rapide seulement » non vérifié."""
    revue = (
        f"revue obligatoire ({description.approbations_requises} approbation(s))"
        if description.revue_requise
        else "aucune revue obligatoire"
    )
    if description.contextes_requis:
        checks = (
            f"{len(description.contextes_requis)} contrôle(s) requis "
            f"({', '.join(description.contextes_requis)}"
            f"{', strict' if description.contexte_strict else ''})"
        )
    else:
        checks = "aucun contrôle requis"
    admins = (
        "administrateurs soumis" if description.admins_soumis else "administrateurs NON soumis"
    )
    ligne = f"{revue} ; {checks} ; {admins}."
    if description.constats:
        ligne += " Constats : " + " ".join(description.constats)
    return ligne


def main(argv: list[str] | None = None) -> int:
    """CLI : `python -m conductor.harness.branch_protection <owner> <repo> [branch=main]`.

    Lit la protection RÉELLE chez l'hébergeur avant toute description — jamais de prose non
    sourcée sur la règle de branche (D-26 (a)). Code de retour 1 si un contournement d'office
    est constaté (ex. `enforce_admins=false`), 0 sinon — un signal, pas un gate CI.
    """
    args = sys.argv[1:] if argv is None else argv
    if len(args) not in (2, 3):
        print(
            "usage: python -m conductor.harness.branch_protection <owner> <repo> [branch=main]",
            file=sys.stderr,
        )
        return 2
    owner, repo = args[0], args[1]
    branch = args[2] if len(args) == 3 else "main"
    config = SubprocessGhBranchProtection().read(owner, repo, branch)
    description = decrire_protection(config)
    print(resume_citable(description))
    return 1 if description.contourne_d_office else 0


if __name__ == "__main__":
    raise SystemExit(main())
