"""Étape B — Scaffold-first SaaS.

Invoque `copier copy` sur la cible (targets/fastapi-saas) ET greffe les briques
SaaS retenues AVANT tout agent (décision canonique 02 — premier garde-fou).
Délègue au template ; n'implémente pas sa logique. Implémentée en Epic 1 (1.1).
"""

from __future__ import annotations

from conductor.contracts import MissionConfig, ScaffoldResult


def scaffold(config: MissionConfig) -> ScaffoldResult:
    """B · génère le squelette de production puis greffe les briques (build-vs-buy)."""
    raise NotImplementedError("Étape B — implémentée en Epic 1 (story 1.1).")
