"""Pont Python → Claude Code : invocation du CLI `claude` en mode headless.

Adapter réutilisable (ingestion maintenant ; /bad, BMAD plus tard). Injectable (fake en test).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Protocol


class CliRunner(Protocol):
    def run(self, prompt: str, cwd: Path) -> str: ...


class SubprocessClaudeCli:
    """Lance `claude -p <prompt> --output-format json` et renvoie le texte final (`result`)."""

    def __init__(self, *, timeout_s: int = 300) -> None:
        self._timeout_s = timeout_s

    def run(self, prompt: str, cwd: Path) -> str:
        try:
            proc = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "json"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self._timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"claude CLI : timeout après {self._timeout_s}s") from exc
        if proc.returncode != 0:
            msg = f"claude CLI a échoué (code {proc.returncode}) : {proc.stderr[:500]}"
            raise RuntimeError(msg)
        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Sortie claude illisible (JSON invalide) : {proc.stdout[:200]}"
            ) from exc
        result = envelope.get("result")
        if not isinstance(result, str):
            raise RuntimeError("Enveloppe claude sans champ `result` exploitable.")
        return result
