"""Sélecteur d'Analyzer : sous-agent réel (opt-in) ou heuristique déterministe (défaut)."""

from __future__ import annotations

import os
import shutil

from conductor.harness.analyzer import ClaudeSubagentAnalyzer
from conductor.onramp.analyzer import Analyzer, HeuristicAnalyzer


def resolve_analyzer() -> Analyzer:
    """Réel si CONDUCTOR_USE_CLAUDE_ANALYZER=1 ET `claude` présent ; sinon heuristique."""
    use_claude = os.environ.get("CONDUCTOR_USE_CLAUDE_ANALYZER") == "1"
    if use_claude and shutil.which("claude") is not None:
        return ClaudeSubagentAnalyzer()
    return HeuristicAnalyzer()
