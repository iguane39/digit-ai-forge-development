"""Pont Python → Claude Code : invocation du CLI `claude` en mode headless.

Adapter réutilisable (ingestion maintenant ; /bad, BMAD plus tard). Injectable (fake en test).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol

from conductor.harness._text import clip
from conductor.process import ProcessRunner, SubprocessProcessRunner, ToolNotFound

_DEFAULT_TIMEOUT_S = 300


def _default_timeout_s() -> int:
    """Timeout par défaut, surchargé par ``CONDUCTOR_CLAUDE_TIMEOUT_S`` (300s est trop court pour
    la planification BMAD ou le développement autonome d'une story)."""
    raw = os.environ.get("CONDUCTOR_CLAUDE_TIMEOUT_S", "").strip()
    if raw.isdigit() and int(raw) > 0:
        return int(raw)
    return _DEFAULT_TIMEOUT_S


class CliRunner(Protocol):
    def run(self, prompt: str, cwd: Path) -> str: ...


class SubprocessClaudeCli:
    """Lance `claude -p <prompt> --output-format json` et renvoie le texte final (`result`).

    Passe par le ProcessRunner unifié (P-07) : binaire résolu par ``shutil.which`` — portable
    Windows/Linux, où `claude` est un shim `.cmd`/`.ps1` que ``subprocess`` ne trouve pas par nom
    nu (WinError 2) —, sortie décodée en UTF-8, timeout borné.

    Args:
        timeout_s: Délai maximal d'attente du processus claude (secondes). ``None`` → valeur par
            défaut, surchargée par l'env ``CONDUCTOR_CLAUDE_TIMEOUT_S``.
        skip_permissions: Si ``True``, ajoute ``--dangerously-skip-permissions`` à la commande
            (nécessaire pour le mode autonome BAD).
        runner: ProcessRunner injectable (fake en test).
    """

    def __init__(
        self,
        *,
        timeout_s: int | None = None,
        skip_permissions: bool = False,
        runner: ProcessRunner | None = None,
    ) -> None:
        self._timeout_s = timeout_s if timeout_s is not None else _default_timeout_s()
        self._skip_permissions = skip_permissions
        self._runner: ProcessRunner = runner or SubprocessProcessRunner()

    def run(self, prompt: str, cwd: Path) -> str:
        cmd = ["claude", "-p", prompt, "--output-format", "json"]
        if self._skip_permissions:
            cmd.append("--dangerously-skip-permissions")
        try:
            res = self._runner.run(cmd, cwd=cwd, timeout_s=self._timeout_s)
        except ToolNotFound as exc:
            raise RuntimeError(f"claude CLI introuvable dans le PATH : {exc}") from exc
        if res.returncode != 0:
            msg = f"claude CLI a échoué (code {res.returncode}) : {clip(res.stderr, 500)}"
            raise RuntimeError(msg)
        try:
            envelope = json.loads(res.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Sortie claude illisible (JSON invalide) : {res.stdout[:200]}"
            ) from exc
        result = envelope.get("result")
        if not isinstance(result, str):
            raise RuntimeError("Enveloppe claude sans champ `result` exploitable.")
        return result
