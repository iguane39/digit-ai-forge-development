"""Étape A — Cadrage cible & style.

Transforme une idée + des contraintes en une MissionConfig validable. Cible et charte
paramétrables (décision 08). Les briques de t0 (multi-tenancy, rbac, auth-sso) sont
imposées en `build`, quoi que demande l'appelant (décision canonique 05).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from conductor.catalog import CATALOG, T0_BRICKS
from conductor.contracts import BrickChoice, MissionConfig

DEFAULT_CHARTER = Path("design/DESIGN.md")
DEFAULT_STYLE = "digitai"


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
    target: str = "fastapi-saas",
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
