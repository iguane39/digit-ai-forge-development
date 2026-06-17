"""Onramps : sélection de la bretelle selon le mode/la distance à la cible."""

from __future__ import annotations

from conductor.contracts import MissionConfig
from conductor.onramp.base import Onramp, Substrate
from conductor.onramp.no_onramp import NoOnramp
from conductor.onramp.scaffold_onramp import ScaffoldOnramp

__all__ = ["NoOnramp", "Onramp", "ScaffoldOnramp", "Substrate", "select_onramp"]


def select_onramp(mission: MissionConfig) -> Onramp:
    """BA : brownfield → NoOnramp (branche A). BC/BB ajouteront Adapter/Builder selon la distance.
    """
    if mission.mode == "greenfield":
        return ScaffoldOnramp()
    return NoOnramp()
