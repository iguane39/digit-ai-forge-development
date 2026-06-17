"""Étape C : planification + HITL 1 (la chaîne se met en pause sans approbation)."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.bmad_bridge import lancer_planification
from conductor.contracts import BmadPlan, ScaffoldResult
from conductor.governance import HitlPending


class FakePlanner:
    def plan(self, scaffold: ScaffoldResult) -> BmadPlan:
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


def _scaffold(tmp: Path) -> ScaffoldResult:
    return ScaffoldResult(repo_path=tmp, ci_harness_ready=True, design_md_path=tmp / "DESIGN.md")


def test_hitl1_approval_marks_plan_approved(tmp_path: Path) -> None:
    plan = lancer_planification(_scaffold(tmp_path), planner=FakePlanner(), gate=ApproveGate())
    assert plan.hitl1_approved is True


def test_hitl1_rejection_pauses_chain(tmp_path: Path) -> None:
    with pytest.raises(HitlPending, match="HITL 1"):
        lancer_planification(_scaffold(tmp_path), planner=FakePlanner(), gate=RejectGate())


def test_default_gate_pauses_without_human(tmp_path: Path) -> None:
    """Défaut ManualGate : pas d'approbation auto → pause (gouvernance, décision 07)."""
    with pytest.raises(HitlPending):
        lancer_planification(_scaffold(tmp_path), planner=FakePlanner())
