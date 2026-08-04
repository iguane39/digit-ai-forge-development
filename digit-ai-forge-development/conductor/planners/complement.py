"""ComplementPlanner (intention) — réutilise la planification BMAD greenfield sur l'existant.

BA : un complément sur un SaaS forge = lancer la planification BMAD habituelle DANS le repo
existant (le substrat). On délègue donc à DefaultBmadPlanner. CompositePlanner enchaîne deux
planners (remédiation puis complément) et fusionne leurs stories en un seul backlog.
"""

from __future__ import annotations

from conductor.bmad_bridge import BmadPlanner
from conductor.contracts import BmadPlan
from conductor.onramp.base import Substrate


class ComplementPlanner:
    """Délègue à un planner BMAD (résolu via resolve_bmad_planner() par défaut) sur le substrat."""

    def __init__(self, inner: BmadPlanner | None = None) -> None:
        self._inner = inner  # résolu à l'appel via resolve_bmad_planner() si None

    def plan(self, substrate: Substrate) -> BmadPlan:
        inner = self._inner
        if inner is None:
            from conductor.harness.resolve import resolve_bmad_planner

            inner = resolve_bmad_planner()
        return inner.plan(substrate)


class CompositePlanner:
    """Compose deux planners : backlog = stories du 1er + du 2nd (ex. remédiation + complément)."""

    def __init__(self, first: BmadPlanner, second: BmadPlanner) -> None:
        self._first = first
        self._second = second

    def plan(self, substrate: Substrate) -> BmadPlan:
        a = self._first.plan(substrate)
        a_text = a.epics_md.read_text(encoding="utf-8") if a.epics_md.exists() else ""
        b = self._second.plan(substrate)  # peut écrire sur le même chemin que a
        b_text = b.epics_md.read_text(encoding="utf-8") if b.epics_md.exists() else ""
        a.epics_md.parent.mkdir(parents=True, exist_ok=True)
        a.epics_md.write_text(f"{a_text}\n{b_text}".strip() + "\n", encoding="utf-8")
        return a.model_copy(update={"stories": [*a.stories, *b.stories]})
