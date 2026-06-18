# Real BMAD planner (`claude -p`) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox steps. Toujours afficher la sortie des gates (jamais `>/dev/null`).

**Goal:** 3ᵉ et dernier effet réel — déclencher la planification BMAD via le pont `CliRunner`, observée par lecture d'`epics.md`, gated par HITL 1, opt-in env.

**Architecture:** `ClaudeCliBmadPlanner` (implémente `BmadPlanner` : `plan(substrate)` → trigger `claude -p` + lit `_bmad-output/planning-artifacts/epics.md`), `resolve_bmad_planner()` (opt-in `CONDUCTOR_ENABLE_REAL_BMAD=1`), branchement lazy de `lancer_planification` + `ComplementPlanner`. Réf. spec : `docs/superpowers/specs/2026-06-18-real-bmad-planner-design.md`.

**Tech Stack:** Python 3.11+, pydantic v2, pytest, ruff, mypy --strict, uv. Branche `epic-real-bmad` (depuis main).

---

## Task 1 : `ClaudeCliBmadPlanner`

**Files:** Create `conductor/harness/bmad_planner.py`; Modify `conductor/harness/__init__.py`; Test `tests/test_bmad_planner.py`.

- [ ] **Step 1: failing test `tests/test_bmad_planner.py`**
```python
"""ClaudeCliBmadPlanner : déclenche la planif BMAD (claude -p) puis observe epics.md."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.governance import HitlPending
from conductor.harness.bmad_planner import ClaudeCliBmadPlanner
from conductor.onramp.base import Substrate
from conductor.profiles import FASTAPI_SAAS


class _FakeCli:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def run(self, prompt: str, cwd: Path) -> str:
        self.prompts.append(prompt)
        return "planifié"


def _substrate(tmp: Path) -> Substrate:
    return Substrate(repo_path=tmp, profile=FASTAPI_SAAS, design_md_path=tmp / "d.md")


def test_plan_triggers_and_reads_epics(tmp_path: Path) -> None:
    planning = tmp_path / "_bmad-output" / "planning-artifacts"
    planning.mkdir(parents=True)
    (planning / "epics.md").write_text("# Epics\n", encoding="utf-8")
    cli = _FakeCli()
    plan = ClaudeCliBmadPlanner(cli=cli).plan(_substrate(tmp_path))
    assert cli.prompts and "BMAD" in cli.prompts[0]
    assert plan.epics_md == planning / "epics.md"
    assert plan.hitl1_approved is False
    assert plan.stories == []


def test_plan_raises_hitl_pending_if_no_epics(tmp_path: Path) -> None:
    with pytest.raises(HitlPending, match="BMAD|epics"):
        ClaudeCliBmadPlanner(cli=_FakeCli()).plan(_substrate(tmp_path))
```

- [ ] **Step 2:** run `uv run pytest tests/test_bmad_planner.py -v` → FAIL.

- [ ] **Step 3: create `conductor/harness/bmad_planner.py`**
```python
"""ClaudeCliBmadPlanner — planification BMAD réelle déclenchée via le CLI claude.

Déclenche la planification agentique (PRD/architecture/epics) puis OBSERVE les artefacts écrits
dans _bmad-output/planning-artifacts/. Gated par HITL 1 en aval. skip_permissions car la planif
écrit des fichiers / lance npx en headless. stories=[] : BAD reconstruit le graphe (spike S-1).
"""

from __future__ import annotations

from pathlib import Path

from conductor.contracts import BmadPlan
from conductor.governance import HitlPending
from conductor.harness.claude_cli import CliRunner, SubprocessClaudeCli
from conductor.onramp.base import Substrate

_PLANNING_DIR = Path("_bmad-output/planning-artifacts")
_TRIGGER = (
    "Installe BMAD-METHOD (npx bmad-method install --modules bmm,tea) puis lance la planification "
    "BMAD : produis PRD, architecture, epics et stories dans "
    "_bmad-output/planning-artifacts/epics.md."
)


class ClaudeCliBmadPlanner:
    """Implémente BmadPlanner : déclenche la planif BMAD réelle puis collecte les artefacts."""

    def __init__(self, *, cli: CliRunner | None = None) -> None:
        self._cli = cli or SubprocessClaudeCli(skip_permissions=True)

    def plan(self, substrate: Substrate) -> BmadPlan:
        self._cli.run(_TRIGGER, substrate.repo_path)
        planning = substrate.repo_path / _PLANNING_DIR
        epics = planning / "epics.md"
        if not epics.exists():
            raise HitlPending(
                f"Planification BMAD : {epics} introuvable après déclenchement. "
                "Produire/valider le backlog, puis approuver (HITL 1)."
            )
        return BmadPlan(
            prd_path=planning / "PRD.md",
            architecture_path=planning / "architecture.md",
            epics_md=epics,
        )
```
Update `conductor/harness/__init__.py` : add `from conductor.harness.bmad_planner import ClaudeCliBmadPlanner` + `"ClaudeCliBmadPlanner"` to `__all__`.

- [ ] **Step 4:** run `uv run pytest tests/test_bmad_planner.py -v` → PASS (2). Full suite (show output).

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/harness/bmad_planner.py conductor/harness/__init__.py tests/test_bmad_planner.py
git commit -m "feat(harness): ClaudeCliBmadPlanner (planif BMAD réelle) (real-bmad)"
```

## Important (T1)
- Import cycle : `bmad_planner` importe `contracts`, `governance`, `harness.claude_cli`, `onramp.base` — PAS `bmad_bridge`. Vérifier la suite verte (collecte).
- `ClaudeCliBmadPlanner` satisfait `BmadPlanner` (protocole `plan(substrate)->BmadPlan`) structurellement.

---

## Task 2 : `resolve_bmad_planner()`

**Files:** Modify `conductor/harness/resolve.py`; Test `tests/test_resolve_bmad_planner.py`.

- [ ] **Step 1: failing test `tests/test_resolve_bmad_planner.py`**
```python
"""resolve_bmad_planner : ClaudeCliBmadPlanner si env=1 + claude ; sinon DefaultBmadPlanner."""

from __future__ import annotations

import pytest

from conductor.bmad_bridge import DefaultBmadPlanner
from conductor.harness.bmad_planner import ClaudeCliBmadPlanner
from conductor.harness.resolve import resolve_bmad_planner


def test_default_is_default_planner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONDUCTOR_ENABLE_REAL_BMAD", raising=False)
    assert isinstance(resolve_bmad_planner(), DefaultBmadPlanner)


def test_env_on_with_claude_is_real(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_ENABLE_REAL_BMAD", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: "/usr/bin/claude")
    assert isinstance(resolve_bmad_planner(), ClaudeCliBmadPlanner)


def test_env_on_without_claude_is_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_ENABLE_REAL_BMAD", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: None)
    assert isinstance(resolve_bmad_planner(), DefaultBmadPlanner)
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3:** in `conductor/harness/resolve.py`, extend the `TYPE_CHECKING` block and add the function (use existing `os`, `shutil`):
```python
if TYPE_CHECKING:
    from conductor.bmad_bridge import BmadPlanner
    from conductor.supervisor import BadRunner  # (déjà présent)
```
```python
def resolve_bmad_planner() -> "BmadPlanner":
    """ClaudeCliBmadPlanner si CONDUCTOR_ENABLE_REAL_BMAD=1 ET `claude` présent ; sinon défaut."""
    from conductor.bmad_bridge import DefaultBmadPlanner
    from conductor.harness.bmad_planner import ClaudeCliBmadPlanner

    if os.environ.get("CONDUCTOR_ENABLE_REAL_BMAD") == "1" and shutil.which("claude") is not None:
        return ClaudeCliBmadPlanner()
    return DefaultBmadPlanner()
```
(Adapt the `TYPE_CHECKING` block to whatever already exists — just ADD `BmadPlanner`; keep `BadRunner`.)

- [ ] **Step 4:** run `uv run pytest tests/test_resolve_bmad_planner.py -v` → PASS (3). Full suite (show output). Verify no cycle.

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/harness/resolve.py tests/test_resolve_bmad_planner.py
git commit -m "feat(harness): resolve_bmad_planner (opt-in) (real-bmad)"
```

---

## Task 3 : branchement lazy (`lancer_planification` + `ComplementPlanner`)

**Files:** Modify `conductor/bmad_bridge.py`, `conductor/planners/complement.py`; Test (append) `tests/test_bmad_bridge.py`.

- [ ] **Step 1: failing test (append `tests/test_bmad_bridge.py`)** — vérifie que le défaut `planner=None` passe par le résolveur :
```python
def test_lancer_planification_uses_resolver_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from conductor.harness import resolve as resolve_mod

    sentinel = BmadPlan(
        prd_path=Path("PRD.md"),
        architecture_path=Path("a.md"),
        epics_md=Path("e.md"),
    )

    class _Resolved:
        def plan(self, substrate: Substrate) -> BmadPlan:
            return sentinel

    monkeypatch.setattr(resolve_mod, "resolve_bmad_planner", lambda: _Resolved())
    plan = lancer_planification(_substrate(tmp_path), gate=ApproveGate())
    assert plan.hitl1_approved is True  # passé par _Resolved (sentinel) + HITL 1 approuvé
```
(Reuse the file's existing `_substrate` helper, `ApproveGate`, `BmadPlan`, `Substrate`, `Path` imports — add any missing import at top.)

- [ ] **Step 2:** run → FAIL (default still `DefaultBmadPlanner`).

- [ ] **Step 3a: `conductor/bmad_bridge.py`** — in `lancer_planification`, replace the default-planner resolution. Current:
```python
    plan = (planner or DefaultBmadPlanner()).plan(substrate)
```
→
```python
    if planner is None:
        from conductor.harness.resolve import resolve_bmad_planner

        planner = resolve_bmad_planner()
    plan = planner.plan(substrate)
```
(Keep `DefaultBmadPlanner` defined in `bmad_bridge.py` and the HITL-1 gate logic unchanged.)

- [ ] **Step 3b: `conductor/planners/complement.py`** — make `ComplementPlanner` resolve its inner lazily. Current `__init__` sets `self._inner = inner or DefaultBmadPlanner()`. Change to:
```python
    def __init__(self, inner: BmadPlanner | None = None) -> None:
        self._inner = inner  # résolu à l'appel si None

    def plan(self, substrate: Substrate) -> BmadPlan:
        inner = self._inner
        if inner is None:
            from conductor.harness.resolve import resolve_bmad_planner

            inner = resolve_bmad_planner()
        return inner.plan(substrate)
```
Remove the now-unused top-level `DefaultBmadPlanner` import in `complement.py` if it becomes unused (ruff F401) — but KEEP `BmadPlanner` import (used in the annotation).

- [ ] **Step 4:** run `uv run pytest tests/test_bmad_bridge.py tests/test_planners.py -v` → PASS. Full suite (show output). Existing tests (inject planner / inner) stay green. Verify no cycle.

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/bmad_bridge.py conductor/planners/complement.py tests/test_bmad_bridge.py
git commit -m "feat(real-bmad): branchement lazy resolve_bmad_planner (lancer_planification + Complement)"
```

## Important (T3)
- Cycle : `bmad_bridge`/`complement` importent `harness.resolve` **dans le corps de fonction** ; `resolve` importe `bmad_bridge`/`bmad_planner` **dans le corps**. Pas d'import top croisé. Si cycle au collect → STOP, BLOCKED.
- `ComplementPlanner` doit toujours satisfaire `BmadPlanner` (`plan(substrate)->BmadPlan`).

---

## Task 4 : note pilote (playbook EN)

**Files:** Modify `docs/conductor-run-playbook.md`.

- [ ] **Step 1:** ajouter après la section « Real autonomous sprint (`/bad`, pilot) » :
```markdown
## Real BMAD planning (pilot)

BMAD planning is collected by default (`DefaultBmadPlanner` installs BMAD and reads the
artifacts; HITL 1 pauses if absent). To enable **autonomous BMAD planning** via `claude -p`,
set `CONDUCTOR_ENABLE_REAL_BMAD=1` (requires `claude` authenticated). It only produces planning
documents under `_bmad-output/planning-artifacts/` and is always gated by **HITL 1** before any
development. No code is changed and nothing is merged at this stage.
```

- [ ] **Step 2:** full gate (show output) `uv run ruff check . ; uv run mypy ; uv run pytest`.

- [ ] **Step 3: commit**
```
git add docs/conductor-run-playbook.md
git commit -m "docs(real-bmad): note pilote planification BMAD (playbook)"
```

---

## Définition de fin
- [ ] ruff clean · mypy success · pytest vert (analyzer integration *skipped*)
- [ ] Défaut env-off → `DefaultBmadPlanner` (aucune planif autonome involontaire)
- [ ] HITL 1 inchangé ; `skip_permissions` confiné au planner réel ; pas de cycle d'import
- [ ] greenfield ET complément brownfield passent au réel si opt-in

## Self-Review (effectuée)
**Couverture spec :** `ClaudeCliBmadPlanner` (T1) ; `resolve_bmad_planner` opt-in (T2) ; branchement lazy lancer_planification + ComplementPlanner (T3) ; note pilote (T4). Hors périmètre (run réel automatisé, flip défaut, parsing stories) exclu. **Placeholders :** aucun. **Types :** `BmadPlanner.plan(substrate)->BmadPlan` cohérent ; `resolve_bmad_planner()->BmadPlanner` (lazy) ; `BmadPlan.stories=[]` (BAD reconstruit le graphe). **Sûreté :** opt-in, docs-only, HITL 1 garde-fou, skip_permissions confiné.
