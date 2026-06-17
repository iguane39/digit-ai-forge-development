"""RemediationPlanner — backlog de correctifs déterministe depuis la baseline.

v1 (décision spec) : couvre tests/CI + conformité design — les deux dimensions déjà
mesurables sans outillage neuf (baseline capturée à l'onramp). Sécurité/dette/upgrades
= incréments ultérieurs. Écrit epics.md dans la layout attendue par /bad (spike S-1b).
"""

from __future__ import annotations

from pathlib import Path

from conductor.contracts import BmadPlan, Story
from conductor.onramp.base import Substrate

PLANNING_DIR = Path("_bmad-output/planning-artifacts")


def _remediation_stories(baseline: dict[str, bool]) -> list[Story]:
    stories: list[Story] = []
    if baseline.get("code") is False:
        stories.append(
            Story(
                id="R1",
                epic="remediation",
                title="Rendre la CI code verte",
                acceptance=[
                    "Le gate code (ruff/mypy/pytest) passe",
                    "Aucune régression introduite",
                ],
            )
        )
    if baseline.get("design") is False:
        stories.append(
            Story(
                id="R2",
                epic="remediation",
                title="Mettre l'UI en conformité design (WCAG/refs)",
                acceptance=["Le lint design ne remonte aucun finding bloquant"],
            )
        )
    return stories


def _render_epics_md(stories: list[Story]) -> str:
    lines = ["# Epics — remediation", ""]
    for s in stories:
        lines.append(f"## Story {s.id} — {s.title}")
        for a in s.acceptance:
            lines.append(f"- [ ] {a}")
        lines.append("")
    return "\n".join(lines)


class RemediationPlanner:
    """Implémente le protocole BmadPlanner : substrat → BmadPlan (stories de correctif)."""

    def plan(self, substrate: Substrate) -> BmadPlan:
        baseline = substrate.baseline or {}
        stories = _remediation_stories(baseline)
        planning = substrate.repo_path / PLANNING_DIR
        planning.mkdir(parents=True, exist_ok=True)
        epics_md = planning / "epics.md"
        epics_md.write_text(_render_epics_md(stories), encoding="utf-8")
        return BmadPlan(
            prd_path=planning / "PRD.md",
            architecture_path=planning / "architecture.md",
            epics_md=epics_md,
            stories=stories,
        )
