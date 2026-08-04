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
from pathlib import Path
from typing import Literal, Protocol

from conductor.contracts import (
    BadSprintLayout,
    GateVerdict,
    SpecVerdict,
    SprintReport,
    Story,
    StoryOutcome,
    StoryResult,
)
from conductor.findings import FindingRecord, write_findings
from conductor.gates.design_gate import run_design_gate
from conductor.gates.regression_gate import evaluate_regression
from conductor.governance import HumanGate, ManualGate

GATE_MAX_RETRIES = 3  # DE-3 : 3 retries d'agent avant escalade HITL

DesignCheck = Callable[[StoryOutcome], GateVerdict]


class SpecComplianceReviewer(Protocol):
    """Juge la conformité d'une PR de story à ses critères d'acceptation."""

    def review(self, story: Story, outcome: StoryOutcome, cwd: Path) -> SpecVerdict: ...


class DefaultSpecReviewer:
    """Pass-through déterministe : aucune revue, aucun finding (comportement par défaut)."""

    def review(self, story: Story, outcome: StoryOutcome, cwd: Path) -> SpecVerdict:
        return SpecVerdict(passed=True)


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
    spec_reviewer: SpecComplianceReviewer | None = None,
    stories: list[Story] | None = None,
    max_retries: int = GATE_MAX_RETRIES,
) -> SprintReport:
    """E · lance le sprint, applique le double gate + remédiation, pose HITL 2.

    Ne merge jamais : `SprintReport.merged` reste False (décision 07).
    """
    if bad is not None:
        runner = bad
    else:
        from conductor.harness.resolve import resolve_bad_runner

        runner = resolve_bad_runner()
    gate = hitl if hitl is not None else ManualGate()
    design_md = layout.project_root / "design" / "DESIGN.md"
    check: DesignCheck = design_check or (lambda _outcome: run_design_gate(design_md))
    if spec_reviewer is not None:
        reviewer: SpecComplianceReviewer = spec_reviewer
    else:
        from conductor.harness.resolve import resolve_spec_reviewer

        reviewer = resolve_spec_reviewer()
    story_by_id = {s.id: s for s in (stories or [])}

    def _story_for(o: StoryOutcome) -> Story:
        return story_by_id.get(o.story_id) or Story(id=o.story_id, epic="", title="")

    def _passes(o: StoryOutcome) -> bool:
        design_ok = check(o).passed
        current = {"code": o.code_ok, "design": design_ok}
        # Non-régression : garde-fou do-no-harm. Actuellement SUBSUMÉ par les gates absolus de la
        # ligne de retour (current ne porte que code/design, déjà exigés verts) → pas de pouvoir de
        # blocage indépendant ICI ; sa logique propre est testée isolément (test_regression_gate).
        # Valeur indépendante = sémantique non-régression en brownfield (baseline rouge tolérée si
        # non aggravée) — décision différée, hors périmètre.
        no_regression = evaluate_regression(layout.baseline or {}, current).passed
        spec_ok = reviewer.review(_story_for(o), o, layout.project_root).passed
        return o.code_ok and design_ok and no_regression and spec_ok

    results: list[StoryResult] = []
    all_ready = True
    records: list[FindingRecord] = []
    next_id = 0

    for outcome in runner.run_sprint(layout):
        first = reviewer.review(_story_for(outcome), outcome, layout.project_root)
        attempts = 1
        passed = _passes(outcome)
        while not passed and attempts <= max_retries:
            outcome = runner.remediate(outcome.story_id, layout)  # noqa: PLW2901
            attempts += 1
            passed = _passes(outcome)

        status: Literal["ready-for-review", "blocked"] = (
            "ready-for-review" if passed else "blocked"
        )
        if not passed:
            all_ready = False  # escalade HITL : la story reste bloquée
        results.append(
            StoryResult(
                story_id=outcome.story_id,
                status=status,
                attempts=attempts,
                pr_url=outcome.pr_url,
            )
        )
        for finding in first.findings:
            next_id += 1
            kind = finding.get("kind", "")
            resolved = kind == "under-build" and status == "ready-for-review"
            records.append(
                FindingRecord(
                    id=f"SF-{next_id}",
                    story=outcome.story_id,
                    kind=kind,
                    criterion=finding.get("criterion", ""),
                    detail=finding.get("detail", ""),
                    severity=finding.get("severity", ""),
                    status="traité" if resolved else "non-traité",
                    note="corrigé en remédiation" if resolved else "à reprendre manuellement",
                )
            )

    if records:
        write_findings(layout.project_root / "SPEC_FINDINGS.md", records)

    hitl2 = gate.approve("merge final (HITL 2)", results) if (all_ready and results) else False
    return SprintReport(results=results, hitl2_approved=hitl2)
