"""ClaudeSubagentAnalyzer : fusionne faits heuristiques + interprétation agent ; fallback gracieux."""  # noqa: E501

from __future__ import annotations

import json
from pathlib import Path

from conductor.harness.analyzer import ClaudeSubagentAnalyzer


class _FakeRunner:
    def __init__(self, output: str, *, boom: bool = False) -> None:
        self._output = output
        self._boom = boom

    def run(self, prompt: str, cwd: Path) -> str:
        if self._boom:
            raise RuntimeError("claude indisponible")
        return self._output


def _repo(tmp: Path) -> Path:
    (tmp / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp / "backend").mkdir()
    return tmp


def test_merges_facts_and_interpretation(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    payload = json.dumps({"summary": "API FastAPI", "conventions": ["ruff"], "debt": []})
    arch = ClaudeSubagentAnalyzer(runner=_FakeRunner(payload)).analyze(repo)
    assert arch["has_pyproject"] is True
    assert arch["summary"] == "API FastAPI"
    assert arch["conventions"] == ["ruff"]


def test_fallback_on_non_json(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    arch = ClaudeSubagentAnalyzer(runner=_FakeRunner("blabla pas json")).analyze(repo)
    assert arch["has_pyproject"] is True
    assert arch["interpretation"] == "indisponible"


def test_fallback_on_runner_error(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    arch = ClaudeSubagentAnalyzer(runner=_FakeRunner("", boom=True)).analyze(repo)
    assert arch["interpretation"] == "indisponible"
    assert "top_level" in arch
