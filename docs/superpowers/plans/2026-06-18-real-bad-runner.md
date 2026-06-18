# Real `/bad` runner (`claude -p` + `gh`) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox steps. Toujours afficher la sortie des gates (jamais `>/dev/null`).

**Goal:** 2ᵉ effet réel — exécution autonome de sprint par `/bad`, déclenchée via le pont `CliRunner`, observée via `gh`, sous posture de sécurité B (opt-in env, garde-fous natifs BAD, jamais de merge).

**Architecture:** `GhRunner`/`SubprocessGh` (observation PR), `SubprocessClaudeCli` étendu (`skip_permissions`), `ClaudeCliBadRunner` (implémente `BadRunner` : `run_sprint`/`remediate` via CliRunner+GhRunner), `resolve_bad_runner()` (opt-in `CONDUCTOR_ENABLE_REAL_BAD=1`), branchement lazy du superviseur. Réf. spec : `docs/superpowers/specs/2026-06-18-real-bad-runner-design.md`.

**Tech Stack:** Python 3.11+, pydantic v2, pytest, ruff, mypy --strict, uv. Branche `epic-real-bad` (depuis main).

---

## Task 1 : `GhRunner` + `SubprocessGh`

**Files:** Create `conductor/harness/gh.py`; Modify `conductor/harness/__init__.py`; Test `tests/test_gh.py`.

- [ ] **Step 1: failing test `tests/test_gh.py`**
```python
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


def test_list_prs_empty_output_is_empty_list(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("conductor.harness.gh.subprocess.run", lambda *a, **k: _completed(""))
    assert SubprocessGh().list_prs(tmp_path) == []


def test_list_prs_nonzero_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("conductor.harness.gh.subprocess.run", lambda *a, **k: _completed("", rc=1))
    with pytest.raises(RuntimeError, match="gh"):
        SubprocessGh().list_prs(tmp_path)
```

- [ ] **Step 2:** run `uv run pytest tests/test_gh.py -v` → FAIL.

- [ ] **Step 3: create `conductor/harness/gh.py`**
```python
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
```
Update `conductor/harness/__init__.py` to also export `GhRunner`, `SubprocessGh`:
```python
from conductor.harness.gh import GhRunner, SubprocessGh
```
(add both to `__all__`, keep existing exports).

- [ ] **Step 4:** run `uv run pytest tests/test_gh.py -v` → PASS (3). Full suite (show output).

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/harness/gh.py conductor/harness/__init__.py tests/test_gh.py
git commit -m "feat(harness): GhRunner + SubprocessGh (observation PR) (real-bad)"
```

---

## Task 2 : `SubprocessClaudeCli` étendu (`skip_permissions`)

**Files:** Modify `conductor/harness/claude_cli.py`; Test (append) `tests/test_claude_cli.py`.

- [ ] **Step 1: failing test (append `tests/test_claude_cli.py`)**
```python
def test_skip_permissions_adds_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, list[str]] = {}

    def _run(cmd: list[str], **k: object) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        return _completed(json.dumps({"result": "ok"}))

    monkeypatch.setattr("conductor.harness.claude_cli.subprocess.run", _run)
    SubprocessClaudeCli(skip_permissions=True).run("p", tmp_path)
    assert "--dangerously-skip-permissions" in captured["cmd"]


def test_default_has_no_skip_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    captured: dict[str, list[str]] = {}

    def _run(cmd: list[str], **k: object) -> subprocess.CompletedProcess[str]:
        captured["cmd"] = cmd
        return _completed(json.dumps({"result": "ok"}))

    monkeypatch.setattr("conductor.harness.claude_cli.subprocess.run", _run)
    SubprocessClaudeCli().run("p", tmp_path)
    assert "--dangerously-skip-permissions" not in captured["cmd"]
```

- [ ] **Step 2:** run `uv run pytest tests/test_claude_cli.py -v` → FAIL (unexpected kwarg / flag absent).

- [ ] **Step 3: modify `conductor/harness/claude_cli.py`** — add `skip_permissions` to `SubprocessClaudeCli.__init__` and the command:
```python
    def __init__(self, *, timeout_s: int = 300, skip_permissions: bool = False) -> None:
        self._timeout_s = timeout_s
        self._skip_permissions = skip_permissions

    def run(self, prompt: str, cwd: Path) -> str:
        cmd = ["claude", "-p", prompt, "--output-format", "json"]
        if self._skip_permissions:
            cmd.append("--dangerously-skip-permissions")
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=self._timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"claude CLI : timeout après {self._timeout_s}s") from exc
        ...  # le reste (returncode / json / result) inchangé
```
(Keep the rest of `run` exactly as-is.)

- [ ] **Step 4:** run `uv run pytest tests/test_claude_cli.py -v` → PASS (5 existing + 2 new = 7). Full suite (show output).

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/harness/claude_cli.py tests/test_claude_cli.py
git commit -m "feat(harness): SubprocessClaudeCli.skip_permissions (real-bad)"
```

---

## Task 3 : `ClaudeCliBadRunner`

**Files:** Create `conductor/harness/bad_runner.py`; Modify `conductor/harness/__init__.py`; Test `tests/test_bad_runner.py`.

- [ ] **Step 1: failing test `tests/test_bad_runner.py`**
```python
"""ClaudeCliBadRunner : déclenche /bad (CliRunner) puis observe les PR (GhRunner) → StoryOutcome."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from conductor.contracts import BadSprintLayout
from conductor.harness.bad_runner import ClaudeCliBadRunner


class _FakeCli:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def run(self, prompt: str, cwd: Path) -> str:
        self.prompts.append(prompt)
        return "déclenché"


class _FakeGh:
    def __init__(self, prs: list[dict[str, Any]]) -> None:
        self._prs = prs

    def list_prs(self, cwd: Path) -> list[dict[str, Any]]:
        return self._prs


def _layout(tmp: Path) -> BadSprintLayout:
    return BadSprintLayout(
        project_root=tmp,
        epics_md=tmp / "epics.md",
        sprint_status_yaml=tmp / "s.yaml",
        bmad_config_yaml=tmp / "c.yaml",
    )


def _pr(branch: str, *, ok: bool, url: str = "u") -> dict[str, Any]:
    rollup = [{"conclusion": "SUCCESS"}] if ok else [{"conclusion": "FAILURE"}]
    return {"number": 1, "headRefName": branch, "statusCheckRollup": rollup, "url": url}


def test_run_sprint_maps_prs_to_outcomes(tmp_path: Path) -> None:
    gh = _FakeGh([_pr("story-1-1-login", ok=True, url="http://pr/1")])
    runner = ClaudeCliBadRunner(cli=_FakeCli(), gh=gh)
    outcomes = runner.run_sprint(_layout(tmp_path))
    assert len(outcomes) == 1
    assert outcomes[0].story_id == "story-1-1-login"
    assert outcomes[0].code_ok is True
    assert outcomes[0].pr_url == "http://pr/1"


def test_run_sprint_triggers_bad(tmp_path: Path) -> None:
    cli = _FakeCli()
    ClaudeCliBadRunner(cli=cli, gh=_FakeGh([])).run_sprint(_layout(tmp_path))
    assert cli.prompts and "BAD" in cli.prompts[0]


def test_code_ok_false_on_failed_check(tmp_path: Path) -> None:
    gh = _FakeGh([_pr("story-2-1-x", ok=False)])
    outcomes = ClaudeCliBadRunner(cli=_FakeCli(), gh=gh).run_sprint(_layout(tmp_path))
    assert outcomes[0].code_ok is False


def test_remediate_reobserves_target_story(tmp_path: Path) -> None:
    gh = _FakeGh([_pr("story-3-1-x", ok=True, url="http://pr/3")])
    out = ClaudeCliBadRunner(cli=_FakeCli(), gh=gh).remediate("story-3-1-x", _layout(tmp_path))
    assert out.story_id == "story-3-1-x"
    assert out.pr_url == "http://pr/3"
```

- [ ] **Step 2:** run `uv run pytest tests/test_bad_runner.py -v` → FAIL.

- [ ] **Step 3: create `conductor/harness/bad_runner.py`**
```python
"""ClaudeCliBadRunner — exécution réelle du sprint par le skill /bad.

Déclenche /bad via le CLI `claude` (autonome, 1 worktree/story) puis OBSERVE le résultat via
`gh pr list` (source de vérité). N'auto-merge jamais : AUTO_PR_MERGE=false est garanti par le
type (`BadConfig.auto_pr_merge: Literal[False]`). Posture B : opt-in env + garde-fous natifs BAD.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from conductor.contracts import BadSprintLayout, StoryOutcome
from conductor.harness.claude_cli import CliRunner, SubprocessClaudeCli
from conductor.harness.gh import GhRunner, SubprocessGh

_TRIGGER = (
    "run BAD : lance le sprint autonome (un worktree git par story, pipeline 7 étapes). "
    "Ne merge AUCUNE PR (AUTO_PR_MERGE=false) ; ouvre les PR pour revue humaine."
)
_REMEDIATE = "BAD : reprends la story {story_id} pour corriger les gates en échec, sans merger."

_FAIL = {"FAILURE", "ERROR", "CANCELLED", "TIMED_OUT", "ACTION_REQUIRED", "FAILING", "FAILED"}


def _code_ok(rollup: list[dict[str, Any]]) -> bool:
    """Vrai si au moins un check et aucun en échec (état CI consolidé de la PR)."""
    if not rollup:
        return False
    for check in rollup:
        status = str(check.get("conclusion") or check.get("state") or "").upper()
        if status in _FAIL:
            return False
    return True


def _to_outcome(pr: dict[str, Any]) -> StoryOutcome:
    return StoryOutcome(
        story_id=str(pr.get("headRefName", "")),
        code_ok=_code_ok(pr.get("statusCheckRollup") or []),
        pr_url=pr.get("url"),
    )


class ClaudeCliBadRunner:
    """Implémente BadRunner : /bad réel (CliRunner) + observation via GhRunner."""

    def __init__(self, *, cli: CliRunner | None = None, gh: GhRunner | None = None) -> None:
        self._cli = cli or SubprocessClaudeCli(skip_permissions=True)
        self._gh = gh or SubprocessGh()

    def run_sprint(self, layout: BadSprintLayout) -> list[StoryOutcome]:
        self._cli.run(_TRIGGER, layout.project_root)  # /bad autonome ; ouvre des PR
        return [_to_outcome(pr) for pr in self._gh.list_prs(layout.project_root)]

    def remediate(self, story_id: str, layout: BadSprintLayout) -> StoryOutcome:
        self._cli.run(_REMEDIATE.format(story_id=story_id), layout.project_root)
        for pr in self._gh.list_prs(layout.project_root):
            if str(pr.get("headRefName", "")) == story_id:
                return _to_outcome(pr)
        return StoryOutcome(story_id=story_id, code_ok=False)
```
Update `conductor/harness/__init__.py` : export `ClaudeCliBadRunner` (add import + `__all__`).

- [ ] **Step 4:** run `uv run pytest tests/test_bad_runner.py -v` → PASS (4). Full suite (show output).

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/harness/bad_runner.py conductor/harness/__init__.py tests/test_bad_runner.py
git commit -m "feat(harness): ClaudeCliBadRunner (/bad réel + observation gh) (real-bad)"
```

---

## Task 4 : `resolve_bad_runner()` + branchement lazy du superviseur

**Files:** Modify `conductor/harness/resolve.py`, `conductor/supervisor.py`; Test `tests/test_resolve_bad_runner.py`.

- [ ] **Step 1: failing test `tests/test_resolve_bad_runner.py`**
```python
"""resolve_bad_runner : ClaudeCliBadRunner si env=1 + claude + gh ; sinon DefaultBadRunner."""

from __future__ import annotations

import pytest

from conductor.harness.bad_runner import ClaudeCliBadRunner
from conductor.harness.resolve import resolve_bad_runner
from conductor.supervisor import DefaultBadRunner


def test_default_is_default_bad_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONDUCTOR_ENABLE_REAL_BAD", raising=False)
    assert isinstance(resolve_bad_runner(), DefaultBadRunner)


def test_env_on_with_tools_is_real(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_ENABLE_REAL_BAD", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: "/usr/bin/x")
    assert isinstance(resolve_bad_runner(), ClaudeCliBadRunner)


def test_env_on_without_tools_is_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_ENABLE_REAL_BAD", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: None)
    assert isinstance(resolve_bad_runner(), DefaultBadRunner)
```

- [ ] **Step 2:** run `uv run pytest tests/test_resolve_bad_runner.py -v` → FAIL.

- [ ] **Step 3a: add `resolve_bad_runner` to `conductor/harness/resolve.py`**
Add at top (for the mypy annotation only) :
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from conductor.supervisor import BadRunner
```
Add the function:
```python
def resolve_bad_runner() -> "BadRunner":
    """ClaudeCliBadRunner si CONDUCTOR_ENABLE_REAL_BAD=1 ET `claude`+`gh` présents ; sinon stub."""
    from conductor.harness.bad_runner import ClaudeCliBadRunner
    from conductor.supervisor import DefaultBadRunner

    enabled = os.environ.get("CONDUCTOR_ENABLE_REAL_BAD") == "1"
    tools = shutil.which("claude") is not None and shutil.which("gh") is not None
    if enabled and tools:
        return ClaudeCliBadRunner()
    return DefaultBadRunner()
```
(`os` and `shutil` are already imported in `resolve.py`.)

- [ ] **Step 3b: wire the supervisor** (`conductor/supervisor.py`) — replace the line that builds the default runner (`runner = bad or DefaultBadRunner()`, near the top of `superviser`) with a lazy resolver:
```python
    if bad is not None:
        runner = bad
    else:
        from conductor.harness.resolve import resolve_bad_runner

        runner = resolve_bad_runner()
```
(Keep `DefaultBadRunner` defined in `supervisor.py` as-is; it's still the fallback returned by the resolver. Everything else in `superviser` unchanged.)

- [ ] **Step 4:** run `uv run pytest tests/test_resolve_bad_runner.py -v` → PASS (3). Full suite (show output) — existing supervisor tests inject a fake `bad`, so they're unaffected; verify NO import cycle (suite green at collection).

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/harness/resolve.py conductor/supervisor.py tests/test_resolve_bad_runner.py
git commit -m "feat(harness): resolve_bad_runner (opt-in) + branchement lazy du superviseur (real-bad)"
```

⚠ IMPORT-CYCLE : `resolve.py` importe `supervisor` et `bad_runner` **dans la fonction** (lazy) ; `supervisor` importe `resolve` **dans superviser** (lazy). Aucun import top-level croisé → pas de cycle. Si un cycle apparaît, signaler BLOCKED.

---

## Task 5 : note de sûreté & run pilote (playbook + spec)

**Files:** Modify `docs/conductor-run-playbook.md` (EN canonique).

- [ ] **Step 1:** ajouter une sous-section avant la fin du playbook EN (après « Real ingestion (pilot) ») :
```markdown
## Real autonomous sprint (`/bad`, pilot)

The autonomous BAD sprint is **off by default**. To enable it, set
`CONDUCTOR_ENABLE_REAL_BAD=1` (requires `claude` and `gh` authenticated). Safety posture:
the run uses BAD's native isolation (one git worktree per story), `AUTO_PR_MERGE=false` is
type-locked (never auto-merges), and HITL 2 still gates every merge. `/bad` runs with
`--dangerously-skip-permissions` and relaxed network isolation — **only run it on a repo whose
`main` is branch-protected, never on sensitive client code without review**. Results are
observed via `gh pr list` (source of truth).
```

- [ ] **Step 2:** full gate (show output) `uv run ruff check . ; uv run mypy ; uv run pytest` (tout vert ; intégration analyzer toujours *skipped*).

- [ ] **Step 3: commit**
```
git add docs/conductor-run-playbook.md
git commit -m "docs(real-bad): note sûreté & run pilote /bad (playbook)"
```

---

## Définition de fin
- [ ] ruff clean · mypy success · pytest vert (analyzer integration *skipped*)
- [ ] Défaut env-off → `DefaultBadRunner` (aucune autonomie involontaire)
- [ ] `--dangerously-skip-permissions` ajouté uniquement par le BAD runner réel
- [ ] Pas de cycle d'import · HITL 2 + `AUTO_PR_MERGE=false` intacts

## Self-Review (effectuée)
**Couverture spec :** `GhRunner`/`SubprocessGh` (T1) ; `skip_permissions` (T2) ; `ClaudeCliBadRunner` run_sprint/remediate/mapping (T3) ; `resolve_bad_runner` opt-in + branchement lazy (T4) ; note sûreté/pilote (T5). Hors périmètre (BMAD, vrai run automatisé, flip défaut) exclu. **Placeholders :** aucun. **Types :** `GhRunner.list_prs->list[dict]` → `_to_outcome` → `StoryOutcome` ; `CliRunner.run(prompt,cwd)->str` réutilisé ; `resolve_bad_runner()->BadRunner` (protocole supervisor) branché lazy ; `auto_pr_merge` garanti `Literal[False]` (pas de check runtime mort). **Sûreté :** opt-in bruyant, skip-permissions confiné, jamais de merge.
