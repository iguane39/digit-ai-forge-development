"""Bout-en-bout BB : repo node-ts → BuilderOnramp (profil synthétisé, dégradation déclarée) →
baseline (npm test) → remédiation → D → E, rien n'est mergé ; HITL-0 forcé (dégradation)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from conductor.cadrage import cadrer
from conductor.contracts import GateVerdict, StoryOutcome
from conductor.governance import HitlPending, require_hitl0
from conductor.onramp import select_onramp
from conductor.onramp.builder_onramp import BuilderOnramp
from conductor.planners.remediation import RemediationPlanner
from conductor.profiles import NODE_TS
from conductor.sprint_config import preparer_sprint
from conductor.supervisor import superviser


class _CodeRunner:
    def __init__(self, rc: int) -> None:
        self.rc = rc

    def run(self, command: str, cwd: Path) -> int:
        return self.rc


class _Linter:
    def lint_json(self, design_md: Path) -> dict[str, Any]:
        return {"findings": []}


class _FakeBad:
    def __init__(self, outcomes: list[StoryOutcome]) -> None:
        self._outcomes = outcomes

    def run_sprint(self, layout: object) -> list[StoryOutcome]:
        return self._outcomes

    def remediate(self, story_id: str, layout: object) -> StoryOutcome:
        return StoryOutcome(story_id=story_id, code_ok=True, pr_url=f"pr/{story_id}")


def _design_pass(_o: StoryOutcome) -> GateVerdict:
    return GateVerdict(gate="design", passed=True)


class _ApproveGate:
    def approve(self, checkpoint: str, payload: object) -> bool:
        return True


def test_bb_node_ts_end_to_end(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    mission = cadrer("assainir le SaaS node", mode="brownfield", existing_repo=tmp_path)
    assert isinstance(select_onramp(mission), BuilderOnramp)

    substrate = BuilderOnramp(code_runner=_CodeRunner(0), design_linter=_Linter()).prepare(
        mission, tmp_path
    )
    assert substrate.profile is NODE_TS
    assert substrate.declared_degradation

    with pytest.raises(HitlPending):
        require_hitl0("normalisation", substrate)  # HITL-0 forcé (dégradation déclarée)

    plan = RemediationPlanner().plan(substrate).model_copy(update={"hitl1_approved": True})
    layout = preparer_sprint(plan, tmp_path, baseline=substrate.baseline)
    bad = _FakeBad([StoryOutcome(story_id="B1", code_ok=True, pr_url="pr/B1")])
    report = superviser(layout, bad=bad, design_check=_design_pass, hitl=_ApproveGate())
    assert report.merged is False
