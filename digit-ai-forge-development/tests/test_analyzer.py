"""Ingestion : carte d'archi. HeuristicAnalyzer (faits durs) ; SubagentAnalyzer = harness."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.onramp.analyzer import HeuristicAnalyzer, SubagentAnalyzer


def test_heuristic_analyzer_lists_top_level(tmp_path: Path) -> None:
    (tmp_path / "backend").mkdir()
    (tmp_path / "frontend").mkdir()
    (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
    arch = HeuristicAnalyzer().analyze(tmp_path)
    assert "backend" in arch["top_level"]
    assert "frontend" in arch["top_level"]
    assert arch["has_pyproject"] is True


def test_subagent_analyzer_requires_harness(tmp_path: Path) -> None:
    with pytest.raises(NotImplementedError, match="harness"):
        SubagentAnalyzer().analyze(tmp_path)


def test_heuristic_analyzer_caps_top_level(tmp_path: Path) -> None:
    for i in range(250):
        (tmp_path / f"f{i:03d}.txt").write_text("x", encoding="utf-8")
    arch = HeuristicAnalyzer().analyze(tmp_path)
    assert len(arch["top_level"]) == 200
    assert arch["top_level_truncated"] is True


def test_heuristic_analyzer_not_truncated_for_small_repo(tmp_path: Path) -> None:
    (tmp_path / "backend").mkdir()
    arch = HeuristicAnalyzer().analyze(tmp_path)
    assert arch["top_level_truncated"] is False
