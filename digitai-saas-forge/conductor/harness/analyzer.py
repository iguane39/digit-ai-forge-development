"""ClaudeSubagentAnalyzer — ingestion hybride : faits heuristiques + interprétation sous-agent.

Implémente le protocole `Analyzer`. Les faits durs viennent de HeuristicAnalyzer (déterministes) ;
l'interprétation (résumé/conventions/dette) vient d'un sous-agent via le CLI `claude`. En cas
d'échec d'interprétation (erreur runner ou JSON invalide), on retombe sur les faits seuls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from conductor.harness.claude_cli import CliRunner, SubprocessClaudeCli
from conductor.onramp.analyzer import HeuristicAnalyzer

_PROMPT = (
    "Analyse le dépôt courant. Réponds UNIQUEMENT par un objet JSON avec les clés : "
    '"summary" (string), "conventions" (liste de strings), "debt" (liste de strings). '
    "Aucun texte hors du JSON."
)


class ClaudeSubagentAnalyzer:
    """Analyzer hybride : HeuristicAnalyzer (faits) + sous-agent claude (interprétation)."""

    def __init__(self, *, runner: CliRunner | None = None) -> None:
        self._runner: CliRunner = runner or SubprocessClaudeCli()
        self._heuristic = HeuristicAnalyzer()

    def analyze(self, repo_path: Path) -> dict[str, Any]:
        facts = self._heuristic.analyze(repo_path)
        try:
            raw = self._runner.run(_PROMPT, repo_path)
            interpretation = json.loads(raw)
            if not isinstance(interpretation, dict):
                raise ValueError("interprétation non-objet")
        except (RuntimeError, ValueError, json.JSONDecodeError):
            return {**facts, "interpretation": "indisponible"}
        return {**facts, **interpretation}
