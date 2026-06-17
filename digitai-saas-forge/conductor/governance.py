"""Gouvernance humaine — les deux points HITL (décision canonique 07).

L'automatisation s'arrête aux points de validation humaine, volontairement. Un `HumanGate`
modélise un point de contrôle ; en mode headless (`ManualGate`), aucune approbation n'est
accordée automatiquement → la chaîne se met en pause via `HitlPending`.
"""

from __future__ import annotations

from typing import Protocol


class HitlPending(Exception):
    """Levée quand la chaîne atteint un point HITL non approuvé : pause, pas échec."""


class HumanGate(Protocol):
    def approve(self, checkpoint: str, payload: object) -> bool: ...


class ManualGate:
    """Défaut headless : aucune validation automatique (l'humain doit approuver hors chaîne)."""

    def approve(self, checkpoint: str, payload: object) -> bool:
        return False
