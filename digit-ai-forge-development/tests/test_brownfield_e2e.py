"""Bout-en-bout brownfield (branche A) : NoOnramp → remédiation → D → E avec fakes.

Vérifie : reprise d'un repo cible, baseline capturée, backlog de remédiation, gate de
non-régression effectif, HITL 2 non franchi par défaut (rien n'est mergé)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from conductor.cadrage import cadrer
from conductor.contracts import GateVerdict, StoryOutcome
from conductor.onramp import select_onramp
from conductor.onramp.no_onramp import NoOnramp
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


def test_brownfield_remediation_end_to_end(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "design").mkdir(parents=True, exist_ok=True)
    (tmp_path / "design" / "DESIGN.md").write_text("# DESIGN\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    mission = cadrer(
        "assainir le CRM", mode="brownfield", existing_repo=tmp_path, intent="remediation"
    )

    assert isinstance(select_onramp(mission), NoOnramp)
    substrate = NoOnramp(code_runner=_CodeRunner(1), design_linter=_Linter()).prepare(
        mission, tmp_path
    )
    assert substrate.baseline == {"code": False, "design": True}

    plan = RemediationPlanner().plan(substrate)
    assert any("CI code" in s.title for s in plan.stories)
    plan = plan.model_copy(update={"hitl1_approved": True})

    layout = preparer_sprint(plan, tmp_path, baseline=substrate.baseline)
    assert layout.baseline == {"code": False, "design": True}

    bad = _FakeBad([StoryOutcome(story_id="R1", code_ok=True, pr_url="pr/R1")])
    report = superviser(layout, bad=bad, design_check=_design_pass, hitl=_ApproveGate())
    assert report.results[0].status == "ready-for-review"
    assert report.merged is False
