"""Gate code — délègue à la CI du template (ruff, mypy --strict, pytest, Playwright).

Note S-1 : le pipeline interne de BAD couvre déjà revue de tests, revue de code et
monitoring CI ; ce gate sert de filet de confirmation côté conductor. L'autorité de
blocage du merge reste la CI GitHub. Implémenté en Epic 1 (story 1.6).
"""

from __future__ import annotations

from pathlib import Path

from conductor.contracts import GateVerdict


def run_code_gate(repo_path: Path) -> GateVerdict:
    """Lit le verdict de la CI du template pour le repo de story."""
    raise NotImplementedError("Gate code — implémenté en Epic 1 (story 1.6).")
