"""Gouvernance humaine — les deux points HITL (décision canonique 07).

L'automatisation s'arrête aux points de validation humaine, volontairement. Un `HumanGate`
modélise un point de contrôle ; en mode headless (`ManualGate`), aucune approbation n'est
accordée automatiquement → la chaîne se met en pause via `HitlPending`.

`DelegatedGate` (TF-0009, décision humaine Q-A du 08/08 : le conductor est maintenu) ouvre un
mode déléguable pour le dogfooding headless : une politique explicite, passée en config,
auto-approuve les checkpoints listés — tout le reste reste refusé par défaut, même posture que
`ManualGate`. Ce n'est jamais une approbation implicite : un checkpoint absent de la politique
est refusé, pas approuvé par erreur.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol


class HitlPending(Exception):
    """Levée quand la chaîne atteint un point HITL non approuvé : pause, pas échec."""


class HumanGate(Protocol):
    def approve(self, checkpoint: str, payload: object) -> bool: ...


class ManualGate:
    """Défaut headless : aucune validation automatique (l'humain doit approuver hors chaîne)."""

    def approve(self, checkpoint: str, payload: object) -> bool:
        return False


class DelegatedGate:
    """Politique déléguable : auto-approuve UNIQUEMENT les checkpoints dont l'intitulé commence
    par l'un des préfixes explicitement listés en config ; refuse tout le reste (repli identique
    à `ManualGate`). Les intitulés de checkpoint portent parfois un suffixe dynamique (ex.
    ``"HITL-0 — {subject}"``) : la correspondance par préfixe permet de cibler un type de
    checkpoint sans connaître son suffixe à l'avance, sans jamais élargir l'approbation au-delà
    des préfixes déclarés.

    Une politique vide (défaut) refuse tout, comme `ManualGate` — la délégation est un
    élargissement explicite, jamais un comportement implicite.
    """

    def __init__(self, auto_approve_prefixes: Iterable[str] = ()) -> None:
        self._prefixes = tuple(auto_approve_prefixes)

    def approve(self, checkpoint: str, payload: object) -> bool:
        return any(checkpoint.startswith(prefix) for prefix in self._prefixes)


def require_hitl0(subject: str, payload: object, *, gate: HumanGate | None = None) -> None:
    """Point HITL-0 (brownfield) : valider la normalisation / la carte d'archi avant le dev.

    Lève HitlPending si non approuvé (défaut ManualGate → pause). Optionnel/léger en C,
    fortement recommandé en B (dégradation déclarée à valider).
    """
    resolved = gate if gate is not None else ManualGate()
    if not resolved.approve(f"HITL-0 — {subject}", payload):
        raise HitlPending(f"HITL-0 — validation requise : {subject}")
