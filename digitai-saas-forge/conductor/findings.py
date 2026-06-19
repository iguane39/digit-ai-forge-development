"""Registre persistant des findings de conformité au spec (SPEC_FINDINGS.md).

Statut `traité`/`non-traité` pour reprise manuelle ultérieure (HITL 2, ou pré-vol du run suivant).
Rien n'est effacé : on bascule le statut, on conserve l'historique.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

_HEADER = (
    "# SPEC_FINDINGS — conformité au spec\n\n"
    "> Statut : `traité` (corrigé en remédiation) / `non-traité` (à reprendre manuellement).\n\n"
    "| id | story | kind | critère | détail | sévérité | statut | note |\n"
    "|----|-------|------|---------|--------|----------|--------|------|\n"
)


class FindingRecord(BaseModel):
    """Une ligne du registre SPEC_FINDINGS.md."""

    id: str
    story: str
    kind: str  # under-build | over-build
    criterion: str
    detail: str
    severity: str
    status: str  # traité | non-traité
    note: str = ""


def render_findings_md(records: list[FindingRecord]) -> str:
    """Rend le registre complet en Markdown (table à colonne `statut`)."""
    rows = "".join(
        f"| {r.id} | {r.story} | {r.kind} | {r.criterion} | {r.detail} | "
        f"{r.severity} | {r.status} | {r.note} |\n"
        for r in records
    )
    return _HEADER + rows


def write_findings(path: Path, records: list[FindingRecord]) -> None:
    """Écrit le registre sur disque (écrase : la liste fournie est l'état courant complet)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_findings_md(records), encoding="utf-8")
