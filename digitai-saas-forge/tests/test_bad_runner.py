"""ClaudeCliBadRunner : déclenche /bad (CliRunner) puis observe les PR (GhRunner) → StoryOutcome."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from conductor.contracts import BadSprintLayout
from conductor.harness.bad_runner import ClaudeCliBadRunner


class _FakeCli:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def run(self, prompt: str, cwd: Path) -> str:
        self.prompts.append(prompt)
        return "déclenché"


class _FakeGh:
    def __init__(self, prs: list[dict[str, Any]]) -> None:
        self._prs = prs

    def list_prs(self, cwd: Path) -> list[dict[str, Any]]:
        return self._prs


def _layout(tmp: Path) -> BadSprintLayout:
    return BadSprintLayout(
        project_root=tmp,
        epics_md=tmp / "epics.md",
        sprint_status_yaml=tmp / "s.yaml",
        bmad_config_yaml=tmp / "c.yaml",
    )


def _pr(branch: str, *, ok: bool, url: str = "u") -> dict[str, Any]:
    rollup = [{"conclusion": "SUCCESS"}] if ok else [{"conclusion": "FAILURE"}]
    return {"number": 1, "headRefName": branch, "statusCheckRollup": rollup, "url": url}


def test_run_sprint_maps_prs_to_outcomes(tmp_path: Path) -> None:
    gh = _FakeGh([_pr("story-1-1-login", ok=True, url="http://pr/1")])
    runner = ClaudeCliBadRunner(cli=_FakeCli(), gh=gh)
    outcomes = runner.run_sprint(_layout(tmp_path))
    assert len(outcomes) == 1
    assert outcomes[0].story_id == "story-1-1-login"
    assert outcomes[0].code_ok is True
    assert outcomes[0].pr_url == "http://pr/1"


def test_run_sprint_triggers_bad(tmp_path: Path) -> None:
    cli = _FakeCli()
    ClaudeCliBadRunner(cli=cli, gh=_FakeGh([])).run_sprint(_layout(tmp_path))
    assert cli.prompts and "BAD" in cli.prompts[0]


def test_code_ok_false_on_failed_check(tmp_path: Path) -> None:
    gh = _FakeGh([_pr("story-2-1-x", ok=False)])
    outcomes = ClaudeCliBadRunner(cli=_FakeCli(), gh=gh).run_sprint(_layout(tmp_path))
    assert outcomes[0].code_ok is False


def test_remediate_reobserves_target_story(tmp_path: Path) -> None:
    gh = _FakeGh([_pr("story-3-1-x", ok=True, url="http://pr/3")])
    out = ClaudeCliBadRunner(cli=_FakeCli(), gh=gh).remediate("story-3-1-x", _layout(tmp_path))
    assert out.story_id == "story-3-1-x"
    assert out.pr_url == "http://pr/3"
