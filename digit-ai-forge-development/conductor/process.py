"""ProcessRunner cross-platform unifié (portabilité — backlog P-07).

Tous les spawns de process externes de la forge passent par ici :
- args en ``list[str]`` (jamais une chaîne shell contenant une entrée non maîtrisée) ;
- binaire résolu par ``shutil.which`` → portable Windows/Linux/macOS (corrige les invocations
  en nom nu type ``npx`` qui lèvent ``WinError 2`` sous Windows, P-01/P-02) ;
- ``shell=False``, timeout borné.

Garde-fou : ``shell=True`` est interdit ici. Une commande contenant chemins/paramètres issus de
la mission doit être construite comme ``list[str]`` par l'appelant, pas comme f-string shell.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class ToolNotFound(RuntimeError):
    """Binaire requis introuvable dans le PATH (résolution ``shutil.which`` échouée)."""


@dataclass(frozen=True)
class ProcessResult:
    """Résultat d'un spawn : code de sortie + sorties capturées."""

    returncode: int
    stdout: str
    stderr: str


class ProcessRunner(Protocol):
    """Lance un process externe (args en liste) et renvoie un ProcessResult."""

    def run(
        self, args: Sequence[str], *, cwd: Path | None = None, timeout_s: int = 300
    ) -> ProcessResult: ...


class SubprocessProcessRunner:
    """Runner de prod : ``shutil.which(args[0])`` + subprocess (shell=False, list, timeout).

    ``env_overlay`` : variables appliquées **par-dessus** l'environnement courant pour chaque
    spawn (ex. préfixer le PATH avec le shim ``gh``). ``None`` = héritage intégral de
    l'environnement (comportement historique, non-régression). Porté par le constructeur — et non
    par ``run`` — pour ne pas alourdir le contrat ``ProcessRunner`` partagé par tous les runners.
    """

    def __init__(self, *, env_overlay: Mapping[str, str] | None = None) -> None:
        self._env_overlay = dict(env_overlay) if env_overlay is not None else None

    def run(
        self, args: Sequence[str], *, cwd: Path | None = None, timeout_s: int = 300
    ) -> ProcessResult:
        if not args:
            raise ValueError("ProcessRunner.run : args vide")
        # L'overlay doit aussi guider la résolution du binaire : si l'appelant préfixe le PATH
        # (shim gh), c'est ce PATH-là que `shutil.which` doit voir, pas celui du process courant.
        proc_env = {**os.environ, **self._env_overlay} if self._env_overlay is not None else None
        # Sans overlay : résolution historique (n'impose pas le kwarg `path`). Avec overlay :
        # `shutil.which` doit voir le PATH préfixé (shim gh), pas celui du process courant.
        if proc_env is None:
            exe = shutil.which(args[0])
        else:
            exe = shutil.which(args[0], path=proc_env.get("PATH"))
        if exe is None:
            raise ToolNotFound(f"Outil introuvable dans le PATH : {args[0]!r}")
        try:
            proc = subprocess.run(
                [exe, *args[1:]],
                cwd=cwd,
                capture_output=True,
                text=True,
                # Les outils (git/gh/az/npm) émettent de l'UTF-8 ; sans forçage, `text=True`
                # décode avec le codepage Windows (cp1252) et corrompt les accents (P-07).
                encoding="utf-8",
                errors="replace",
                timeout=timeout_s,
                check=False,
                env=proc_env,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"{args[0]} : timeout après {timeout_s}s") from exc
        return ProcessResult(proc.returncode, proc.stdout or "", proc.stderr or "")
