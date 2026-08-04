"""Étape E : double gate par story, 3 retries puis escalade (DE-3), HITL 2, jamais de merge."""

from __future__ import annotations

from pathlib import Path

from conductor.contracts import BadSprintLayout, GateVerdict, StoryOutcome
from conductor.supervisor import superviser


def _layout(tmp: Path) -> BadSprintLayout:
    return BadSprintLayout(
        project_root=tmp,
        epics_md=tmp / "_bmad-output/planning-artifacts/epics.md",
        sprint_status_yaml=tmp / "_bmad-output/implementation-artifacts/sprint-status.yaml",
        bmad_config_yaml=tmp / "_bmad/config.yaml",
    )


class FakeBad:
    """Développe des stories ; `flaky` échoue au gate code jusqu'à un certain essai."""

    def __init__(self, outcomes: list[StoryOutcome], heal_after: int | None = None) -> None:
        self._outcomes = outcomes
        self.heal_after = heal_after
        self.remediations: dict[str, int] = {}

    def run_sprint(self, layout: BadSprintLayout) -> list[StoryOutcome]:
        return self._outcomes

    def remediate(self, story_id: str, layout: BadSprintLayout) -> StoryOutcome:
        self.remediations[story_id] = self.remediations.get(story_id, 0) + 1
        healed = self.heal_after is not None and self.remediations[story_id] >= self.heal_after
        return StoryOutcome(story_id=story_id, code_ok=healed, pr_url=f"pr/{story_id}")


def _design_pass(_o: StoryOutcome) -> GateVerdict:
    return GateVerdict(gate="design", passed=True)


def _design_fail(_o: StoryOutcome) -> GateVerdict:
    return GateVerdict(gate="design", passed=False)


class ApproveGate:
    def approve(self, checkpoint: str, payload: object) -> bool:
        return True


def test_all_pass_ready_and_hitl2_but_never_merged(tmp_path: Path) -> None:
    bad = FakeBad([StoryOutcome(story_id="1.1", code_ok=True, pr_url="pr/1.1")])
    report = superviser(_layout(tmp_path), bad=bad, design_check=_design_pass, hitl=ApproveGate())
    assert report.results[0].status == "ready-for-review"
    assert report.results[0].attempts == 1
    assert report.hitl2_approved is True
    assert report.merged is False  # jamais d'auto-merge (décision 07)


def test_design_failure_retries_then_blocks(tmp_path: Path) -> None:
    bad = FakeBad([StoryOutcome(story_id="2.1", code_ok=True, pr_url="pr/2.1")])
    report = superviser(_layout(tmp_path), bad=bad, design_check=_design_fail, hitl=ApproveGate())
    assert report.results[0].status == "blocked"
    assert report.results[0].attempts == 4  # 1 initial + 3 retries (DE-3)
    assert report.hitl2_approved is False  # HITL 2 ne s'ouvre pas si une story est bloquée


def test_code_failure_heals_within_retries(tmp_path: Path) -> None:
    bad = FakeBad([StoryOutcome(story_id="3.1", code_ok=False)], heal_after=2)
    report = superviser(_layout(tmp_path), bad=bad, design_check=_design_pass, hitl=ApproveGate())
    assert report.results[0].status == "ready-for-review"
    assert report.results[0].attempts == 3  # initial KO + 2 remédiations


def test_default_hitl2_pauses_without_human(tmp_path: Path) -> None:
    bad = FakeBad([StoryOutcome(story_id="4.1", code_ok=True, pr_url="pr/4.1")])
    report = superviser(_layout(tmp_path), bad=bad, design_check=_design_pass)
    assert report.hitl2_approved is False  # ManualGate par défaut → pas de merge


def test_regression_blocks_when_baseline_green_turns_red(tmp_path: Path) -> None:
    """Baseline code verte ; une story qui casse le code (code_ok=False) est bloquée par
    le gate de non-régression, même après retries."""
    layout = _layout(tmp_path)
    layout.baseline = {"code": True}
    bad = FakeBad([StoryOutcome(story_id="9.1", code_ok=False)])  # code rouge → régression
    report = superviser(layout, bad=bad, design_check=_design_pass, hitl=ApproveGate())
    assert report.results[0].status == "blocked"
    assert report.results[0].attempts == 4  # 1 + 3 retries


def test_no_regression_when_baseline_absent(tmp_path: Path) -> None:
    layout = _layout(tmp_path)  # baseline None
    bad = FakeBad([StoryOutcome(story_id="9.2", code_ok=True, pr_url="pr/9.2")])
    report = superviser(layout, bad=bad, design_check=_design_pass, hitl=ApproveGate())
    assert report.results[0].status == "ready-for-review"
