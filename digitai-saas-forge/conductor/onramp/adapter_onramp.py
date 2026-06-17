"""AdapterOnramp (branche C) — stub posé en BC-T1 pour le routage ; implémenté en BC-T3."""

from __future__ import annotations

from pathlib import Path

from conductor.contracts import MissionConfig
from conductor.onramp.base import Substrate


class AdapterOnramp:
    """Bretelle brownfield « branche C ». Implémentation complète en BC-T3."""

    def __init__(
        self,
        *,
        code_runner: object | None = None,
        design_linter: object | None = None,
        analyzer: object | None = None,
    ) -> None:
        self._code_runner = code_runner
        self._design_linter = design_linter
        self._analyzer = analyzer

    def prepare(self, config: MissionConfig, dest: Path) -> Substrate:
        raise NotImplementedError("AdapterOnramp implémenté en BC-T3.")
