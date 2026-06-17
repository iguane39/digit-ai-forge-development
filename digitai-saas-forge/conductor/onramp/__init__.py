"""Onramps : sélection de la bretelle selon le mode/la distance à la cible."""

from __future__ import annotations

from conductor.onramp.base import Onramp, Substrate
from conductor.onramp.scaffold_onramp import ScaffoldOnramp

__all__ = ["Onramp", "ScaffoldOnramp", "Substrate", "select_onramp"]


def select_onramp(mode: str) -> Onramp:
    """Choisit la bretelle. brownfield (None/Adapter/Builder) arrive aux epics BA/BC/BB."""
    if mode == "greenfield":
        return ScaffoldOnramp()
    raise NotImplementedError(
        "Onramp brownfield à venir (epic BA : NoOnramp, puis BC/BB) — mode non supporté en B0."
    )
