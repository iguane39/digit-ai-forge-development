"""Planners brownfield : remédiation déterministe depuis la baseline (v1 tests/CI + design)."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.contracts import BmadPlan
from conductor.onramp.base import Substrate
from conductor.planners import ComplementPlanner, CompositePlanner
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


def test_remediation_code_check_derived_from_profile(tmp_path: Path) -> None:
    # La story R1 cite la commande du profil (node-ts → npm test), pas ruff/mypy/pytest en dur.
    from conductor.profiles import NODE_TS

    (tmp_path / "design").mkdir(parents=True, exist_ok=True)
    substrate = Substrate(
        repo_path=tmp_path,
        profile=NODE_TS,
        design_md_path=tmp_path / "design/DESIGN.md",
        baseline={"code": False, "design": True},
    )
    plan = RemediationPlanner().plan(substrate)
    accept = " ".join(a for s in plan.stories for a in (s.acceptance or []))
    assert "npm test" in accept
    assert "pytest" not in accept


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


class _StubPlanner:
    def __init__(self, plan: BmadPlan) -> None:
        self._plan = plan

    def plan(self, substrate: Substrate) -> BmadPlan:
        return self._plan


def test_complement_delegates_to_inner(tmp_path: Path) -> None:
    inner_plan = BmadPlan(
        prd_path=tmp_path / "PRD.md",
        architecture_path=tmp_path / "arch.md",
        epics_md=tmp_path / "epics.md",
    )
    planner = ComplementPlanner(inner=_StubPlanner(inner_plan))
    assert planner.plan(_substrate(tmp_path, {})) is inner_plan


def test_complement_default_inner_resolves_lazily(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # inner=None → résolu à l'appel via resolve_bmad_planner (chemin par défaut).
    from conductor.harness import resolve as resolve_mod

    sentinel = BmadPlan(
        prd_path=tmp_path / "PRD.md",
        architecture_path=tmp_path / "a.md",
        epics_md=tmp_path / "e.md",
    )
    monkeypatch.setattr(resolve_mod, "resolve_bmad_planner", lambda: _StubPlanner(sentinel))
    assert ComplementPlanner().plan(_substrate(tmp_path, {})) is sentinel


def test_composite_concatenates_stories(tmp_path: Path) -> None:
    from conductor.contracts import Story

    p1 = BmadPlan(
        prd_path=tmp_path / "PRD.md",
        architecture_path=tmp_path / "a.md",
        epics_md=tmp_path / "e1.md",
        stories=[Story(id="R1", epic="remediation", title="fix")],
    )
    p2 = BmadPlan(
        prd_path=tmp_path / "PRD.md",
        architecture_path=tmp_path / "a.md",
        epics_md=tmp_path / "e2.md",
        stories=[Story(id="C1", epic="complement", title="feature")],
    )
    composite = CompositePlanner(_StubPlanner(p1), _StubPlanner(p2))
    out = composite.plan(_substrate(tmp_path, {}))
    assert [s.id for s in out.stories] == ["R1", "C1"]
    assert out.epics_md == p1.epics_md


def test_composite_writes_merged_epics_on_disk(tmp_path: Path) -> None:
    a_file = tmp_path / "a_epics.md"
    a_file.write_text("# Remediation\n- R1\n", encoding="utf-8")
    b_file = tmp_path / "b_epics.md"
    b_file.write_text("# Complement\n- C1\n", encoding="utf-8")
    pa = BmadPlan(prd_path=tmp_path / "p", architecture_path=tmp_path / "ar", epics_md=a_file)
    pb = BmadPlan(prd_path=tmp_path / "p", architecture_path=tmp_path / "ar", epics_md=b_file)
    out = CompositePlanner(_StubPlanner(pa), _StubPlanner(pb)).plan(_substrate(tmp_path, {}))
    merged = out.epics_md.read_text(encoding="utf-8")
    assert "Remediation" in merged and "Complement" in merged


class _WritingStubPlanner:
    """Planner qui ÉCRIT son contenu sur le chemin epics_md au moment du plan (cas intent=both)."""

    def __init__(self, epics_md: Path, content: str) -> None:
        self._epics_md = epics_md
        self._content = content

    def plan(self, substrate: Substrate) -> BmadPlan:
        self._epics_md.write_text(self._content, encoding="utf-8")
        return BmadPlan(
            prd_path=self._epics_md.parent / "p",
            architecture_path=self._epics_md.parent / "ar",
            epics_md=self._epics_md,
        )


def test_composite_same_path_reads_first_before_second_overwrites(tmp_path: Path) -> None:
    """intent=both : le 2ᵉ planner écrit sur le MÊME epics.md ; on lit le 1ᵉʳ AVANT l'écrasement."""
    shared = tmp_path / "epics.md"
    shared.write_text("# Remediation\n- R1\n", encoding="utf-8")  # contenu du 1ᵉʳ planner
    pa = BmadPlan(prd_path=tmp_path / "p", architecture_path=tmp_path / "ar", epics_md=shared)
    second = _WritingStubPlanner(shared, "# Complement\n- C1\n")  # écrase shared au plan
    out = CompositePlanner(_StubPlanner(pa), second).plan(_substrate(tmp_path, {}))
    merged = out.epics_md.read_text(encoding="utf-8")
    assert "Remediation" in merged and "Complement" in merged  # union malgré le même chemin
