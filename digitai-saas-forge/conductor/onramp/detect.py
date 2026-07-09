"""Détection de la distance à la cible pour router la bretelle brownfield.

A : repo déjà conforme (pyproject + DESIGN.md + CI) → NoOnramp.
C : repo FastAPI-compatible mais incomplet (pyproject présent, DESIGN.md ou CI manquant)
    → AdapterOnramp (normalisation).
Sinon (pas de pyproject) : stack arbitraire → relève de BB.
Heuristique pure (faits durs déterministes).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from conductor.capabilities import Capabilities, detect_capabilities
from conductor.profiles import FASTAPI_SAAS

__all__ = ["Capabilities", "detect_capabilities", "detect_distance", "detect_stack", "has_ci"]


def has_ci(repo: Path) -> bool:
    """Présence d'un workflow CI (.github/workflows/*.yml|*.yaml)."""
    wf = repo / ".github" / "workflows"
    if not wf.is_dir():
        return False
    return any(wf.glob("*.yml")) or any(wf.glob("*.yaml"))


def has_pyproject(repo: Path) -> bool:
    """Marqueur de projet Python/FastAPI : présence de pyproject.toml."""
    return (repo / "pyproject.toml").exists()


def detect_distance(repo: Path) -> Literal["A", "C"]:
    """Classe le repo : 'A' (déjà cible) ou 'C' (à normaliser). Lève si non-FastAPI (→ BB)."""
    if not has_pyproject(repo):
        raise ValueError(
            f"Repo non reconnu comme cible FastAPI (pyproject.toml absent) dans {repo} : "
            "stack arbitraire → relève de l'epic BB (BuilderOnramp)."
        )
    has_design = (repo / FASTAPI_SAAS.design_md_path).exists()
    return "A" if (has_design and has_ci(repo)) else "C"


def detect_stack(repo: Path) -> Literal["fastapi", "node-ts", "generic"]:
    """Détecte la stack par marqueur RACINE curé : pyproject.toml → fastapi ; package.json →
    node-ts ; sinon ``generic`` (P-15 : plus d'échec indirect — la résolution générique prend le
    relais via ``resolve_profile`` + ``BuilderOnramp``).

    Priorité à pyproject.toml si les deux marqueurs coexistent (cas full-stack rare).
    """
    if (repo / "pyproject.toml").exists():
        return "fastapi"
    if (repo / "package.json").exists():
        return "node-ts"
    return "generic"
