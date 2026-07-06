"""Gate code — délègue à la CI du template (ruff, mypy --strict, pytest, Playwright).

Note S-1 : le pipeline interne de BAD couvre déjà revue de tests, revue de code et
monitoring CI ; ce gate sert de filet de confirmation côté conductor. L'autorité de
blocage du merge reste la CI GitHub. Le conductor ne réimplémente pas les tests : il
lance le harness du dépôt généré via un runner injectable (subprocess en prod, fake en
test).
"""

from __future__ import annotations

import shlex
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from conductor.profiles import TargetProfile

from conductor.contracts import GateVerdict
from conductor.process import ProcessRunner, SubprocessProcessRunner

# Commande par défaut du harness code du template (déléguée, pas réimplémentée).
DEFAULT_CODE_CHECK = "uv run pytest"


class CommandRunner(Protocol):
    def run(self, command: str, cwd: Path) -> int: ...


class SubprocessRunner:
    """Runner de prod : découpe la commande en ``list[str]`` et délègue au ProcessRunner
    (``shell=False``, binaire résolu par ``shutil.which`` — portable). La commande vient du
    profil (valeur de confiance), donc ``shlex.split`` est sûr ; jamais de ``shell=True``."""

    def __init__(self, runner: ProcessRunner | None = None) -> None:
        self._runner: ProcessRunner = runner or SubprocessProcessRunner()

    def run(self, command: str, cwd: Path) -> int:
        return self._runner.run(shlex.split(command), cwd=cwd).returncode


def run_code_gate(
    repo_path: Path,
    *,
    profile: TargetProfile | None = None,
    command: str = DEFAULT_CODE_CHECK,
    runner: CommandRunner | None = None,
) -> GateVerdict:
    """Lit le verdict de la CI pour le dépôt de story (passed = exit 0).

    La commande vient du `TargetProfile` si fourni (sinon `command`/défaut).
    """
    cmd = profile.code_check if (profile and profile.code_check) else command
    rc = (runner or SubprocessRunner()).run(cmd, repo_path)
    return GateVerdict(
        gate="code",
        passed=rc == 0,
        findings=[] if rc == 0 else [{"command": cmd, "returncode": str(rc)}],
        log_ref=str(repo_path),
    )
