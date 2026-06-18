"""ClaudeCliBadRunner — exécution réelle du sprint par le skill /bad.

Déclenche /bad via le CLI `claude` (autonome, 1 worktree/story) puis OBSERVE le résultat via
`gh pr list` (source de vérité). N'auto-merge jamais : AUTO_PR_MERGE=false est garanti par le
type (`BadConfig.auto_pr_merge: Literal[False]`). Posture B : opt-in env + garde-fous natifs BAD.
"""

from __future__ import annotations

from typing import Any

from conductor.contracts import BadSprintLayout, StoryOutcome
from conductor.harness.claude_cli import CliRunner, SubprocessClaudeCli
from conductor.harness.gh import GhRunner, SubprocessGh

_TRIGGER = (
    "run BAD : lance le sprint autonome (un worktree git par story, pipeline 7 étapes). "
    "Ne merge AUCUNE PR (AUTO_PR_MERGE=false) ; ouvre les PR pour revue humaine."
)
_REMEDIATE = "BAD : reprends la story {story_id} pour corriger les gates en échec, sans merger."

_FAIL = {"FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "FAILING", "FAILED"}


def _code_ok(rollup: list[dict[str, Any]]) -> bool:
    """Vrai si au moins un check et aucun en échec (état CI consolidé de la PR)."""
    if not rollup:
        return False
    for check in rollup:
        status = str(check.get("conclusion") or check.get("state") or "").upper()
        if status in _FAIL:
            return False
    return True


def _to_outcome(pr: dict[str, Any]) -> StoryOutcome:
    return StoryOutcome(
        story_id=str(pr.get("headRefName", "")),
        code_ok=_code_ok(pr.get("statusCheckRollup") or []),
        pr_url=pr.get("url"),
    )


class ClaudeCliBadRunner:
    """Implémente BadRunner : /bad réel (CliRunner) + observation via GhRunner."""

    def __init__(self, *, cli: CliRunner | None = None, gh: GhRunner | None = None) -> None:
        self._cli = cli or SubprocessClaudeCli(skip_permissions=True)
        self._gh = gh or SubprocessGh()

    def run_sprint(self, layout: BadSprintLayout) -> list[StoryOutcome]:
        self._cli.run(_TRIGGER, layout.project_root)
        return [_to_outcome(pr) for pr in self._gh.list_prs(layout.project_root)]

    def remediate(self, story_id: str, layout: BadSprintLayout) -> StoryOutcome:
        self._cli.run(_REMEDIATE.format(story_id=story_id), layout.project_root)
        for pr in self._gh.list_prs(layout.project_root):
            if str(pr.get("headRefName", "")) == story_id:
                return _to_outcome(pr)
        return StoryOutcome(story_id=story_id, code_ok=False)
