"""Sélecteur d'Analyzer : sous-agent réel (opt-in) ou heuristique déterministe (défaut)."""

from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING

from conductor.harness.analyzer import ClaudeSubagentAnalyzer
from conductor.onramp.analyzer import Analyzer, HeuristicAnalyzer

if TYPE_CHECKING:
    from conductor.supervisor import BadRunner


def resolve_analyzer() -> Analyzer:
    """Réel si CONDUCTOR_USE_CLAUDE_ANALYZER=1 ET `claude` présent ; sinon heuristique."""
    use_claude = os.environ.get("CONDUCTOR_USE_CLAUDE_ANALYZER") == "1"
    if use_claude and shutil.which("claude") is not None:
        return ClaudeSubagentAnalyzer()
    return HeuristicAnalyzer()


def resolve_bad_runner() -> BadRunner:
    """ClaudeCliBadRunner si CONDUCTOR_ENABLE_REAL_BAD=1 ET `claude`+`gh` présents ; sinon stub."""
    from conductor.harness.bad_runner import ClaudeCliBadRunner
    from conductor.supervisor import DefaultBadRunner

    enabled = os.environ.get("CONDUCTOR_ENABLE_REAL_BAD") == "1"
    tools = shutil.which("claude") is not None and shutil.which("gh") is not None
    if enabled and tools:
        return ClaudeCliBadRunner()
    return DefaultBadRunner()
