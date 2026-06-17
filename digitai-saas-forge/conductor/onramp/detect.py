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


def _has_ci(repo: Path) -> bool:
    wf = repo / ".github" / "workflows"
    if not wf.is_dir():
        return False
    return any(wf.glob("*.yml")) or any(wf.glob("*.yaml"))


def detect_distance(repo: Path) -> Literal["A", "C"]:
    """Classe le repo : 'A' (déjà cible) ou 'C' (à normaliser). Lève si non-FastAPI (→ BB)."""
    if not (repo / "pyproject.toml").exists():
        raise ValueError(
            f"Repo non reconnu comme cible FastAPI (pyproject.toml absent) dans {repo} : "
            "stack arbitraire → relève de l'epic BB (BuilderOnramp)."
        )
    has_design = (repo / "design" / "DESIGN.md").exists()
    has_ci = _has_ci(repo)
    return "A" if (has_design and has_ci) else "C"
