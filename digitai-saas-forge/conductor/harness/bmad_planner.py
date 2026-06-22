"""ClaudeCliBmadPlanner — planification BMAD réelle déclenchée via le CLI claude.

Déclenche la planification agentique (PRD/architecture/epics) puis OBSERVE les artefacts écrits
dans _bmad-output/planning-artifacts/. Gated par HITL 1 en aval. skip_permissions car la planif
écrit des fichiers / lance npx en headless. stories=[] : BAD reconstruit le graphe (spike S-1).
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
    "Installe BMAD-METHOD en mode NON-INTERACTIF "
    "(npx --yes bmad-method install --modules bmm,tea --tools claude-code) puis lance la "
    "planification BMAD dans le dossier _bmad-output/planning-artifacts/ : produis PRD.md, "
    "architecture.md, et epics.md (epics + stories priorisées)."
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
