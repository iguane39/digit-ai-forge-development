"""Préflight de disponibilité des outils (portabilité — backlog P-13).

Vérifie via ``shutil.which`` que les binaires requis (claude, npx, gh, uv, git, copier…) sont
présents dans le PATH, avec un message actionnable. Portable (aucun spawn, juste la résolution).
"""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class PreflightReport:
    """Disponibilité de chaque outil requis (True = résolu dans le PATH)."""

    available: dict[str, bool]

    @property
    def missing(self) -> list[str]:
        return sorted(tool for tool, ok in self.available.items() if not ok)

    @property
    def ok(self) -> bool:
        return not self.missing


def check_tools(tools: Iterable[str]) -> PreflightReport:
    """Résout chaque outil via ``shutil.which`` (portable Windows/Linux/macOS)."""
    return PreflightReport(available={tool: shutil.which(tool) is not None for tool in tools})


def preflight_message(report: PreflightReport) -> str:
    """Message actionnable pour l'opérateur."""
    if report.ok:
        return "Préflight OK : tous les outils requis sont disponibles."
    return (
        "Préflight KO — outils introuvables dans le PATH : "
        + ", ".join(report.missing)
        + ". Installe-les (ou ajuste le PATH) avant de lancer le run."
    )
