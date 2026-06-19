"""NoOnramp (branche A) : vérifie les marqueurs cible + capture une baseline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from conductor.cadrage import cadrer
from conductor.onramp import select_onramp
from conductor.onramp.no_onramp import NoOnramp, capture_baseline
from conductor.profiles import FASTAPI_SAAS


class _CodeRunner:
    def __init__(self, rc: int) -> None:
        self.rc = rc

    def run(self, command: str, cwd: Path) -> int:
        return self.rc


class _Linter:
    def __init__(self, report: dict[str, Any]) -> None:
        self.report = report

    def lint_json(self, design_md: Path) -> dict[str, Any]:
        return self.report


def test_capture_baseline_records_green_checks(tmp_path: Path) -> None:
    baseline = capture_baseline(
        tmp_path, FASTAPI_SAAS, code_runner=_CodeRunner(0), design_linter=_Linter({"findings": []})
    )
    assert baseline == {"code": True, "design": True}


def test_capture_baseline_marks_failing_code(tmp_path: Path) -> None:
    baseline = capture_baseline(
        tmp_path, FASTAPI_SAAS, code_runner=_CodeRunner(1), design_linter=_Linter({"findings": []})
    )
    assert baseline["code"] is False


def test_no_onramp_requires_target_markers(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="marqueurs"):
        NoOnramp().prepare(cadrer("idée", mode="brownfield", existing_repo=tmp_path), tmp_path)


def test_no_onramp_returns_substrate_with_baseline(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    onramp = NoOnramp(code_runner=_CodeRunner(0), design_linter=_Linter({"findings": []}))
    substrate = onramp.prepare(cadrer("idée", mode="brownfield", existing_repo=tmp_path), tmp_path)
    assert substrate.repo_path == tmp_path
    assert substrate.profile is FASTAPI_SAAS
    assert substrate.baseline == {"code": True, "design": True}


def test_no_onramp_red_baseline_is_declared(tmp_path: Path) -> None:
    """Do-no-harm : un gate rouge à l'entrée est signalé (declared_degradation), pas avalé."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    onramp = NoOnramp(code_runner=_CodeRunner(1), design_linter=_Linter({"findings": []}))
    substrate = onramp.prepare(cadrer("idée", mode="brownfield", existing_repo=tmp_path), tmp_path)
    assert substrate.baseline == {"code": False, "design": True}
    assert any("code" in note and "rouge" in note for note in substrate.declared_degradation)


def test_no_onramp_green_baseline_no_degradation(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    onramp = NoOnramp(code_runner=_CodeRunner(0), design_linter=_Linter({"findings": []}))
    substrate = onramp.prepare(cadrer("idée", mode="brownfield", existing_repo=tmp_path), tmp_path)
    assert substrate.declared_degradation == []


def test_select_onramp_brownfield_is_no_onramp(tmp_path: Path) -> None:
    """Un repo distance A (pyproject + DESIGN.md + CI) → NoOnramp."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "design").mkdir(parents=True, exist_ok=True)
    (tmp_path / "design" / "DESIGN.md").write_text("# DESIGN\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    mission = cadrer("idée", mode="brownfield", existing_repo=tmp_path)
    assert isinstance(select_onramp(mission), NoOnramp)
