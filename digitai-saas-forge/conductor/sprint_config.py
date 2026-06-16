"""Étape D — Adapter de sprint (ex-« compilateur »).

CORRECTION spike S-1 : BAD construit lui-même le graphe de dépendances depuis le
backlog. D NE compile PAS de graphe (cela réimplémenterait BAD = violation
décision 01). D est un adapter de *placement & configuration* :
  - placer les artefacts BMAD dans la layout attendue par /bad ;
  - initialiser sprint-status.yaml ;
  - écrire la section bad: de _bmad/config.yaml (auto_pr_merge=False — HITL 2).
Implémentée en Epic 3 (story 3.2).
"""

from __future__ import annotations

from conductor.contracts import BadSprintLayout, BmadPlan


def preparer_sprint(plan: BmadPlan) -> BadSprintLayout:
    """D · place le backlog + écrit la config bad: pour que /bad démarre."""
    raise NotImplementedError("Étape D — implémentée en Epic 3 (story 3.2).")
