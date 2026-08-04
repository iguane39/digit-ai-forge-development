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
    command: str | None = None,
    runner: CommandRunner | None = None,
) -> GateVerdict:
    """Lit le verdict de la CI pour le dépôt de story (passed = exit 0).

    **P-16** : si le profil porte des commandes PAR RÔLE (`commands`), chacune est exécutée dans
    le répertoire du rôle et le verdict est agrégé (rôle sans commande test → skip tracé). Sinon
    la commande vient de `code_check` (ou de `command`). **P-06** : aucun défaut Python — sans
    commande utilisable, le gate est **skip tracé** (do-no-harm), jamais un `pytest` implicite.
    """
    if profile and profile.commands:
        return _run_role_gate(repo_path, profile, runner)
    cmd = profile.code_check if (profile and profile.code_check) else command
    if not cmd:
        return GateVerdict(
            gate="code",
            passed=True,
            findings=[{"skipped": "aucune commande code (profil absent ou sans code_check)"}],
            log_ref=str(repo_path),
        )
    rc = (runner or SubprocessRunner()).run(cmd, repo_path)
    return GateVerdict(
        gate="code",
        passed=rc == 0,
        findings=[] if rc == 0 else [{"command": cmd, "returncode": str(rc)}],
        log_ref=str(repo_path),
    )


def _run_role_gate(
    repo_path: Path, profile: TargetProfile, runner: CommandRunner | None
) -> GateVerdict:
    """Exécute la commande de test de chaque rôle dans son répertoire (P-16), verdict agrégé."""
    r = runner or SubprocessRunner()
    findings: list[dict[str, str]] = []
    passed = True
    ran_any = False
    for role, cmds in profile.commands.items():
        test = cmds.test
        if not test:
            findings.append({"skipped": f"rôle '{role}' sans commande test (P-06)"})
            continue
        ran_any = True
        role_dir = repo_path / profile.roles.get(role, ".")
        rc = r.run(test, role_dir)
        if rc != 0:
            passed = False
            findings.append({"role": role, "command": test, "returncode": str(rc)})
    if not ran_any:
        findings.append({"skipped": "aucune commande test par rôle utilisable (P-06)"})
    return GateVerdict(gate="code", passed=passed, findings=findings, log_ref=str(repo_path))
