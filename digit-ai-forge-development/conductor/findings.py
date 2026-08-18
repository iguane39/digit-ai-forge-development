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


def render_findings_md(
    records: list[FindingRecord], *, indecisions: list[str] | None = None
) -> str:
    """Rend le registre complet en Markdown (table à colonne `statut`).

    TF-0375 — `indecisions` porte les stories que PERSONNE n a jugées. Sans ce préambule, une
    table vide se lit « zéro écart au cahier », alors qu elle peut vouloir dire « le gate n a
    rien confronté ». Les deux états produisaient exactement le même document.
    """
    rows = "".join(
        f"| {r.id} | {r.story} | {r.kind} | {r.criterion} | {r.detail} | "
        f"{r.severity} | {r.status} | {r.note} |\n"
        for r in records
    )
    tete = _HEADER
    if indecisions:
        tete = (
            "# SPEC_FINDINGS — conformité au spec\n\n"
            f"> **{len(indecisions)} story(s) NON JUGÉE(S)** — la table ci-dessous ne dit rien "
            "de leur conformité :\n"
            + "".join(f"> - {m}\n" for m in indecisions)
            + "\n" + _HEADER.split("\n\n", 1)[1]
        )
    elif not records:
        tete = _HEADER + ""
        return (
            tete
            + "\n_Aucun écart constaté, et le verdict a bien été RENDU sur chaque story : "
            "cette table vide est un résultat, pas un silence (TF-0375)._\n"
        )
    return tete + rows


def write_findings(
    path: Path, records: list[FindingRecord], *, indecisions: list[str] | None = None
) -> None:
    """Écrit le registre sur disque (écrase : la liste fournie est l'état courant complet)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_findings_md(records, indecisions=indecisions), encoding="utf-8")
