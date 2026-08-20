"""Étape A — Cadrage cible & style.

Transforme une idée + des contraintes en une MissionConfig validable. Cible et charte
paramétrables (décision 08). Les briques de t0 (multi-tenancy, rbac, auth-sso) sont
imposées en `build`, quoi que demande l'appelant (décision canonique 05).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import TypeAdapter, ValidationError

from conductor.catalog import CATALOG, T0_BRICKS
from conductor.contracts import BrickChoice, MissionConfig

DEFAULT_CHARTER = Path("design/DESIGN.md")
DEFAULT_STYLE = "digitai"
# TF-0406 (RF-8) — la MONO-CIBLE se déclare au contrat d'entrée, plus seulement au code : le
# scaffold ne connaît qu'une cible (`targets/fastapi-saas`, template
# gh:fastapi/full-stack-fastapi-template). Un produit Next.js/Strapi ne l'apprenait qu'en
# lisant `scaffold.py` — un contrat qui tait sa seule valeur admise laisse chaque appelant la
# découvrir au premier échec.
CIBLES_CONNUES: tuple[str, ...] = ("fastapi-saas",)
DEFAULT_TARGET = "fastapi-saas"

_SCOPE_ADAPTER = TypeAdapter(list[BrickChoice])


def charger_scope(path: Path) -> list[BrickChoice]:
    """Charge un scope SaaS depuis un fichier JSON (liste de BrickChoice).

    Le fichier est validé par les contrats pydantic ; toute erreur (fichier absent, JSON
    malformé, schéma non respecté) est convertie en `ValueError` lisible — le CLI n'a rien
    à interpréter. Les noms hors catalogue restent rejetés par `cadrer()`.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as err:
        raise ValueError(f"Fichier de scope illisible : {path} ({err.strerror})") from err
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as err:
        raise ValueError(f"Fichier de scope JSON invalide : {path} — {err}") from err
    try:
        return _SCOPE_ADAPTER.validate_python(data)
    except ValidationError as err:
        raise ValueError(
            f"Scope invalide dans {path} : attendu une liste d'objets "
            f'{{"name": ..., "decision": "build|buy|skip"}} — {err}'
        ) from err


def _merge_t0(scope: list[BrickChoice]) -> list[BrickChoice]:
    """Garantit que les briques de t0 sont présentes en `build` (décision 05)."""
    forced = {b.name: b for b in scope}
    for name in T0_BRICKS:
        forced[name] = BrickChoice(name=name, decision="build")
    # ordre : t0 d'abord, puis le reste dans l'ordre fourni
    rest = [b for b in scope if b.name not in T0_BRICKS]
    return [forced[n] for n in T0_BRICKS] + rest


def cadrer(
    idea: str,
    *,
    mode: Literal["greenfield", "brownfield"] = "greenfield",
    existing_repo: Path | None = None,
    intent: Literal["remediation", "complement", "both"] = "remediation",
    target: str = DEFAULT_TARGET,
    brand_charter: Path = DEFAULT_CHARTER,
    style_slug: str = DEFAULT_STYLE,
    budget: str | None = None,
    deadline: str | None = None,
    bricks: list[BrickChoice] | None = None,
) -> MissionConfig:
    """A · produit la configuration de mission. Pose les briques de t0 (décision 05).

    `bricks` liste les briques additionnelles voulues ; les briques de t0 sont ajoutées
    automatiquement et ne peuvent pas être désactivées ici. Les noms inconnus du catalogue
    sont rejetés tôt (fail-fast).
    """
    if not idea.strip():
        raise ValueError("L'idée produit ne peut pas être vide.")
    if mode == "brownfield" and existing_repo is None:
        raise ValueError("Le mode brownfield exige un existing_repo (repo cible existant).")
    if mode == "greenfield" and existing_repo is not None:
        raise ValueError("Le mode greenfield n'accepte pas d'existing_repo (on génère le repo).")

    # TF-0406 (RF-8) — une cible inconnue se REFUSE à l'entrée, en nommant les cibles admises :
    # un contrat qui accepte un argument sans effet coûte plus cher qu'un contrat qui le refuse,
    # et la mono-cible ne doit plus s'apprendre en lisant scaffold.py au premier échec.
    if target not in CIBLES_CONNUES:
        raise ValueError(
            f"Cible de scaffold inconnue : {target!r} — cibles admises : "
            f"{', '.join(CIBLES_CONNUES)} (mono-cible assumée : le scaffold ne connaît que le "
            "template FastAPI ; un produit Next.js/Strapi passe par le mode brownfield ou par "
            "une cible à ajouter sous targets/)"
        )

    requested = bricks or []
    for choice in requested:
        if choice.name not in CATALOG:
            raise ValueError(f"Brique inconnue du catalogue : {choice.name!r}")

    return MissionConfig(
        idea=idea.strip(),
        mode=mode,
        existing_repo=existing_repo,
        brownfield_intent=intent,
        target=target,
        budget=budget,
        deadline=deadline,
        saas_scope=_merge_t0(requested),
        brand_charter=brand_charter,
        style_slug=style_slug,
    )
