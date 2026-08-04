"""Onramp — amène un projet au point où le contrat de la cible est applicable.

Généralise le scaffold-first : greenfield = onramp qui *génère* ; brownfield = onramp qui
*reprend/normalise/construit*. Sortie commune : un Substrate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field

from conductor.contracts import MissionConfig
from conductor.profiles import TargetProfile


class Substrate(BaseModel):
    """État prêt-à-planifier : un repo + son profil de cible (+ baseline/carte d'archi)."""

    repo_path: Path
    profile: TargetProfile
    design_md_path: Path  # chemin CONCRET du DESIGN.md dans le repo (≠ convention du profil)
    baseline: dict[str, bool] | None = None  # statut vert/rouge des gates existants (capturé en BA)
    arch_map: dict[str, Any] | None = None  # carte d'architecture (remplie en BC/BB)
    declared_degradation: list[str] = Field(default_factory=list)  # dégradation explicite (B)
    # P-17 : niveau de confiance du profil résolu (curated/manifest/inferred/analyzed) — affiché
    # au HITL-0. "curated" = profil de registre (aucune validation supplémentaire requise).
    profile_confidence: str = "curated"


class Onramp(Protocol):
    """Prépare un Substrate à partir d'une mission et d'un répertoire de destination."""

    def prepare(self, config: MissionConfig, dest: Path) -> Substrate: ...
