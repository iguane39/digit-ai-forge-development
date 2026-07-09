"""Onramps : sélection de la bretelle selon le mode/la distance à la cible."""

from __future__ import annotations

from conductor.contracts import MissionConfig
from conductor.onramp.adapter_onramp import AdapterOnramp
from conductor.onramp.base import Onramp, Substrate
from conductor.onramp.builder_onramp import BuilderOnramp
from conductor.onramp.detect import detect_distance, detect_stack
from conductor.onramp.no_onramp import NoOnramp
from conductor.onramp.scaffold_onramp import ScaffoldOnramp
from conductor.profiles import resolve_profile

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
    node-ts : BuilderOnramp (profil curé).
    stack quelconque (generic) : BuilderOnramp avec profil résolu par cascade (P-14/P-15) —
    plus jamais de « stack non supportée » pour un repo analysable. Erreur seulement si le repo
    n'expose aucun signal (levée par ``resolve_profile``).
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
    # generic : cascade ① manifeste → ③ inférence → (④ LLM) ; lève seulement si aucun signal.
    resolution = resolve_profile(repo)
    return BuilderOnramp(profile=resolution.profile, confidence=resolution.confidence)
