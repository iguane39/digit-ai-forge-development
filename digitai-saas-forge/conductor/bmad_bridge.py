"""Étape C — Pont BMAD.

Collecte les artefacts de planification BMAD (`_bmad-output/planning-artifacts/epics.md` + PRD +
architecture) et pose **HITL 1** (décision 07). Le conductor **n'installe PAS** le framework BMAD :
son installeur est un TUI interactif non automatisable en headless (constaté en pilote, B-11). Les
artefacts (format BMAD) sont produits directement — par l'agent réel ou à la main — puis collectés
ici ; BAD construira ensuite lui-même le graphe de dépendances.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from conductor.contracts import BmadPlan
from conductor.governance import HitlPending, HumanGate, ManualGate
from conductor.onramp.base import Substrate

# Emplacements normalisés attendus par /bad (spike S-1b).
PLANNING_DIR = Path("_bmad-output/planning-artifacts")
EPICS_FILE = PLANNING_DIR / "epics.md"


class BmadPlanner(Protocol):
    """Produit un BmadPlan (PRD, architecture, epics) à partir d'un Substrate."""

    def plan(self, substrate: Substrate) -> BmadPlan: ...


class DefaultBmadPlanner:
    """Planner par défaut : collecte les artefacts de planification, pause HITL 1 si absents.

    N'installe rien (installeur BMAD = TUI non headless, B-11). Les artefacts au format BMAD sont
    produits par l'agent réel (opt-in) ou à la main ; le conductor garantit seulement leur
    présence. L'extraction des stories est laissée à BAD (spike S-1).
    """

    def plan(self, substrate: Substrate) -> BmadPlan:
        epics = substrate.repo_path / EPICS_FILE
        if not epics.exists():
            raise HitlPending(
                "Planification BMAD à produire : rédige les artefacts au format BMAD "
                f"({EPICS_FILE} + PRD.md + architecture.md) dans {substrate.repo_path}, puis "
                "approuve (HITL 1). Le conductor n'installe pas le framework (installeur TUI)."
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
