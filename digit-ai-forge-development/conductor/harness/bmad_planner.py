"""ClaudeCliBmadPlanner — planification BMAD réelle déclenchée via le CLI claude.

Déclenche un agent qui **produit directement** les artefacts (PRD/architecture/epics) dans
_bmad-output/planning-artifacts/, **sans installer** le framework BMAD (installeur TUI non
headless, B-11), puis OBSERVE epics.md et en parse les stories (parse_epics, B-3). Gated HITL 1.
skip_permissions car l'agent écrit des fichiers en headless.
"""

from __future__ import annotations

from pathlib import Path

from conductor.contracts import BmadPlan
from conductor.governance import HitlPending
from conductor.harness.claude_cli import CliRunner, SubprocessClaudeCli
from conductor.harness.epics_parser import parse_epics
from conductor.onramp.base import Substrate

_PLANNING_DIR = Path("_bmad-output/planning-artifacts")
_TRIGGER = (
    "Produis DIRECTEMENT les artefacts de planification BMAD dans "
    "_bmad-output/planning-artifacts/ : PRD.md, architecture.md, et epics.md (epics + stories "
    "priorisées, chacune avec ses critères d'acceptation, au format BMAD). N'installe PAS le "
    "framework BMAD — son installeur est un TUI non automatisable : rédige les fichiers toi-même."
)


class ClaudeCliBmadPlanner:
    """Implémente BmadPlanner : déclenche la planif BMAD réelle puis collecte les artefacts."""

    def __init__(self, *, cli: CliRunner | None = None) -> None:
        self._cli = cli or SubprocessClaudeCli(skip_permissions=True)

    def plan(self, substrate: Substrate) -> BmadPlan:
        self._cli.run(_TRIGGER, substrate.repo_path)
        planning = substrate.repo_path / _PLANNING_DIR
        epics = planning / "epics.md"
        if not epics.exists():
            raise HitlPending(
                f"Planification BMAD : {epics} introuvable après déclenchement. "
                "Produire/valider le backlog, puis approuver (HITL 1)."
            )
        return BmadPlan(
            prd_path=planning / "PRD.md",
            architecture_path=planning / "architecture.md",
            epics_md=epics,
            stories=parse_epics(epics.read_text(encoding="utf-8")),
        )
