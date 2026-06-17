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


def require_hitl0(subject: str, payload: object, *, gate: HumanGate | None = None) -> None:
    """Point HITL-0 (brownfield) : valider la normalisation / la carte d'archi avant le dev.

    Lève HitlPending si non approuvé (défaut ManualGate → pause). Optionnel/léger en C,
    fortement recommandé en B (dégradation déclarée à valider).
    """
    if not (gate or ManualGate()).approve(f"HITL-0 — {subject}", payload):
        raise HitlPending(f"HITL-0 — validation requise : {subject}")
