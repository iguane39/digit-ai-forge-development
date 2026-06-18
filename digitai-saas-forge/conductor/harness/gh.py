"""Adapter GitHub CLI : observation des PR (source de vérité du run /bad)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Protocol

_FIELDS = "number,title,headRefName,statusCheckRollup,url"


class GhRunner(Protocol):
    def list_prs(self, cwd: Path) -> list[dict[str, Any]]: ...


class SubprocessGh:
    """Liste les PR ouvertes via `gh pr list --json`. Injectable (fake en test)."""

    def __init__(self, *, timeout_s: int = 60) -> None:
        self._timeout_s = timeout_s

    def list_prs(self, cwd: Path) -> list[dict[str, Any]]:
        try:
            proc = subprocess.run(
                ["gh", "pr", "list", "--state", "open", "--json", _FIELDS],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self._timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"gh : timeout après {self._timeout_s}s") from exc
        if proc.returncode != 0:
            raise RuntimeError(f"gh a échoué (code {proc.returncode}) : {proc.stderr[:500]}")
        out = proc.stdout.strip()
        if not out:
            return []
        parsed: list[dict[str, Any]] = json.loads(out)
        return parsed
