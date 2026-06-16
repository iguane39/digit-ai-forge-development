"""Étape E — Superviseur BAD + double gate.

Invoque le skill `/bad` (PAS un import Python — spike S-1) epic par epic, injecte
le contexte design par COPIE LOCALE des styles (DE-2, pas de CLI), orchestre le
gate design (le gate code est largement couvert par le pipeline interne de BAD),
applique 3 retries puis escalade HITL (DE-3), et pose HITL 2 (décision 07).
Implémentée en Epic 3 (stories 3.3–3.5).
"""

from __future__ import annotations

from conductor.contracts import BadSprintLayout

GATE_MAX_RETRIES = 3  # DE-3 : 3 retries d'agent avant escalade HITL


def superviser(layout: BadSprintLayout) -> None:
    """E · lance le sprint autonome, double gate, HITL 2. Ne merge jamais (HITL 2)."""
    raise NotImplementedError("Étape E — implémentée en Epic 3 (stories 3.3–3.5).")
