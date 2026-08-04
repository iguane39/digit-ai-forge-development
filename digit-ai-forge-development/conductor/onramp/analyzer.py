"""Ingestion hybride — carte d'archi d'un repo existant.

HeuristicAnalyzer : faits durs déterministes (structure top-level, présence pyproject) —
testable hors-ligne, base de la carte. Le scan top-level est borné à _MAX_TOP_LEVEL entrées ;
au-delà, ``top_level_truncated`` vaut True. SubagentAnalyzer : interprétation par un sous-agent
Claude Code (dette, conventions) — nécessite le harness ; stub ici (branché en production).
Décision spec : BC = ingestion hybride (faits heuristiques + interprétation agent).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

_MAX_TOP_LEVEL = 200


class Analyzer(Protocol):
    def analyze(self, repo_path: Path) -> dict[str, Any]: ...


class HeuristicAnalyzer:
    """Faits durs : structure de premier niveau + marqueurs. Déterministe.

    Le nombre d'entrées top-level retournées est borné à _MAX_TOP_LEVEL (200).
    Si le répertoire contient davantage d'entrées, ``top_level_truncated`` vaut True.
    """

    def analyze(self, repo_path: Path) -> dict[str, Any]:
        names = sorted(p.name for p in repo_path.iterdir()) if repo_path.is_dir() else []
        truncated = len(names) > _MAX_TOP_LEVEL
        return {
            "top_level": names[:_MAX_TOP_LEVEL],
            "top_level_truncated": truncated,
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
