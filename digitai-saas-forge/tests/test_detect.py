"""Détection de la distance à la cible : A (déjà conforme) vs C (à normaliser)."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.cadrage import cadrer
from conductor.onramp import select_onramp
from conductor.onramp.adapter_onramp import AdapterOnramp
from conductor.onramp.detect import detect_distance
from conductor.onramp.no_onramp import NoOnramp


def _fastapi_repo(tmp: Path, *, with_design: bool, with_ci: bool) -> Path:
    (tmp / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    if with_design:
        (tmp / "design").mkdir(parents=True, exist_ok=True)
        (tmp / "design" / "DESIGN.md").write_text("# DESIGN\n", encoding="utf-8")
    if with_ci:
        (tmp / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
        (tmp / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    return tmp


def test_complete_target_repo_is_distance_a(tmp_path: Path) -> None:
    repo = _fastapi_repo(tmp_path, with_design=True, with_ci=True)
    assert detect_distance(repo) == "A"


def test_fastapi_missing_design_is_distance_c(tmp_path: Path) -> None:
    repo = _fastapi_repo(tmp_path, with_design=False, with_ci=True)
    assert detect_distance(repo) == "C"


def test_non_fastapi_repo_raises_for_bb(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="BB"):
        detect_distance(tmp_path)


def test_select_onramp_routes_distance_a_to_no_onramp(tmp_path: Path) -> None:
    _fastapi_repo(tmp_path, with_design=True, with_ci=True)
    mission = cadrer("i", mode="brownfield", existing_repo=tmp_path)
    assert isinstance(select_onramp(mission), NoOnramp)


def test_select_onramp_routes_distance_c_to_adapter(tmp_path: Path) -> None:
    _fastapi_repo(tmp_path, with_design=False, with_ci=True)
    mission = cadrer("i", mode="brownfield", existing_repo=tmp_path)
    assert isinstance(select_onramp(mission), AdapterOnramp)
