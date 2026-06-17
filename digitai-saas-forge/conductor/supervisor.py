"""Étape E — Superviseur BAD + double gate.

Invoque le skill `/bad` (PAS un import Python — spike S-1) qui développe les stories
(1 worktree/story, pipeline 7 étapes, code gate interne). Le superviseur ajoute ce que
BAD ne fait pas : le **gate design** par story, une remédiation bornée à **3 retries**
(DE-3) puis escalade, et **HITL 2** avant tout merge (décision 07). Le merge automatique
est interdit : `auto_pr_merge=False` et `SprintReport.merged` verrouillé à False.

Le contexte design est injecté par **copie locale** des styles (DE-2), pas via CLI.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from conductor.contracts import (
    BadSprintLayout,
    GateVerdict,
    SprintReport,
    StoryOutcome,
    StoryResult,
)
from conductor.gates.design_gate import run_design_gate
from conductor.gates.regression_gate import evaluate_regression
from conductor.governance import HumanGate, ManualGate

GATE_MAX_RETRIES = 3  # DE-3 : 3 retries d'agent avant escalade HITL

DesignCheck = Callable[[StoryOutcome], GateVerdict]


class BadRunner(Protocol):
    """Pilote le skill /bad : développe les stories et remédie sur demande."""

    def run_sprint(self, layout: BadSprintLayout) -> list[StoryOutcome]: ...
    def remediate(self, story_id: str, layout: BadSprintLayout) -> StoryOutcome: ...


class DefaultBadRunner:
    """Runner de production : invoque le skill `/bad` (harness Claude Code).

    Nécessite `gh` authentifié + GITHUB_PERSONAL_ACCESS_TOKEN, et force AUTO_PR_MERGE=false
    (préserve HITL 2). L'invocation effective relève du harness Claude Code, hors process
    Python : on signale explicitement le point d'intégration.
    """

    def run_sprint(self, layout: BadSprintLayout) -> list[StoryOutcome]:
        raise NotImplementedError(
            "Invoquer le skill /bad dans le harness Claude Code : "
            f"`/bad MAX_PARALLEL_STORIES={layout.config.max_parallel_stories} "
            "AUTO_PR_MERGE=false` (gh authentifié requis)."
        )

    def remediate(self, story_id: str, layout: BadSprintLayout) -> StoryOutcome:
        raise NotImplementedError(f"Remédiation de la story {story_id} via /bad (harness requis).")


def superviser(
    layout: BadSprintLayout,
    *,
    bad: BadRunner | None = None,
    design_check: DesignCheck | None = None,
    hitl: HumanGate | None = None,
    max_retries: int = GATE_MAX_RETRIES,
) -> SprintReport:
    """E · lance le sprint, applique le double gate + remédiation, pose HITL 2.

    Ne merge jamais : `SprintReport.merged` reste False (décision 07).
    """
    runner = bad or DefaultBadRunner()
    gate = hitl or ManualGate()
    design_md = layout.project_root / "design" / "DESIGN.md"
    check: DesignCheck = design_check or (lambda _outcome: run_design_gate(design_md))

    def _passes(o: StoryOutcome) -> bool:
        design_ok = check(o).passed
        current = {"code": o.code_ok, "design": design_ok}
        no_regression = evaluate_regression(layout.baseline or {}, current).passed
        return o.code_ok and design_ok and no_regression

    results: list[StoryResult] = []
    all_ready = True

    for outcome in runner.run_sprint(layout):
        attempts = 1
        passed = _passes(outcome)
        while not passed and attempts <= max_retries:
            outcome = runner.remediate(outcome.story_id, layout)  # noqa: PLW2901
            attempts += 1
            passed = _passes(outcome)

        if passed:
            results.append(
                StoryResult(
                    story_id=outcome.story_id,
                    status="ready-for-review",
                    attempts=attempts,
                    pr_url=outcome.pr_url,
                )
            )
        else:
            all_ready = False  # escalade HITL : la story reste bloquée
            results.append(
                StoryResult(
                    story_id=outcome.story_id,
                    status="blocked",
                    attempts=attempts,
                    pr_url=outcome.pr_url,
                )
            )

    hitl2 = gate.approve("merge final (HITL 2)", results) if (all_ready and results) else False
    return SprintReport(results=results, hitl2_approved=hitl2)
