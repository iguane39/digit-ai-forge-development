"""BuilderOnramp (branche B, B-standard) : hisse une stack non-FastAPI au contrat cible."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from conductor.cadrage import cadrer
from conductor.onramp.builder_onramp import BuilderOnramp
from conductor.profiles import NODE_TS


class _CodeRunner:
    def __init__(self, rc: int) -> None:
        self.rc = rc

    def run(self, command: str, cwd: Path) -> int:
        return self.rc


class _Linter:
    def lint_json(self, design_md: Path) -> dict[str, Any]:
        return {"findings": []}


def _node_repo(tmp: Path) -> Path:
    (tmp / "package.json").write_text("{}", encoding="utf-8")
    return tmp


def _onramp() -> BuilderOnramp:
    return BuilderOnramp(code_runner=_CodeRunner(0), design_linter=_Linter())


def test_builder_resolves_node_profile_and_declares_degradation(tmp_path: Path) -> None:
    repo = _node_repo(tmp_path)
    substrate = _onramp().prepare(cadrer("i", mode="brownfield", existing_repo=repo), repo)
    assert substrate.profile is NODE_TS
    assert substrate.declared_degradation


def test_builder_creates_missing_design_md(tmp_path: Path) -> None:
    repo = _node_repo(tmp_path)
    _onramp().prepare(cadrer("i", mode="brownfield", existing_repo=repo), repo)
    assert (repo / "design" / "DESIGN.md").exists()


def test_builder_captures_baseline_with_node_code_check(tmp_path: Path) -> None:
    repo = _node_repo(tmp_path)
    captured: list[str] = []

    class _Rec:
        def run(self, command: str, cwd: Path) -> int:
            captured.append(command)
            return 0

    substrate = BuilderOnramp(code_runner=_Rec(), design_linter=_Linter()).prepare(
        cadrer("i", mode="brownfield", existing_repo=repo), repo
    )
    assert substrate.baseline == {"code": True, "design": True}
    assert captured == ["npm test"]


def test_builder_rejects_unknown_stack(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="non gérée|unsupported|stack"):
        _onramp().prepare(cadrer("i", mode="brownfield", existing_repo=tmp_path), tmp_path)
