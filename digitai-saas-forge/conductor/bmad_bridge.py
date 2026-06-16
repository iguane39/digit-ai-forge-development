"""Étape C — Pont BMAD.

Installe/lance BMAD-METHOD (modules bmm,tea) sur le scaffold et collecte ses
artefacts dans _bmad-output/planning-artifacts/epics.md. Pose HITL 1 (validation
humaine du PRD & de l'architecture, décision 07). C'est ici que se concentre le
travail réel post-spike S-1. Implémentée en Epic 3 (story 3.1).
"""

from __future__ import annotations

from conductor.contracts import BmadPlan, ScaffoldResult


def lancer_planification(scaffold: ScaffoldResult) -> BmadPlan:
    """C · brief → PRD → architecture → epics → stories ; suspend sur HITL 1."""
    raise NotImplementedError("Étape C — implémentée en Epic 3 (story 3.1).")
