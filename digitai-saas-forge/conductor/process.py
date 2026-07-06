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

import shutil
import subprocess
from collections.abc import Sequence
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
    """Runner de prod : ``shutil.which(args[0])`` + subprocess (shell=False, list, timeout)."""

    def run(
        self, args: Sequence[str], *, cwd: Path | None = None, timeout_s: int = 300
    ) -> ProcessResult:
        if not args:
            raise ValueError("ProcessRunner.run : args vide")
        exe = shutil.which(args[0])
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
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"{args[0]} : timeout après {timeout_s}s") from exc
        return ProcessResult(proc.returncode, proc.stdout or "", proc.stderr or "")
