"""Sortie machine du run — `_forge-output/run-report.json` (R-V1).

Un run produisait un `SprintReport` puis le jetait : aucune trace exploitable par un outil
(CI, script, agent superviseur). Ce module sérialise le bilan de fin de chaîne dans le repo
cible, avec le **statut global** du run et un **horodatage**. L'horloge est injectable
(Protocol + implémentation par défaut, comme les runners de `process`/`tokens`) : les tests
figent le temps au lieu de le subir.

Le rapport est écrit dans les trois issues d'un run — complet, pause HITL, échec — pour que
l'appelant trouve toujours un fichier à lire, cohérent avec le code de retour du CLI.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel

from conductor.contracts import SprintReport

OUTPUT_DIR = Path("_forge-output")
REPORT_FILE = OUTPUT_DIR / "run-report.json"

# Statut global du run — aligné sur les codes de retour du CLI (0 / 2 / 1).
RunStatus = Literal["complete", "hitl-pending", "error"]


class Clock(Protocol):
    """Fournit l'horodatage du rapport (injectable : figé en test)."""

    def now(self) -> datetime: ...


class SystemClock:
    """Horloge de production : instant courant en UTC, timezone-aware."""

    def now(self) -> datetime:
        return datetime.now(UTC)


class RunReport(BaseModel):
    """Contenu de `_forge-output/run-report.json`.

    `sprint` est le `SprintReport` de l'étape E — absent (None) quand le run n'a pas atteint
    la fin de la chaîne (pause HITL ou échec).
    """

    status: RunStatus
    generated_at: datetime
    idea: str
    mode: str
    target: Path
    detail: str = ""  # message de pause HITL ou d'erreur, vide sur un run complet
    sprint: SprintReport | None = None


def write_run_report(
    target: Path,
    *,
    status: RunStatus,
    idea: str,
    mode: str,
    sprint: SprintReport | None = None,
    detail: str = "",
    clock: Clock | None = None,
) -> Path:
    """Écrit le rapport machine dans le repo cible et renvoie le chemin écrit.

    Crée `_forge-output/` au besoin ; écrase le rapport du run précédent (l'état courant
    complet est dans le fichier, pas dans son historique).
    """
    report = RunReport(
        status=status,
        generated_at=(clock or SystemClock()).now(),
        idea=idea,
        mode=mode,
        target=target,
        detail=detail,
        sprint=sprint,
    )
    dest = target / REPORT_FILE
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return dest
