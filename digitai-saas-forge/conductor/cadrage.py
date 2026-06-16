"""Étape A — Cadrage cible & style.

Transforme une idée + des contraintes (budget, délai, stack, scope SaaS, charte)
en une MissionConfig validable. Cible et charte paramétrables (décision 08).
La logique sera implémentée en Epic 1 (story 1.5).
"""

from __future__ import annotations

from conductor.contracts import MissionConfig


def cadrer(idea: str, **contraintes: object) -> MissionConfig:
    """A · produit la configuration de mission. Pose les briques de t0 (décision 05)."""
    raise NotImplementedError("Étape A — implémentée en Epic 1 (story 1.5).")
