"""Bout-en-bout BC : repo FastAPI externe sans DESIGN.md → AdapterOnramp normalise →
baseline → remédiation → D → E, rien n'est mergé."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from conductor.cadrage import cadrer
from conductor.contracts import GateVerdict, StoryOutcome
from conductor.onramp import select_onramp
from conductor.onramp.adapter_onramp import AdapterOnramp
from conductor.planners.remediation import RemediationPlanner
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


def test_bc_external_repo_normalized_end_to_end(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    mission = cadrer("compléter le SaaS", mode="brownfield", existing_repo=tmp_path)
    assert isinstance(select_onramp(mission), AdapterOnramp)

    substrate = AdapterOnramp(code_runner=_CodeRunner(0), design_linter=_Linter()).prepare(
        mission, tmp_path
    )
    assert (tmp_path / "design" / "DESIGN.md").exists()
    assert substrate.declared_degradation

    plan = RemediationPlanner().plan(substrate)
    plan = plan.model_copy(update={"hitl1_approved": True})
    layout = preparer_sprint(plan, tmp_path, baseline=substrate.baseline)

    bad = _FakeBad([StoryOutcome(story_id="C1", code_ok=True, pr_url="pr/C1")])
    report = superviser(layout, bad=bad, design_check=_design_pass, hitl=_ApproveGate())
    assert report.merged is False
