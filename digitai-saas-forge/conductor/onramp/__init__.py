"""Onramps : sélection de la bretelle selon le mode/la distance à la cible."""

from __future__ import annotations

from conductor.contracts import MissionConfig
from conductor.onramp.adapter_onramp import AdapterOnramp
from conductor.onramp.base import Onramp, Substrate
from conductor.onramp.detect import detect_distance
from conductor.onramp.no_onramp import NoOnramp
from conductor.onramp.scaffold_onramp import ScaffoldOnramp

__all__ = ["AdapterOnramp", "NoOnramp", "Onramp", "ScaffoldOnramp", "Substrate", "select_onramp"]


def select_onramp(mission: MissionConfig) -> Onramp:
    """greenfield → Scaffold ; brownfield → NoOnramp (A) ou AdapterOnramp (C) selon la distance."""
    if mission.mode == "greenfield":
        return ScaffoldOnramp()
    assert mission.existing_repo is not None  # garanti par cadrer() ; mypy narrowing
    distance = detect_distance(mission.existing_repo)
    return NoOnramp() if distance == "A" else AdapterOnramp()
