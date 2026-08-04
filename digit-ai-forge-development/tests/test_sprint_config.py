"""Étape D : place le backlog + écrit la config bad: (I/O réel)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from conductor.contracts import BmadPlan, Story
from conductor.sprint_config import preparer_sprint


def _plan(approved: bool, stories: list[Story] | None = None) -> BmadPlan:
    return BmadPlan(
        prd_path=Path("PRD.md"),
        architecture_path=Path("architecture.md"),
        epics_md=Path("_bmad-output/planning-artifacts/epics.md"),
        stories=stories or [],
        hitl1_approved=approved,
    )


def test_requires_hitl1(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="HITL 1"):
        preparer_sprint(_plan(approved=False), tmp_path)


def test_writes_config_and_status(tmp_path: Path) -> None:
    plan = _plan(approved=True, stories=[Story(id="1.1", epic="1", title="x")])
    layout = preparer_sprint(plan, tmp_path)

    cfg = yaml.safe_load(layout.bmad_config_yaml.read_text(encoding="utf-8"))
    assert cfg["bad"]["auto_pr_merge"] is False  # HITL 2 garanti (décision 07)
    assert cfg["bad"]["max_parallel_stories"] == 3

    status = yaml.safe_load(layout.sprint_status_yaml.read_text(encoding="utf-8"))
    assert status["stories"]["1.1"] == "ready-for-dev"


def test_layout_points_to_bad_expected_paths(tmp_path: Path) -> None:
    layout = preparer_sprint(_plan(approved=True), tmp_path)
    assert layout.bmad_config_yaml == tmp_path / "_bmad/config.yaml"
    tail = layout.sprint_status_yaml.parts[-2:]
    assert tail == ("implementation-artifacts", "sprint-status.yaml")


def test_baseline_is_carried_into_layout(tmp_path: Path) -> None:
    plan = _plan(approved=True)
    layout = preparer_sprint(plan, tmp_path, baseline={"code": True, "design": False})
    assert layout.baseline == {"code": True, "design": False}


def test_baseline_defaults_to_none(tmp_path: Path) -> None:
    layout = preparer_sprint(_plan(approved=True), tmp_path)
    assert layout.baseline is None
