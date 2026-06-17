"""NoOnramp — bretelle brownfield « branche A » : reprise d'un SaaS généré par la forge.

Ne génère rien : vérifie que le repo porte les marqueurs de la cible, puis capture une
BASELINE (statut vert/rouge des gates existants) qui servira au gate de non-régression (E).
Ingestion 100 % heuristique en BA (décision spec).
"""

from __future__ import annotations

from pathlib import Path

from conductor.contracts import MissionConfig
from conductor.gates.code_gate import CommandRunner, run_code_gate
from conductor.gates.design_gate import DesignLinter, run_design_gate
from conductor.onramp.base import Substrate
from conductor.profiles import FASTAPI_SAAS, TargetProfile


def capture_baseline(
    repo_path: Path,
    profile: TargetProfile,
    *,
    code_runner: CommandRunner | None = None,
    design_linter: DesignLinter | None = None,
) -> dict[str, bool]:
    """Statut vert/rouge des gates applicables AVANT toute intervention (do-no-harm)."""
    baseline: dict[str, bool] = {}
    if profile.code_check is not None:
        baseline["code"] = run_code_gate(repo_path, profile=profile, runner=code_runner).passed
    if profile.has_ui:
        design_md = repo_path / profile.design_md_path
        baseline["design"] = run_design_gate(design_md, linter=design_linter).passed
    return baseline


class NoOnramp:
    """Branche A : repo déjà sur la cible. Vérifie les marqueurs + capture la baseline."""

    def __init__(
        self,
        *,
        code_runner: CommandRunner | None = None,
        design_linter: DesignLinter | None = None,
    ) -> None:
        self._code_runner = code_runner
        self._design_linter = design_linter

    def prepare(self, config: MissionConfig, dest: Path) -> Substrate:
        repo = dest  # en brownfield, `dest` EST le repo existant
        if not (repo / "pyproject.toml").exists():
            raise ValueError(
                f"NoOnramp (branche A) attend un repo cible : marqueurs absents dans {repo} "
                "(pyproject.toml introuvable). Un repo non conforme relève de BC/BB."
            )
        baseline = capture_baseline(
            repo, FASTAPI_SAAS, code_runner=self._code_runner, design_linter=self._design_linter
        )
        return Substrate(
            repo_path=repo,
            profile=FASTAPI_SAAS,
            design_md_path=repo / FASTAPI_SAAS.design_md_path,
            baseline=baseline,
        )
