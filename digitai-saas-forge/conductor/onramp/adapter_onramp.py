"""AdapterOnramp — bretelle brownfield « branche C » : repo FastAPI compatible à normaliser.

Normalise vers le contrat de la cible (crée un DESIGN.md par défaut s'il manque),
DÉCLARE ce qui ne peut être tenu (ex. harness CI absent), capture la carte d'archi (ingestion
hybride) et la baseline APRÈS normalisation. Ne migre pas la stack (B-standard).
"""

from __future__ import annotations

from pathlib import Path

from conductor.contracts import MissionConfig
from conductor.gates.code_gate import CommandRunner
from conductor.gates.design_gate import DesignLinter
from conductor.onramp.analyzer import Analyzer, HeuristicAnalyzer
from conductor.onramp.base import Substrate
from conductor.onramp.detect import has_ci
from conductor.onramp.no_onramp import capture_baseline
from conductor.profiles import FASTAPI_SAAS

_DEFAULT_DESIGN_MD = """---
name: Imported Project
colors:
  primary: "#2563eb"
  ink: "#0f172a"
typography:
  heading: "Roboto"
  body: "DM Sans"
---

# Design System (importé)

Charte minimale créée par AdapterOnramp (branche C). À compléter par la charte réelle.
"""


class AdapterOnramp:
    """Branche C : normalise un repo FastAPI incomplet, puis capture baseline + carte d'archi."""

    def __init__(
        self,
        *,
        code_runner: CommandRunner | None = None,
        design_linter: DesignLinter | None = None,
        analyzer: Analyzer | None = None,
    ) -> None:
        self._code_runner = code_runner
        self._design_linter = design_linter
        self._analyzer: Analyzer = analyzer or HeuristicAnalyzer()

    def prepare(self, config: MissionConfig, dest: Path) -> Substrate:
        repo = dest
        if not (repo / "pyproject.toml").exists():
            raise ValueError(
                f"AdapterOnramp (C) attend un repo FastAPI (pyproject.toml absent) dans {repo} : "
                "stack arbitraire → relève de l'epic BB."
            )
        notes: list[str] = []

        design_md = repo / FASTAPI_SAAS.design_md_path
        if not design_md.exists():
            design_md.parent.mkdir(parents=True, exist_ok=True)
            design_md.write_text(_DEFAULT_DESIGN_MD, encoding="utf-8")
            notes.append("DESIGN.md créé par normalisation (à compléter).")

        if not has_ci(repo):
            notes.append("Harness CI absent : le gate code s'appuiera sur un harness à fournir.")

        arch_map = self._analyzer.analyze(repo)
        baseline = capture_baseline(
            repo, FASTAPI_SAAS, code_runner=self._code_runner, design_linter=self._design_linter
        )
        return Substrate(
            repo_path=repo,
            profile=FASTAPI_SAAS,
            design_md_path=design_md,
            baseline=baseline,
            arch_map=arch_map,
            declared_degradation=notes,
        )
