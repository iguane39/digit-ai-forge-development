"""Intégration RÉELLE de l'analyzer sous-agent — GATED.

Sauté sauf RUN_CLAUDE_INTEGRATION=1 ET CLI `claude` présent. Sert de mode d'emploi exécutable
du run pilote ; ne tourne jamais en CI standard (réseau/auth/tokens)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_CLAUDE_INTEGRATION") != "1" or shutil.which("claude") is None,
    reason="intégration claude désactivée (RUN_CLAUDE_INTEGRATION!=1 ou claude absent)",
)


def test_real_claude_analyzer_on_fixture(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='pilot'\n", encoding="utf-8")
    (tmp_path / "backend").mkdir()
    from conductor.harness.analyzer import ClaudeSubagentAnalyzer

    arch = ClaudeSubagentAnalyzer().analyze(tmp_path)
    assert arch["has_pyproject"] is True
    assert "summary" in arch or arch.get("interpretation") == "indisponible"
