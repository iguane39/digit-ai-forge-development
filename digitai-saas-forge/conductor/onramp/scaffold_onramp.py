"""ScaffoldOnramp — la bretelle greenfield : génère le repo (enveloppe scaffold.scaffold)."""

from __future__ import annotations

from pathlib import Path

from conductor.contracts import MissionConfig
from conductor.onramp.base import Substrate
from conductor.process import ProcessRunner
from conductor.profiles import FASTAPI_SAAS
from conductor.scaffold import scaffold


class ScaffoldOnramp:
    def __init__(self, runner: ProcessRunner | None = None) -> None:
        self._runner = runner

    def prepare(self, config: MissionConfig, dest: Path) -> Substrate:
        result = scaffold(config, dest, runner=self._runner)
        return Substrate(
            repo_path=result.repo_path,
            profile=FASTAPI_SAAS,
            design_md_path=result.design_md_path,
        )
