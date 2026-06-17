"""Onramps : sélection de la bretelle selon le mode/la distance à la cible."""

from __future__ import annotations

from conductor.contracts import MissionConfig
from conductor.onramp.adapter_onramp import AdapterOnramp
from conductor.onramp.base import Onramp, Substrate
from conductor.onramp.builder_onramp import BuilderOnramp
from conductor.onramp.detect import detect_distance, detect_stack
from conductor.onramp.no_onramp import NoOnramp
from conductor.onramp.scaffold_onramp import ScaffoldOnramp

__all__ = [
    "AdapterOnramp",
    "BuilderOnramp",
    "NoOnramp",
    "Onramp",
    "ScaffoldOnramp",
    "Substrate",
    "select_onramp",
]


def select_onramp(mission: MissionConfig) -> Onramp:
    """greenfield → Scaffold ; brownfield → routage stack-aware.

    fastapi : NoOnramp (distance A) ou AdapterOnramp (distance C).
    node-ts (et futurs profils) : BuilderOnramp (B-standard).
    stack inconnue : non supportée.
    """
    if mission.mode == "greenfield":
        return ScaffoldOnramp()
    assert mission.existing_repo is not None  # garanti par cadrer() ; mypy narrowing
    repo = mission.existing_repo
    stack = detect_stack(repo)
    if stack == "fastapi":
        return NoOnramp() if detect_distance(repo) == "A" else AdapterOnramp()
    if stack == "node-ts":
        return BuilderOnramp()
    raise ValueError(
        f"Stack non supportée pour {repo} : ni FastAPI ni node-ts. "
        "Ajouter un profil (TargetProfile) + un cas de routage pour cette stack."
    )
