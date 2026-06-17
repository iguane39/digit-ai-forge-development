"""Ingestion hybride — carte d'archi d'un repo existant.

HeuristicAnalyzer : faits durs déterministes (structure top-level, présence pyproject) —
testable hors-ligne, base de la carte. SubagentAnalyzer : interprétation par un sous-agent
Claude Code (dette, conventions) — nécessite le harness ; stub ici (branché en production).
Décision spec : BC = ingestion hybride (faits heuristiques + interprétation agent).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class Analyzer(Protocol):
    def analyze(self, repo_path: Path) -> dict[str, Any]: ...


class HeuristicAnalyzer:
    """Faits durs : structure de premier niveau + marqueurs. Déterministe."""

    def analyze(self, repo_path: Path) -> dict[str, Any]:
        top_level = sorted(p.name for p in repo_path.iterdir()) if repo_path.is_dir() else []
        return {
            "top_level": top_level,
            "has_pyproject": (repo_path / "pyproject.toml").exists(),
            "has_frontend": (repo_path / "frontend").is_dir(),
        }


class SubagentAnalyzer:
    """Interprétation par un sous-agent Claude Code (carte enrichie, dette).

    Nécessite le harness Claude Code ; point d'intégration matérialisé (cf. DefaultBadRunner).
    """

    def analyze(self, repo_path: Path) -> dict[str, Any]:
        raise NotImplementedError(
            "SubagentAnalyzer nécessite le harness Claude Code (ingestion par sous-agent). "
            "Utiliser HeuristicAnalyzer hors harness."
        )
