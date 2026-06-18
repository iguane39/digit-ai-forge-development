"""Étape C — Pont BMAD.

Installe/lance BMAD-METHOD (modules bmm,tea) sur le scaffold et collecte ses artefacts
dans `_bmad-output/planning-artifacts/epics.md`. Pose **HITL 1** (validation humaine du
PRD & de l'architecture, décision 07) : sans approbation, la chaîne se met en pause.

C'est ici que se concentre le travail réel post-spike S-1 (produire un backlog BMAD
valide) ; BAD construira ensuite lui-même le graphe de dépendances.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Protocol

from conductor.contracts import BmadPlan
from conductor.governance import HitlPending, HumanGate, ManualGate
from conductor.onramp.base import Substrate

# Modules BMAD requis par BAD (spike S-1b) : bmm = méthode, tea = test architecture (ATDD).
BMAD_INSTALL = "npx bmad-method install --modules bmm,tea"

# Emplacements normalisés attendus par /bad (spike S-1b).
PLANNING_DIR = Path("_bmad-output/planning-artifacts")
EPICS_FILE = PLANNING_DIR / "epics.md"


class BmadPlanner(Protocol):
    """Produit un BmadPlan (PRD, architecture, epics) à partir d'un Substrate."""

    def plan(self, substrate: Substrate) -> BmadPlan: ...


class DefaultBmadPlanner:
    """Planner de production : installe BMAD puis recense les artefacts de planification.

    L'extraction des stories est volontairement laissée à BAD (spike S-1) : le conductor
    ne parse pas le backlog, il garantit seulement sa présence.
    """

    def plan(self, substrate: Substrate) -> BmadPlan:
        subprocess.run(BMAD_INSTALL, cwd=substrate.repo_path, shell=True, check=False)
        epics = substrate.repo_path / EPICS_FILE
        if not epics.exists():
            raise HitlPending(
                "Planification BMAD à réaliser : produire "
                f"{EPICS_FILE} dans {substrate.repo_path}, puis approuver (HITL 1)."
            )
        return BmadPlan(
            prd_path=substrate.repo_path / PLANNING_DIR / "PRD.md",
            architecture_path=substrate.repo_path / PLANNING_DIR / "architecture.md",
            epics_md=epics,
        )


def lancer_planification(
    substrate: Substrate,
    *,
    planner: BmadPlanner | None = None,
    gate: HumanGate | None = None,
) -> BmadPlan:
    """C · brief → PRD → architecture → epics → stories ; suspend sur HITL 1.

    Lève HitlPending si la planification n'est pas approuvée par un humain (décision 07).
    """
    if planner is None:
        from conductor.harness.resolve import resolve_bmad_planner

        planner = resolve_bmad_planner()
    plan = planner.plan(substrate)
    resolved_gate = gate if gate is not None else ManualGate()
    if not resolved_gate.approve("PRD & architecture (HITL 1)", plan):
        raise HitlPending("HITL 1 — validation du PRD & de l'architecture requise avant le dev.")
    return plan.model_copy(update={"hitl1_approved": True})
