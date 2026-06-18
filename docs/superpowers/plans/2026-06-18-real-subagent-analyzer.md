# Real SubagentAnalyzer (`claude -p`) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox steps. Toujours afficher la sortie des gates (jamais `>/dev/null`).

**Goal:** Brancher le 1ᵉʳ effet réel Python → Claude Code : l'ingestion par sous-agent (`ClaudeSubagentAnalyzer`) via un adapter `claude -p`, opt-in par env, sans casser le déterminisme CI.

**Architecture:** Paquet `conductor/harness/` : `CliRunner`/`SubprocessClaudeCli` (shelle `claude -p … --output-format json`), `ClaudeSubagentAnalyzer` (hybride : faits heuristiques + interprétation agent, fallback gracieux), `resolve_analyzer()` (réel si `CONDUCTOR_USE_CLAUDE_ANALYZER=1` + `claude` présent, sinon `HeuristicAnalyzer`). Les onramps prennent leur analyzer par défaut du résolveur.

**Tech Stack:** Python 3.11+, pydantic v2, pytest, ruff, mypy --strict, uv. Branche `epic-claude-analyzer` (depuis main). Réf. spec : `docs/superpowers/specs/2026-06-18-real-subagent-analyzer-design.md`.

---

## Task 1 : `CliRunner` + `SubprocessClaudeCli`

**Files:** Create `conductor/harness/__init__.py`, `conductor/harness/claude_cli.py`; Test `tests/test_claude_cli.py`.

- [ ] **Step 1: failing test `tests/test_claude_cli.py`**
```python
"""SubprocessClaudeCli : invoque `claude -p … --output-format json`, renvoie `result`."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from conductor.harness.claude_cli import SubprocessClaudeCli


def _completed(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["claude"], returncode=returncode, stdout=stdout, stderr="")


def test_returns_result_field(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "conductor.harness.claude_cli.subprocess.run",
        lambda *a, **k: _completed(json.dumps({"result": "analyse OK"})),
    )
    assert SubprocessClaudeCli().run("prompt", tmp_path) == "analyse OK"


def test_nonzero_exit_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "conductor.harness.claude_cli.subprocess.run", lambda *a, **k: _completed("", returncode=1)
    )
    with pytest.raises(RuntimeError, match="claude"):
        SubprocessClaudeCli().run("p", tmp_path)


def test_invalid_json_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "conductor.harness.claude_cli.subprocess.run", lambda *a, **k: _completed("pas du json")
    )
    with pytest.raises(RuntimeError, match="illisible|JSON"):
        SubprocessClaudeCli().run("p", tmp_path)


def test_missing_result_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "conductor.harness.claude_cli.subprocess.run",
        lambda *a, **k: _completed(json.dumps({"other": 1})),
    )
    with pytest.raises(RuntimeError, match="result"):
        SubprocessClaudeCli().run("p", tmp_path)


def test_timeout_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def _boom(*a: object, **k: object) -> object:
        raise subprocess.TimeoutExpired(cmd="claude", timeout=1)

    monkeypatch.setattr("conductor.harness.claude_cli.subprocess.run", _boom)
    with pytest.raises(RuntimeError, match="timeout"):
        SubprocessClaudeCli(timeout_s=1).run("p", tmp_path)
```

- [ ] **Step 2:** run `uv run pytest tests/test_claude_cli.py -v` → FAIL (module missing).

- [ ] **Step 3: create `conductor/harness/claude_cli.py`**
```python
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
            raise RuntimeError(f"claude CLI a échoué (code {proc.returncode}) : {proc.stderr[:500]}")
        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Sortie claude illisible (JSON invalide) : {proc.stdout[:200]}") from exc
        result = envelope.get("result")
        if not isinstance(result, str):
            raise RuntimeError("Enveloppe claude sans champ `result` exploitable.")
        return result
```
and `conductor/harness/__init__.py`:
```python
"""Pont Python → harness Claude Code (adapters `claude -p`)."""

from __future__ import annotations

from conductor.harness.claude_cli import CliRunner, SubprocessClaudeCli

__all__ = ["CliRunner", "SubprocessClaudeCli"]
```

- [ ] **Step 4:** run `uv run pytest tests/test_claude_cli.py -v` → PASS (5). Full suite (show output).

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/harness/__init__.py conductor/harness/claude_cli.py tests/test_claude_cli.py
git commit -m "feat(harness): CliRunner + SubprocessClaudeCli (claude -p) (real-analyzer)"
```

---

## Task 2 : `ClaudeSubagentAnalyzer` (hybride + fallback)

**Files:** Create `conductor/harness/analyzer.py`; Modify `conductor/harness/__init__.py`; Test `tests/test_claude_analyzer.py`.

- [ ] **Step 1: failing test `tests/test_claude_analyzer.py`**
```python
"""ClaudeSubagentAnalyzer : fusionne faits heuristiques + interprétation agent ; fallback gracieux."""

from __future__ import annotations

import json
from pathlib import Path

from conductor.harness.analyzer import ClaudeSubagentAnalyzer


class _FakeRunner:
    def __init__(self, output: str, *, boom: bool = False) -> None:
        self._output = output
        self._boom = boom

    def run(self, prompt: str, cwd: Path) -> str:
        if self._boom:
            raise RuntimeError("claude indisponible")
        return self._output


def _repo(tmp: Path) -> Path:
    (tmp / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp / "backend").mkdir()
    return tmp


def test_merges_facts_and_interpretation(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    payload = json.dumps({"summary": "API FastAPI", "conventions": ["ruff"], "debt": []})
    arch = ClaudeSubagentAnalyzer(runner=_FakeRunner(payload)).analyze(repo)
    assert arch["has_pyproject"] is True  # fait heuristique
    assert arch["summary"] == "API FastAPI"  # interprétation agent
    assert arch["conventions"] == ["ruff"]


def test_fallback_on_non_json(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    arch = ClaudeSubagentAnalyzer(runner=_FakeRunner("blabla pas json")).analyze(repo)
    assert arch["has_pyproject"] is True
    assert arch["interpretation"] == "indisponible"


def test_fallback_on_runner_error(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    arch = ClaudeSubagentAnalyzer(runner=_FakeRunner("", boom=True)).analyze(repo)
    assert arch["interpretation"] == "indisponible"
    assert "top_level" in arch  # faits heuristiques toujours présents
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: create `conductor/harness/analyzer.py`**
```python
"""ClaudeSubagentAnalyzer — ingestion hybride : faits heuristiques + interprétation sous-agent.

Implémente le protocole `Analyzer`. Les faits durs viennent de HeuristicAnalyzer (déterministes) ;
l'interprétation (résumé/conventions/dette) vient d'un sous-agent via le CLI `claude`. En cas
d'échec d'interprétation (erreur runner ou JSON invalide), on retombe sur les faits seuls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from conductor.harness.claude_cli import CliRunner, SubprocessClaudeCli
from conductor.onramp.analyzer import HeuristicAnalyzer

_PROMPT = (
    "Analyse le dépôt courant. Réponds UNIQUEMENT par un objet JSON avec les clés : "
    '"summary" (string), "conventions" (liste de strings), "debt" (liste de strings). '
    "Aucun texte hors du JSON."
)


class ClaudeSubagentAnalyzer:
    """Analyzer hybride : HeuristicAnalyzer (faits) + sous-agent claude (interprétation)."""

    def __init__(self, *, runner: CliRunner | None = None) -> None:
        self._runner: CliRunner = runner or SubprocessClaudeCli()
        self._heuristic = HeuristicAnalyzer()

    def analyze(self, repo_path: Path) -> dict[str, Any]:
        facts = self._heuristic.analyze(repo_path)
        try:
            raw = self._runner.run(_PROMPT, repo_path)
            interpretation = json.loads(raw)
            if not isinstance(interpretation, dict):
                raise ValueError("interprétation non-objet")
        except (RuntimeError, ValueError, json.JSONDecodeError):
            return {**facts, "interpretation": "indisponible"}
        return {**facts, **interpretation}
```
Update `conductor/harness/__init__.py` to also export it:
```python
"""Pont Python → harness Claude Code (adapters `claude -p`)."""

from __future__ import annotations

from conductor.harness.analyzer import ClaudeSubagentAnalyzer
from conductor.harness.claude_cli import CliRunner, SubprocessClaudeCli

__all__ = ["ClaudeSubagentAnalyzer", "CliRunner", "SubprocessClaudeCli"]
```

- [ ] **Step 4:** run `uv run pytest tests/test_claude_analyzer.py -v` → PASS (3). Full suite.

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/harness/analyzer.py conductor/harness/__init__.py tests/test_claude_analyzer.py
git commit -m "feat(harness): ClaudeSubagentAnalyzer hybride + fallback (real-analyzer)"
```

---

## Task 3 : `resolve_analyzer()` + branchement des onramps

**Files:** Create `conductor/harness/resolve.py`; Modify `conductor/harness/__init__.py`, `conductor/onramp/adapter_onramp.py`, `conductor/onramp/builder_onramp.py`; Test `tests/test_resolve_analyzer.py`.

- [ ] **Step 1: failing test `tests/test_resolve_analyzer.py`**
```python
"""resolve_analyzer : réel si env=1 ET claude présent ; sinon HeuristicAnalyzer."""

from __future__ import annotations

import pytest

from conductor.harness.analyzer import ClaudeSubagentAnalyzer
from conductor.harness.resolve import resolve_analyzer
from conductor.onramp.analyzer import HeuristicAnalyzer


def test_default_is_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONDUCTOR_USE_CLAUDE_ANALYZER", raising=False)
    assert isinstance(resolve_analyzer(), HeuristicAnalyzer)


def test_env_off_is_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_USE_CLAUDE_ANALYZER", "0")
    assert isinstance(resolve_analyzer(), HeuristicAnalyzer)


def test_env_on_with_claude_is_subagent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_USE_CLAUDE_ANALYZER", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: "/usr/bin/claude")
    assert isinstance(resolve_analyzer(), ClaudeSubagentAnalyzer)


def test_env_on_without_claude_is_heuristic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_USE_CLAUDE_ANALYZER", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: None)
    assert isinstance(resolve_analyzer(), HeuristicAnalyzer)
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: create `conductor/harness/resolve.py`**
```python
"""Sélecteur d'Analyzer : sous-agent réel (opt-in) ou heuristique déterministe (défaut)."""

from __future__ import annotations

import os
import shutil

from conductor.harness.analyzer import ClaudeSubagentAnalyzer
from conductor.onramp.analyzer import Analyzer, HeuristicAnalyzer


def resolve_analyzer() -> Analyzer:
    """ClaudeSubagentAnalyzer si CONDUCTOR_USE_CLAUDE_ANALYZER=1 ET `claude` présent ; sinon heuristique."""
    if os.environ.get("CONDUCTOR_USE_CLAUDE_ANALYZER") == "1" and shutil.which("claude") is not None:
        return ClaudeSubagentAnalyzer()
    return HeuristicAnalyzer()
```
Add `resolve_analyzer` to `conductor/harness/__init__.py` exports:
```python
from conductor.harness.analyzer import ClaudeSubagentAnalyzer
from conductor.harness.claude_cli import CliRunner, SubprocessClaudeCli
from conductor.harness.resolve import resolve_analyzer

__all__ = ["ClaudeSubagentAnalyzer", "CliRunner", "SubprocessClaudeCli", "resolve_analyzer"]
```

- [ ] **Step 3b: wire onramps** — in `conductor/onramp/adapter_onramp.py` and `conductor/onramp/builder_onramp.py`, change the default analyzer from `HeuristicAnalyzer()` to `resolve_analyzer()`:
  - Replace import `from conductor.onramp.analyzer import Analyzer, HeuristicAnalyzer` with `from conductor.onramp.analyzer import Analyzer` and add `from conductor.harness.resolve import resolve_analyzer`.
  - In `__init__`, change `self._analyzer = analyzer or HeuristicAnalyzer()` to `self._analyzer = analyzer or resolve_analyzer()`.

  ⚠ IMPORT-CYCLE WATCH: `onramp.adapter_onramp` → `harness.resolve` → `harness.analyzer` → `onramp.analyzer` (a leaf submodule, no dependency on `onramp/__init__`). This should NOT cycle. RUN THE FULL SUITE to confirm. If a circular import appears at collection time, switch to a LAZY import inside `prepare` (`from conductor.harness.resolve import resolve_analyzer` at call time, `analyzer = self._analyzer or resolve_analyzer()`) and report the change.

- [ ] **Step 4:** run `uv run pytest tests/test_resolve_analyzer.py -v` → PASS (4). Full suite (show output) — existing adapter/builder tests still green (env off → HeuristicAnalyzer, same behavior).

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/harness/ conductor/onramp/adapter_onramp.py conductor/onramp/builder_onramp.py tests/test_resolve_analyzer.py
git commit -m "feat(harness): resolve_analyzer (opt-in env) + branchement des onramps (real-analyzer)"
```

---

## Task 4 : test d'intégration *gated* + note run pilote

**Files:** Create `tests/test_claude_integration.py`; Modify `docs/conductor-run-playbook.md`.

- [ ] **Step 1: create `tests/test_claude_integration.py`**
```python
"""Intégration RÉELLE de l'analyzer sous-agent — GATED.

Sauté sauf RUN_CLAUDE_INTEGRATION=1 ET CLI `claude` présent. Sert de mode d'emploi exécutable
du run pilote ; ne tourne jamais en CI standard (réseau/auth/tokens)."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_CLAUDE_INTEGRATION") != "1" or shutil.which("claude") is None,
    reason="intégration claude désactivée (RUN_CLAUDE_INTEGRATION!=1 ou claude absent)",
)


def test_real_claude_analyzer_on_fixture(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='pilot'\n", encoding="utf-8")
    (tmp_path / "backend").mkdir()
    from conductor.harness.analyzer import ClaudeSubagentAnalyzer

    arch = ClaudeSubagentAnalyzer().analyze(tmp_path)
    assert arch["has_pyproject"] is True
    # interprétation présente, ou fallback gracieux si l'agent n'a pas renvoyé de JSON exploitable
    assert "summary" in arch or arch.get("interpretation") == "indisponible"
```

- [ ] **Step 2:** run `uv run pytest tests/test_claude_integration.py -v` → **SKIPPED** (env off) — c'est le comportement attendu en CI.

- [ ] **Step 3: documenter le run pilote** — dans `docs/conductor-run-playbook.md` (EN canonique), ajouter une courte sous-section avant `## License` :
```markdown
## Real ingestion (pilot)

Ingestion is heuristic by default (deterministic, no network). To enable the **real
sub-agent analyzer** (`claude -p`), set `CONDUCTOR_USE_CLAUDE_ANALYZER=1` (requires the
`claude` CLI authenticated). The gated integration test documents the path:
`RUN_CLAUDE_INTEGRATION=1 uv run pytest tests/test_claude_integration.py`.
```

- [ ] **Step 4:** full gate (show output) — `uv run ruff check . ; uv run mypy ; uv run pytest` (le test d'intégration apparaît `skipped`, le reste vert).

- [ ] **Step 5: commit**
```
git add tests/test_claude_integration.py docs/conductor-run-playbook.md
git commit -m "test(harness): intégration claude gated + note run pilote (real-analyzer)"
```

---

## Définition de fin
- [ ] ruff clean · mypy success · pytest vert (intégration *skipped* en CI)
- [ ] Onramps : défaut heuristique en CI (env off) ; réel opt-in via `CONDUCTOR_USE_CLAUDE_ANALYZER=1`
- [ ] Aucun appel `claude` involontaire dans la suite standard
- [ ] Pas de cycle d'import (suite verte au collect)

## Self-Review (effectuée)
**Couverture spec :** `CliRunner`/`SubprocessClaudeCli` (T1) ; `ClaudeSubagentAnalyzer` hybride + fallback (T2) ; `resolve_analyzer` opt-in + branchement onramps (T3) ; test gated + doc pilote (T4). Hors périmètre (/bad, BMAD, flip défaut) explicitement exclu. **Placeholders :** aucun. **Types :** `CliRunner.run(prompt,cwd)->str` consommé par `ClaudeSubagentAnalyzer` ; `resolve_analyzer()->Analyzer` (protocole onramp) branché dans les onramps ; fusion `dict[str,Any]` cohérente avec `Substrate.arch_map`.
