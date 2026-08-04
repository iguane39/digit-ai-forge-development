"""Étape C : planification + HITL 1 (la chaîne se met en pause sans approbation)."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.bmad_bridge import lancer_planification
from conductor.contracts import BmadPlan
from conductor.governance import HitlPending
from conductor.onramp.base import Substrate
from conductor.profiles import FASTAPI_SAAS


class FakePlanner:
    def plan(self, substrate: Substrate) -> BmadPlan:
        return BmadPlan(
            prd_path=Path("PRD.md"),
            architecture_path=Path("architecture.md"),
            epics_md=Path("_bmad-output/planning-artifacts/epics.md"),
        )


class ApproveGate:
    def approve(self, checkpoint: str, payload: object) -> bool:
        return True


class RejectGate:
    def approve(self, checkpoint: str, payload: object) -> bool:
        return False


def _substrate(tmp: Path) -> Substrate:
    return Substrate(repo_path=tmp, profile=FASTAPI_SAAS, design_md_path=tmp / "DESIGN.md")


def test_default_planner_pauses_without_install(tmp_path: Path) -> None:
    """B-11 : le planner par défaut n'installe rien (TUI) et pause HITL 1 si artefacts absents."""
    from conductor.bmad_bridge import DefaultBmadPlanner

    with pytest.raises(HitlPending, match="format BMAD|installe pas"):
        DefaultBmadPlanner().plan(_substrate(tmp_path))


def test_default_planner_collects_existing_artifacts(tmp_path: Path) -> None:
    """Artefacts présents → BmadPlan, sans tentative d'install."""
    from conductor.bmad_bridge import EPICS_FILE, DefaultBmadPlanner

    epics = tmp_path / EPICS_FILE
    epics.parent.mkdir(parents=True)
    epics.write_text("# Epics\n", encoding="utf-8")
    plan = DefaultBmadPlanner().plan(_substrate(tmp_path))
    assert plan.epics_md == epics


def test_hitl1_approval_marks_plan_approved(tmp_path: Path) -> None:
    plan = lancer_planification(_substrate(tmp_path), planner=FakePlanner(), gate=ApproveGate())
    assert plan.hitl1_approved is True


def test_hitl1_rejection_pauses_chain(tmp_path: Path) -> None:
    with pytest.raises(HitlPending, match="HITL 1"):
        lancer_planification(_substrate(tmp_path), planner=FakePlanner(), gate=RejectGate())


def test_default_gate_pauses_without_human(tmp_path: Path) -> None:
    """Défaut ManualGate : pas d'approbation auto → pause (gouvernance, décision 07)."""
    with pytest.raises(HitlPending):
        lancer_planification(_substrate(tmp_path), planner=FakePlanner())


def test_lancer_planification_uses_resolver_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from conductor.harness import resolve as resolve_mod

    sentinel = BmadPlan(
        prd_path=Path("PRD.md"), architecture_path=Path("a.md"), epics_md=Path("e.md")
    )

    class _Resolved:
        def plan(self, substrate: Substrate) -> BmadPlan:
            return sentinel

    monkeypatch.setattr(resolve_mod, "resolve_bmad_planner", lambda: _Resolved())
    plan = lancer_planification(_substrate(tmp_path), gate=ApproveGate())
    assert plan.hitl1_approved is True  # est passé par _Resolved + HITL 1 approuvé
