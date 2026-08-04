"""SubprocessGh : `gh pr list --json …` → liste de PR (source de vérité d'observation)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from conductor.harness.gh import SubprocessGh


def _completed(stdout: str, rc: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["gh"], returncode=rc, stdout=stdout, stderr="")


def test_list_prs_parses_json(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    prs = [{"number": 1, "headRefName": "story-1-1-x", "url": "u", "statusCheckRollup": []}]
    monkeypatch.setattr(
        "conductor.harness.gh.subprocess.run", lambda *a, **k: _completed(json.dumps(prs))
    )
    assert SubprocessGh().list_prs(tmp_path) == prs


def test_list_prs_empty_output_is_empty_list(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("conductor.harness.gh.subprocess.run", lambda *a, **k: _completed(""))
    assert SubprocessGh().list_prs(tmp_path) == []


def test_list_prs_nonzero_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("conductor.harness.gh.subprocess.run", lambda *a, **k: _completed("", rc=1))
    with pytest.raises(RuntimeError, match="gh"):
        SubprocessGh().list_prs(tmp_path)
