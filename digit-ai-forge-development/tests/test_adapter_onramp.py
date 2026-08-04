"""AdapterOnramp (branche C) : normalise un repo FastAPI incomplet vers le contrat cible."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from conductor.cadrage import cadrer
from conductor.onramp.adapter_onramp import AdapterOnramp
from conductor.profiles import FASTAPI_SAAS


class _CodeRunner:
    def __init__(self, rc: int) -> None:
        self.rc = rc

    def run(self, command: str, cwd: Path) -> int:
        return self.rc


class _Linter:
    def lint_json(self, design_md: Path) -> dict[str, Any]:
        return {"findings": []}


def _repo(tmp: Path) -> Path:
    (tmp / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    return tmp


def _onramp() -> AdapterOnramp:
    return AdapterOnramp(code_runner=_CodeRunner(0), design_linter=_Linter())


def test_adapter_creates_missing_design_md(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    substrate = _onramp().prepare(cadrer("i", mode="brownfield", existing_repo=repo), repo)
    assert (repo / "design" / "DESIGN.md").exists()
    assert any("DESIGN.md" in note for note in substrate.declared_degradation)


def test_adapter_captures_baseline_and_archmap(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    substrate = _onramp().prepare(cadrer("i", mode="brownfield", existing_repo=repo), repo)
    assert substrate.profile is FASTAPI_SAAS
    assert substrate.baseline == {"code": True, "design": True}
    assert substrate.arch_map is not None and substrate.arch_map["has_pyproject"] is True


def test_adapter_declares_missing_ci(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    substrate = _onramp().prepare(cadrer("i", mode="brownfield", existing_repo=repo), repo)
    assert any("CI" in note for note in substrate.declared_degradation)


def test_adapter_requires_pyproject(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="BB"):
        _onramp().prepare(cadrer("i", mode="brownfield", existing_repo=tmp_path), tmp_path)
