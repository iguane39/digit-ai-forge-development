"""Planners brownfield : remédiation déterministe depuis la baseline (v1 tests/CI + design)."""

from __future__ import annotations

from pathlib import Path

from conductor.onramp.base import Substrate
from conductor.planners.remediation import RemediationPlanner
from conductor.profiles import FASTAPI_SAAS


def _substrate(tmp: Path, baseline: dict[str, bool]) -> Substrate:
    (tmp / "design").mkdir(parents=True, exist_ok=True)
    return Substrate(
        repo_path=tmp,
        profile=FASTAPI_SAAS,
        design_md_path=tmp / "design/DESIGN.md",
        baseline=baseline,
    )


def test_remediation_emits_story_for_red_code(tmp_path: Path) -> None:
    plan = RemediationPlanner().plan(_substrate(tmp_path, {"code": False, "design": True}))
    titles = [s.title for s in plan.stories]
    assert any("CI code" in t for t in titles)
    assert all("design" not in t.lower() for t in titles)


def test_remediation_emits_story_for_red_design(tmp_path: Path) -> None:
    plan = RemediationPlanner().plan(_substrate(tmp_path, {"code": True, "design": False}))
    assert any("design" in s.title.lower() for s in plan.stories)


def test_remediation_all_green_yields_no_story(tmp_path: Path) -> None:
    plan = RemediationPlanner().plan(_substrate(tmp_path, {"code": True, "design": True}))
    assert plan.stories == []


def test_remediation_writes_epics_md(tmp_path: Path) -> None:
    plan = RemediationPlanner().plan(_substrate(tmp_path, {"code": False, "design": False}))
    assert plan.epics_md.exists()
    content = plan.epics_md.read_text(encoding="utf-8")
    assert "remediation" in content.lower()
    assert plan.hitl1_approved is False
