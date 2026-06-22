"""ClaudeCliBmadPlanner : déclenche la planif BMAD (claude -p) puis observe epics.md."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.governance import HitlPending
from conductor.harness.bmad_planner import ClaudeCliBmadPlanner
from conductor.onramp.base import Substrate
from conductor.profiles import FASTAPI_SAAS


class _FakeCli:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def run(self, prompt: str, cwd: Path) -> str:
        self.prompts.append(prompt)
        return "planifié"


def _substrate(tmp: Path) -> Substrate:
    return Substrate(repo_path=tmp, profile=FASTAPI_SAAS, design_md_path=tmp / "d.md")


def test_plan_triggers_and_reads_epics(tmp_path: Path) -> None:
    planning = tmp_path / "_bmad-output" / "planning-artifacts"
    planning.mkdir(parents=True)
    (planning / "epics.md").write_text("# Epics\n", encoding="utf-8")
    cli = _FakeCli()
    plan = ClaudeCliBmadPlanner(cli=cli).plan(_substrate(tmp_path))
    assert cli.prompts and "BMAD" in cli.prompts[0]
    assert plan.epics_md == planning / "epics.md"
    assert plan.hitl1_approved is False
    assert plan.stories == []


def test_plan_raises_hitl_pending_if_no_epics(tmp_path: Path) -> None:
    with pytest.raises(HitlPending, match="BMAD|epics"):
        ClaudeCliBmadPlanner(cli=_FakeCli()).plan(_substrate(tmp_path))


def test_trigger_is_non_interactive() -> None:
    """B-10 : le trigger agent instruit aussi un install non-interactif."""
    from conductor.harness.bmad_planner import _TRIGGER

    assert "--yes" in _TRIGGER
    assert "--tools claude-code" in _TRIGGER
