# Brownfield BA — Branche A (SaaS générés par la forge) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reprendre un SaaS **généré par la forge** (même stack/conventions) pour le **remédier** et/ou le **compléter**, via le flux unifié A→E, avec capture de baseline, gate de non-régression et les 2 HITL.

**Architecture:** Onramp brownfield `NoOnramp` (vérifie les marqueurs cible + capture une baseline) → planners enfichables `RemediationPlanner` (déterministe : tests/CI + design, depuis la baseline) et `ComplementPlanner` (réutilise `DefaultBmadPlanner`), composables via `CompositePlanner` → étape E enrichie d'un `RegressionGate` (do-no-harm). B0 a déjà posé `TargetProfile`, `Substrate`, `Onramp`, `select_onramp`, le pipeline sur `Substrate`. BA ne touche pas le greenfield (zéro régression).

**Tech Stack:** Python 3.11+, pydantic v2, pytest, ruff, mypy --strict, uv. Paquet `digitai-saas-forge/conductor`.

**Pré-requis :** B0 mergé sur `main`. Brancher depuis `main` : `git checkout main && git pull && git checkout -b epic-ba-branch-a`.

---

## File Structure

- **Modify** `conductor/contracts.py` — `MissionConfig` += `existing_repo`, `brownfield_intent` ; `GateName` += `"regression"` ; `BadSprintLayout` += `baseline`.
- **Modify** `conductor/cadrage.py` — `cadrer(..., existing_repo, intent)` + validation greenfield/brownfield.
- **Create** `conductor/onramp/no_onramp.py` — `capture_baseline` + `NoOnramp`.
- **Modify** `conductor/onramp/__init__.py` — `select_onramp` brownfield → `NoOnramp`.
- **Create** `conductor/gates/regression_gate.py` — `evaluate_regression` (pur).
- **Modify** `conductor/sprint_config.py` — `preparer_sprint(..., baseline=...)` remplit `BadSprintLayout.baseline`.
- **Modify** `conductor/supervisor.py` — gate de non-régression dans la boucle E.
- **Create** `conductor/planners/__init__.py`, `conductor/planners/remediation.py`, `conductor/planners/complement.py` — planners brownfield + composite.
- **Modify** `conductor/__main__.py` — `run()`/CLI brownfield (mode, repo, intent) + sélection de planner.
- **Tests** : `tests/test_no_onramp.py`, `tests/test_regression_gate.py`, `tests/test_planners.py`, `tests/test_brownfield_e2e.py` (create) ; `tests/test_cadrage.py`, `tests/test_sprint_config.py`, `tests/test_supervisor.py` (modify).

Commandes depuis `digitai-saas-forge/` : `uv run ruff check .`, `uv run mypy`, `uv run pytest`.

---

## Task 1 : `existing_repo` + `brownfield_intent` + validation de cadrage

**Files:** Modify `conductor/contracts.py`, `conductor/cadrage.py`; Test (append) `tests/test_cadrage.py`.

- [ ] **Step 1: Write failing tests (append to `tests/test_cadrage.py`)**

```python
from pathlib import Path

import pytest


def test_brownfield_requires_existing_repo() -> None:
    with pytest.raises(ValueError, match="existing_repo"):
        cadrer("idée", mode="brownfield")


def test_brownfield_with_repo_sets_fields() -> None:
    cfg = cadrer("idée", mode="brownfield", existing_repo=Path("/tmp/app"), intent="complement")
    assert cfg.existing_repo == Path("/tmp/app")
    assert cfg.brownfield_intent == "complement"


def test_greenfield_rejects_existing_repo() -> None:
    with pytest.raises(ValueError, match="greenfield"):
        cadrer("idée", existing_repo=Path("/tmp/app"))


def test_default_intent_is_remediation() -> None:
    cfg = cadrer("idée", mode="brownfield", existing_repo=Path("/tmp/app"))
    assert cfg.brownfield_intent == "remediation"
```
(`Path` / `pytest` may already be imported; keep imports at top, no duplicates.)

- [ ] **Step 2: Run, expect FAIL**

Run: `uv run pytest tests/test_cadrage.py -k "brownfield or intent or greenfield_rejects" -v`
Expected: FAIL (`existing_repo` / `brownfield_intent` unknown).

- [ ] **Step 3a: Extend `MissionConfig`** in `conductor/contracts.py`

Add these two fields right after the existing `mode` field of `MissionConfig`:
```python
    existing_repo: Path | None = None  # brownfield : repo cible existant (None en greenfield)
    brownfield_intent: Literal["remediation", "complement", "both"] = "remediation"
```

- [ ] **Step 3b: Validate in `cadrer`** (`conductor/cadrage.py`)

Add `existing_repo` and `intent` keyword params and validation. Update the signature:
```python
def cadrer(
    idea: str,
    *,
    mode: Literal["greenfield", "brownfield"] = "greenfield",
    existing_repo: Path | None = None,
    intent: Literal["remediation", "complement", "both"] = "remediation",
    target: str = "fastapi-saas",
    brand_charter: Path = DEFAULT_CHARTER,
    style_slug: str = DEFAULT_STYLE,
    budget: str | None = None,
    deadline: str | None = None,
    bricks: list[BrickChoice] | None = None,
) -> MissionConfig:
```
Right after the existing `if not idea.strip(): raise ValueError(...)` guard, add:
```python
    if mode == "brownfield" and existing_repo is None:
        raise ValueError("Le mode brownfield exige un existing_repo (repo cible existant).")
    if mode == "greenfield" and existing_repo is not None:
        raise ValueError("Le mode greenfield n'accepte pas d'existing_repo (on génère le repo).")
```
Add to the `MissionConfig(...)` constructor call: `existing_repo=existing_repo,` and `brownfield_intent=intent,`.

- [ ] **Step 4: Run, expect PASS**

Run: `uv run pytest tests/test_cadrage.py -v` — all green (existing 8 + new 4 = 12).

- [ ] **Step 5: Verify & commit**

```bash
uv run ruff check . && uv run mypy
git add conductor/contracts.py conductor/cadrage.py tests/test_cadrage.py
git commit -m "feat(ba): existing_repo + brownfield_intent + validation cadrage (BA)"
```

---

## Task 2 : `capture_baseline` + `NoOnramp` + routage brownfield

**Files:** Create `conductor/onramp/no_onramp.py`; Modify `conductor/onramp/__init__.py`; Test `tests/test_no_onramp.py`.

- [ ] **Step 1: Write the failing test `tests/test_no_onramp.py`**

```python
"""NoOnramp (branche A) : vérifie les marqueurs cible + capture une baseline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from conductor.cadrage import cadrer
from conductor.onramp import select_onramp
from conductor.onramp.no_onramp import NoOnramp, capture_baseline
from conductor.profiles import FASTAPI_SAAS


class _CodeRunner:
    def __init__(self, rc: int) -> None:
        self.rc = rc

    def run(self, command: str, cwd: Path) -> int:
        return self.rc


class _Linter:
    def __init__(self, report: dict[str, Any]) -> None:
        self.report = report

    def lint_json(self, design_md: Path) -> dict[str, Any]:
        return self.report


def test_capture_baseline_records_green_checks(tmp_path: Path) -> None:
    baseline = capture_baseline(
        tmp_path, FASTAPI_SAAS, code_runner=_CodeRunner(0), design_linter=_Linter({"findings": []})
    )
    assert baseline == {"code": True, "design": True}


def test_capture_baseline_marks_failing_code(tmp_path: Path) -> None:
    baseline = capture_baseline(
        tmp_path, FASTAPI_SAAS, code_runner=_CodeRunner(1), design_linter=_Linter({"findings": []})
    )
    assert baseline["code"] is False


def test_no_onramp_requires_target_markers(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="marqueurs"):
        NoOnramp().prepare(cadrer("idée", mode="brownfield", existing_repo=tmp_path), tmp_path)


def test_no_onramp_returns_substrate_with_baseline(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    onramp = NoOnramp(code_runner=_CodeRunner(0), design_linter=_Linter({"findings": []}))
    substrate = onramp.prepare(cadrer("idée", mode="brownfield", existing_repo=tmp_path), tmp_path)
    assert substrate.repo_path == tmp_path
    assert substrate.profile is FASTAPI_SAAS
    assert substrate.baseline == {"code": True, "design": True}


def test_select_onramp_brownfield_is_no_onramp() -> None:
    mission = cadrer("idée", mode="brownfield", existing_repo=Path("."))
    assert isinstance(select_onramp(mission), NoOnramp)
```

- [ ] **Step 2: Run, expect FAIL** — `uv run pytest tests/test_no_onramp.py -v` (module missing).

- [ ] **Step 3: Create `conductor/onramp/no_onramp.py`**

```python
"""NoOnramp — bretelle brownfield « branche A » : reprise d'un SaaS généré par la forge.

Ne génère rien : vérifie que le repo porte les marqueurs de la cible, puis capture une
BASELINE (statut vert/rouge des gates existants) qui servira au gate de non-régression (E).
Ingestion 100 % heuristique en BA (décision spec).
"""

from __future__ import annotations

from pathlib import Path

from conductor.contracts import MissionConfig
from conductor.gates.code_gate import CommandRunner, run_code_gate
from conductor.gates.design_gate import DesignLinter, run_design_gate
from conductor.onramp.base import Substrate
from conductor.profiles import FASTAPI_SAAS, TargetProfile


def capture_baseline(
    repo_path: Path,
    profile: TargetProfile,
    *,
    code_runner: CommandRunner | None = None,
    design_linter: DesignLinter | None = None,
) -> dict[str, bool]:
    """Statut vert/rouge des gates applicables AVANT toute intervention (do-no-harm)."""
    baseline: dict[str, bool] = {}
    if profile.code_check is not None:
        baseline["code"] = run_code_gate(repo_path, profile=profile, runner=code_runner).passed
    if profile.has_ui:
        design_md = repo_path / profile.design_md_path
        baseline["design"] = run_design_gate(design_md, linter=design_linter).passed
    return baseline


class NoOnramp:
    """Branche A : repo déjà sur la cible. Vérifie les marqueurs + capture la baseline."""

    def __init__(
        self,
        *,
        code_runner: CommandRunner | None = None,
        design_linter: DesignLinter | None = None,
    ) -> None:
        self._code_runner = code_runner
        self._design_linter = design_linter

    def prepare(self, config: MissionConfig, dest: Path) -> Substrate:
        repo = dest  # en brownfield, `dest` EST le repo existant
        if not (repo / "pyproject.toml").exists():
            raise ValueError(
                f"NoOnramp (branche A) attend un repo cible : marqueurs absents dans {repo} "
                "(pyproject.toml introuvable). Un repo non conforme relève de BC/BB."
            )
        baseline = capture_baseline(
            repo, FASTAPI_SAAS, code_runner=self._code_runner, design_linter=self._design_linter
        )
        return Substrate(
            repo_path=repo,
            profile=FASTAPI_SAAS,
            design_md_path=repo / FASTAPI_SAAS.design_md_path,
            baseline=baseline,
        )
```

- [ ] **Step 4: Route brownfield → `NoOnramp`** in `conductor/onramp/__init__.py`

Replace the body of `select_onramp` with:
```python
def select_onramp(mission: MissionConfig) -> Onramp:
    """Choisit la bretelle selon le mode/la distance à la cible.

    BA : brownfield → NoOnramp (branche A, repo déjà sur la cible). BC/BB ajouteront
    AdapterOnramp / BuilderOnramp selon la distance détectée.
    """
    if mission.mode == "greenfield":
        return ScaffoldOnramp()
    return NoOnramp(mission)
```
Wait — `NoOnramp()` takes only keyword runner args, not a mission. Use `return NoOnramp()`. Update imports: add `from conductor.onramp.no_onramp import NoOnramp` and ensure `MissionConfig` import is present (it is used in the signature; import `from conductor.contracts import MissionConfig`). Add `NoOnramp` to `__all__`. Final file:
```python
"""Onramps : sélection de la bretelle selon le mode/la distance à la cible."""

from __future__ import annotations

from conductor.contracts import MissionConfig
from conductor.onramp.base import Onramp, Substrate
from conductor.onramp.no_onramp import NoOnramp
from conductor.onramp.scaffold_onramp import ScaffoldOnramp

__all__ = ["NoOnramp", "Onramp", "ScaffoldOnramp", "Substrate", "select_onramp"]


def select_onramp(mission: MissionConfig) -> Onramp:
    """BA : brownfield → NoOnramp (branche A). BC/BB ajouteront Adapter/Builder."""
    if mission.mode == "greenfield":
        return ScaffoldOnramp()
    return NoOnramp()
```

- [ ] **Step 5: Run, expect PASS** — `uv run pytest tests/test_no_onramp.py -v` (5 tests). Then full suite.

- [ ] **Step 6: Verify & commit**

```bash
uv run ruff check . && uv run mypy && uv run pytest -q
git add conductor/onramp/no_onramp.py conductor/onramp/__init__.py tests/test_no_onramp.py
git commit -m "feat(ba): NoOnramp + capture_baseline + routage brownfield (BA)"
```

**Note:** if `select_onramp` returning `NoOnramp` breaks the B0 test `test_select_onramp_brownfield_not_yet_implemented` (which expected `NotImplementedError`), DELETE that obsolete test in `tests/test_onramp.py` (BA implements brownfield A now). Report the removal.

---

## Task 3 : `RegressionGate` (do-no-harm, pur)

**Files:** Modify `conductor/contracts.py` (extend `GateName`); Create `conductor/gates/regression_gate.py`; Test `tests/test_regression_gate.py`.

- [ ] **Step 1: Write the failing test `tests/test_regression_gate.py`**

```python
"""Gate de non-régression : un check vert dans la baseline ne doit pas passer au rouge."""

from __future__ import annotations

from conductor.gates.regression_gate import evaluate_regression


def test_no_regression_passes() -> None:
    v = evaluate_regression({"code": True, "design": True}, {"code": True, "design": True})
    assert v.passed is True
    assert v.gate == "regression"


def test_green_to_red_blocks() -> None:
    v = evaluate_regression({"code": True}, {"code": False})
    assert v.passed is False
    assert v.findings and v.findings[0]["check"] == "code"


def test_red_baseline_not_aggravated_passes() -> None:
    # un check déjà rouge à la baseline qui reste rouge n'est PAS une régression
    v = evaluate_regression({"code": False}, {"code": False})
    assert v.passed is True


def test_empty_baseline_passes() -> None:
    assert evaluate_regression({}, {"code": True}).passed is True
```

- [ ] **Step 2: Run, expect FAIL** — module missing.

- [ ] **Step 3a: Extend `GateName`** in `conductor/contracts.py`

Find `GateName = Literal["code", "design"]` and replace with:
```python
GateName = Literal["code", "design", "regression"]
```

- [ ] **Step 3b: Create `conductor/gates/regression_gate.py`**

```python
"""Gate de non-régression (do-no-harm, brownfield).

Compare le statut courant des checks à la BASELINE capturée à l'onramp : un check qui était
vert et passe au rouge est une régression bloquante (→ 3 retries puis escalade, comme un gate).
Fonction pure, testable hors-ligne.
"""

from __future__ import annotations

from conductor.contracts import GateVerdict


def evaluate_regression(baseline: dict[str, bool], current: dict[str, bool]) -> GateVerdict:
    """Bloque si un check vert dans `baseline` n'est plus vert dans `current`."""
    regressions = [
        name for name, was_green in baseline.items() if was_green and not current.get(name, False)
    ]
    return GateVerdict(
        gate="regression",
        passed=not regressions,
        findings=[{"check": name, "issue": "vert→rouge"} for name in regressions],
    )
```

- [ ] **Step 4: Run, expect PASS** (4 tests). Then full suite (existing GateVerdict tests still pass — the Literal widened).

- [ ] **Step 5: Verify & commit**

```bash
uv run ruff check . && uv run mypy && uv run pytest -q
git add conductor/contracts.py conductor/gates/regression_gate.py tests/test_regression_gate.py
git commit -m "feat(ba): RegressionGate (do-no-harm) (BA)"
```

---

## Task 4 : threader la baseline jusqu'à l'étape E

**Files:** Modify `conductor/contracts.py` (`BadSprintLayout`), `conductor/sprint_config.py`; Test (append) `tests/test_sprint_config.py`.

- [ ] **Step 1: Write the failing test (append `tests/test_sprint_config.py`)**

```python
def test_baseline_is_carried_into_layout(tmp_path: Path) -> None:
    plan = _plan(approved=True)
    layout = preparer_sprint(plan, tmp_path, baseline={"code": True, "design": False})
    assert layout.baseline == {"code": True, "design": False}


def test_baseline_defaults_to_none(tmp_path: Path) -> None:
    layout = preparer_sprint(_plan(approved=True), tmp_path)
    assert layout.baseline is None
```

- [ ] **Step 2: Run, expect FAIL** (`preparer_sprint` has no `baseline` kwarg / `BadSprintLayout` has no `baseline`).

- [ ] **Step 3a: Add field to `BadSprintLayout`** in `conductor/contracts.py`

Inside `class BadSprintLayout`, add after the `config` field:
```python
    baseline: dict[str, bool] | None = None  # statut des gates avant intervention (brownfield)
```

- [ ] **Step 3b: Thread it in `preparer_sprint`** (`conductor/sprint_config.py`)

Add a `baseline` keyword param and pass it to the returned `BadSprintLayout`:
```python
def preparer_sprint(
    plan: BmadPlan,
    project_root: Path,
    *,
    config: BadConfig | None = None,
    baseline: dict[str, bool] | None = None,
) -> BadSprintLayout:
```
In the `return BadSprintLayout(...)` call, add `baseline=baseline,`.

- [ ] **Step 4: Run, expect PASS** (existing 3 + new 2). Full suite green.

- [ ] **Step 5: Verify & commit**

```bash
uv run ruff check . && uv run mypy && uv run pytest -q
git add conductor/contracts.py conductor/sprint_config.py tests/test_sprint_config.py
git commit -m "feat(ba): baseline portée dans BadSprintLayout (BA)"
```

---

## Task 5 : intégrer le gate de non-régression dans le superviseur (E)

**Files:** Modify `conductor/supervisor.py`; Test (append) `tests/test_supervisor.py`.

- [ ] **Step 1: Write the failing test (append `tests/test_supervisor.py`)**

```python
from conductor.contracts import StoryOutcome


def test_regression_blocks_when_baseline_green_turns_red(tmp_path: Path) -> None:
    """Baseline code verte ; une story qui casse le code (code_ok=False) est bloquée par
    le gate de non-régression, même après retries."""
    layout = _layout(tmp_path)
    layout.baseline = {"code": True}
    bad = FakeBad([StoryOutcome(story_id="9.1", code_ok=False)])  # code rouge → régression
    report = superviser(layout, bad=bad, design_check=_design_pass, hitl=ApproveGate())
    assert report.results[0].status == "blocked"
    assert report.results[0].attempts == 4  # 1 + 3 retries


def test_no_regression_when_baseline_absent(tmp_path: Path) -> None:
    layout = _layout(tmp_path)  # baseline None
    bad = FakeBad([StoryOutcome(story_id="9.2", code_ok=True, pr_url="pr/9.2")])
    report = superviser(layout, bad=bad, design_check=_design_pass, hitl=ApproveGate())
    assert report.results[0].status == "ready-for-review"
```

- [ ] **Step 2: Run, expect FAIL** (regression not yet enforced — story would be `ready` or block for wrong reason).

- [ ] **Step 3: Add the regression check in `superviser`** (`conductor/supervisor.py`)

Add the import at the top:
```python
from conductor.gates.regression_gate import evaluate_regression
```
Inside `superviser`, replace the per-story gate evaluation so that BOTH the double gate AND the regression gate are checked. Replace the loop body's `passed = ...` computations with a helper that also consults the baseline. Concretely, change the two `passed = outcome.code_ok and check(outcome).passed` lines (initial + inside the while) to use:
```python
        def _passes(o: StoryOutcome) -> bool:
            design_ok = check(o).passed
            current = {"code": o.code_ok, "design": design_ok}
            no_regression = evaluate_regression(layout.baseline or {}, current).passed
            return o.code_ok and design_ok and no_regression
```
Define `_passes` once at the top of `superviser` (after `check` is resolved), then use `passed = _passes(outcome)` initially and `passed = _passes(outcome)` after each `remediate`. Keep the rest (attempts counter, StoryResult, HITL 2) unchanged.

- [ ] **Step 4: Run, expect PASS** — `uv run pytest tests/test_supervisor.py -v` (existing 4 + new 2). Full suite green.

- [ ] **Step 5: Verify & commit**

```bash
uv run ruff check . && uv run mypy && uv run pytest -q
git add conductor/supervisor.py tests/test_supervisor.py
git commit -m "feat(ba): gate de non-régression dans le superviseur (BA)"
```

---

## Task 6 : `RemediationPlanner` (déterministe : tests/CI + design)

**Files:** Create `conductor/planners/__init__.py`, `conductor/planners/remediation.py`; Test `tests/test_planners.py`.

- [ ] **Step 1: Write the failing test `tests/test_planners.py`**

```python
"""Planners brownfield : remédiation déterministe depuis la baseline (v1 tests/CI + design)."""

from __future__ import annotations

from pathlib import Path

from conductor.onramp.base import Substrate
from conductor.planners.remediation import RemediationPlanner
from conductor.profiles import FASTAPI_SAAS


def _substrate(tmp: Path, baseline: dict[str, bool]) -> Substrate:
    (tmp / "design").mkdir(parents=True, exist_ok=True)
    return Substrate(
        repo_path=tmp,
        profile=FASTAPI_SAAS,
        design_md_path=tmp / "design/DESIGN.md",
        baseline=baseline,
    )


def test_remediation_emits_story_for_red_code(tmp_path: Path) -> None:
    plan = RemediationPlanner().plan(_substrate(tmp_path, {"code": False, "design": True}))
    titles = [s.title for s in plan.stories]
    assert any("CI code" in t for t in titles)
    assert all("design" not in t.lower() for t in titles)  # design vert → pas de story design


def test_remediation_emits_story_for_red_design(tmp_path: Path) -> None:
    plan = RemediationPlanner().plan(_substrate(tmp_path, {"code": True, "design": False}))
    assert any("design" in s.title.lower() for s in plan.stories)


def test_remediation_all_green_yields_no_story(tmp_path: Path) -> None:
    plan = RemediationPlanner().plan(_substrate(tmp_path, {"code": True, "design": True}))
    assert plan.stories == []


def test_remediation_writes_epics_md(tmp_path: Path) -> None:
    plan = RemediationPlanner().plan(_substrate(tmp_path, {"code": False, "design": False}))
    assert plan.epics_md.exists()
    content = plan.epics_md.read_text(encoding="utf-8")
    assert "remediation" in content.lower()
    assert plan.hitl1_approved is False  # HITL 1 non franchi à ce stade
```

- [ ] **Step 2: Run, expect FAIL** — module missing.

- [ ] **Step 3: Create the package + planner**

`conductor/planners/__init__.py`:
```python
"""Planners brownfield : génération de backlog (remédiation / complément / composite)."""

from __future__ import annotations

from conductor.planners.remediation import RemediationPlanner

__all__ = ["RemediationPlanner"]
```

`conductor/planners/remediation.py`:
```python
"""RemediationPlanner — backlog de correctifs déterministe depuis la baseline.

v1 (décision spec) : couvre tests/CI + conformité design — les deux dimensions déjà
mesurables sans outillage neuf (baseline capturée à l'onramp). Sécurité/dette/upgrades
= incréments ultérieurs. Écrit epics.md dans la layout attendue par /bad (spike S-1b).
"""

from __future__ import annotations

from pathlib import Path

from conductor.contracts import BmadPlan, Story
from conductor.onramp.base import Substrate

PLANNING_DIR = Path("_bmad-output/planning-artifacts")


def _remediation_stories(baseline: dict[str, bool]) -> list[Story]:
    stories: list[Story] = []
    if baseline.get("code") is False:
        stories.append(
            Story(
                id="R1",
                epic="remediation",
                title="Rendre la CI code verte",
                acceptance=["Le gate code (ruff/mypy/pytest) passe", "Aucune régression introduite"],
            )
        )
    if baseline.get("design") is False:
        stories.append(
            Story(
                id="R2",
                epic="remediation",
                title="Mettre l'UI en conformité design (WCAG/refs)",
                acceptance=["Le lint design ne remonte aucun finding bloquant"],
            )
        )
    return stories


def _render_epics_md(stories: list[Story]) -> str:
    lines = ["# Epics — remediation", ""]
    for s in stories:
        lines.append(f"## Story {s.id} — {s.title}")
        for a in s.acceptance:
            lines.append(f"- [ ] {a}")
        lines.append("")
    return "\n".join(lines)


class RemediationPlanner:
    """Implémente le protocole BmadPlanner : substrat → BmadPlan (stories de correctif)."""

    def plan(self, substrate: Substrate) -> BmadPlan:
        baseline = substrate.baseline or {}
        stories = _remediation_stories(baseline)
        planning = substrate.repo_path / PLANNING_DIR
        planning.mkdir(parents=True, exist_ok=True)
        epics_md = planning / "epics.md"
        epics_md.write_text(_render_epics_md(stories), encoding="utf-8")
        return BmadPlan(
            prd_path=planning / "PRD.md",
            architecture_path=planning / "architecture.md",
            epics_md=epics_md,
            stories=stories,
        )
```

- [ ] **Step 4: Run, expect PASS** (4 tests). Full suite green.

- [ ] **Step 5: Verify & commit**

```bash
uv run ruff check . && uv run mypy && uv run pytest -q
git add conductor/planners/ tests/test_planners.py
git commit -m "feat(ba): RemediationPlanner déterministe (tests/CI + design) (BA)"
```

---

## Task 7 : `ComplementPlanner` + `CompositePlanner`

**Files:** Create `conductor/planners/complement.py`; Modify `conductor/planners/__init__.py`; Test (append) `tests/test_planners.py`.

- [ ] **Step 1: Write the failing test (append `tests/test_planners.py`)**

```python
from conductor.contracts import BmadPlan
from conductor.planners import ComplementPlanner, CompositePlanner


class _StubPlanner:
    def __init__(self, plan: BmadPlan) -> None:
        self._plan = plan

    def plan(self, substrate: Substrate) -> BmadPlan:
        return self._plan


def test_complement_delegates_to_inner(tmp_path: Path) -> None:
    inner_plan = BmadPlan(
        prd_path=tmp_path / "PRD.md",
        architecture_path=tmp_path / "arch.md",
        epics_md=tmp_path / "epics.md",
    )
    planner = ComplementPlanner(inner=_StubPlanner(inner_plan))
    assert planner.plan(_substrate(tmp_path, {})) is inner_plan


def test_composite_concatenates_stories(tmp_path: Path) -> None:
    from conductor.contracts import Story

    p1 = BmadPlan(
        prd_path=tmp_path / "PRD.md",
        architecture_path=tmp_path / "a.md",
        epics_md=tmp_path / "e1.md",
        stories=[Story(id="R1", epic="remediation", title="fix")],
    )
    p2 = BmadPlan(
        prd_path=tmp_path / "PRD.md",
        architecture_path=tmp_path / "a.md",
        epics_md=tmp_path / "e2.md",
        stories=[Story(id="C1", epic="complement", title="feature")],
    )
    composite = CompositePlanner(_StubPlanner(p1), _StubPlanner(p2))
    out = composite.plan(_substrate(tmp_path, {}))
    assert [s.id for s in out.stories] == ["R1", "C1"]
    assert out.epics_md == p1.epics_md  # epics_md de référence = celui du 1er planner (remédiation)
```

- [ ] **Step 2: Run, expect FAIL** — `ComplementPlanner` / `CompositePlanner` missing.

- [ ] **Step 3: Create `conductor/planners/complement.py`**

```python
"""ComplementPlanner (intention) — réutilise la planification BMAD greenfield sur l'existant.

BA : un complément sur un SaaS forge = lancer la planification BMAD habituelle DANS le repo
existant (le substrat). On délègue donc à DefaultBmadPlanner. CompositePlanner enchaîne deux
planners (remédiation puis complément) et fusionne leurs stories en un seul backlog.
"""

from __future__ import annotations

from conductor.bmad_bridge import BmadPlanner, DefaultBmadPlanner
from conductor.contracts import BmadPlan
from conductor.onramp.base import Substrate


class ComplementPlanner:
    """Délègue à un planner BMAD (DefaultBmadPlanner par défaut) sur le substrat existant."""

    def __init__(self, inner: BmadPlanner | None = None) -> None:
        self._inner = inner or DefaultBmadPlanner()

    def plan(self, substrate: Substrate) -> BmadPlan:
        return self._inner.plan(substrate)


class CompositePlanner:
    """Compose deux planners : backlog = stories du 1er + stories du 2nd (ex. remédiation + complément)."""

    def __init__(self, first: BmadPlanner, second: BmadPlanner) -> None:
        self._first = first
        self._second = second

    def plan(self, substrate: Substrate) -> BmadPlan:
        a = self._first.plan(substrate)
        b = self._second.plan(substrate)
        return a.model_copy(update={"stories": [*a.stories, *b.stories]})
```

Update `conductor/planners/__init__.py`:
```python
"""Planners brownfield : génération de backlog (remédiation / complément / composite)."""

from __future__ import annotations

from conductor.planners.complement import ComplementPlanner, CompositePlanner
from conductor.planners.remediation import RemediationPlanner

__all__ = ["ComplementPlanner", "CompositePlanner", "RemediationPlanner"]
```

- [ ] **Step 4: Run, expect PASS** (existing 4 + new 2 = 6). Full suite green.

- [ ] **Step 5: Verify & commit**

```bash
uv run ruff check . && uv run mypy && uv run pytest -q
git add conductor/planners/ tests/test_planners.py
git commit -m "feat(ba): ComplementPlanner + CompositePlanner (BA)"
```

---

## Task 8 : câblage `run()` / CLI brownfield + sélection de planner

**Files:** Modify `conductor/__main__.py`; Test (append) `tests/test_e2e_master.py`.

- [ ] **Step 1: Write the failing test (append `tests/test_e2e_master.py`)**

```python
def test_select_planner_maps_intent() -> None:
    from conductor.__main__ import _select_planner
    from conductor.cadrage import cadrer
    from conductor.planners import ComplementPlanner, CompositePlanner, RemediationPlanner

    repo = Path(".")
    assert _select_planner(cadrer("i")) is None  # greenfield → DefaultBmadPlanner (None)
    rem = cadrer("i", mode="brownfield", existing_repo=repo, intent="remediation")
    comp = cadrer("i", mode="brownfield", existing_repo=repo, intent="complement")
    both = cadrer("i", mode="brownfield", existing_repo=repo, intent="both")
    assert isinstance(_select_planner(rem), RemediationPlanner)
    assert isinstance(_select_planner(comp), ComplementPlanner)
    assert isinstance(_select_planner(both), CompositePlanner)
```

- [ ] **Step 2: Run, expect FAIL** — `_select_planner` missing.

- [ ] **Step 3: Add `_select_planner` + brownfield wiring in `conductor/__main__.py`**

Add imports:
```python
from conductor.bmad_bridge import BmadPlanner
from conductor.planners import ComplementPlanner, CompositePlanner, RemediationPlanner
```
Add the helper:
```python
def _select_planner(mission: MissionConfig) -> BmadPlanner | None:
    """Planner selon l'intention. None = DefaultBmadPlanner (greenfield / complément pur délégué)."""
    if mission.mode == "greenfield":
        return None
    intent = mission.brownfield_intent
    if intent == "remediation":
        return RemediationPlanner()
    if intent == "complement":
        return ComplementPlanner()
    return CompositePlanner(RemediationPlanner(), ComplementPlanner())
```
(`MissionConfig` must be imported in `__main__.py` — add `from conductor.contracts import MissionConfig` if absent.)

Replace `run()` to support brownfield (target path = existing repo) and planner/baseline wiring:
```python
def run(
    idea: str,
    *,
    mode: str = "greenfield",
    existing_repo: Path | None = None,
    intent: str = "remediation",
    workdir: Path = Path("generated"),
) -> None:
    """Orchestration A → B (onramp) → C (HITL 1) → D → E (HITL 2), greenfield ou brownfield."""
    mission = cadrer(
        idea,
        mode=mode,  # type: ignore[arg-type]
        existing_repo=existing_repo,
        intent=intent,  # type: ignore[arg-type]
    )
    target = existing_repo if mission.mode == "brownfield" else workdir / _slug(idea)
    assert target is not None
    substrate = select_onramp(mission).prepare(mission, target)  # B
    plan = lancer_planification(substrate, planner=_select_planner(mission))  # C — HITL 1
    layout = preparer_sprint(plan, target, baseline=substrate.baseline)  # D
    superviser(layout)  # E — HITL 2
```
Extend the argparse in `main()` for the `run` subparser:
```python
    run_p.add_argument("--mode", choices=["greenfield", "brownfield"], default="greenfield")
    run_p.add_argument("--repo", type=Path, default=None, help="repo cible existant (brownfield)")
    run_p.add_argument(
        "--intent", choices=["remediation", "complement", "both"], default="remediation"
    )
```
And update the dispatch `if args.command == "run":` to:
```python
        run(args.idea, mode=args.mode, existing_repo=args.repo, intent=args.intent)
```

- [ ] **Step 4: Run full gate** — `uv run ruff check . && uv run mypy && uv run pytest`. All green; the greenfield `run()` path unchanged in behavior (mode default greenfield).

- [ ] **Step 5: Commit**

```bash
git add conductor/__main__.py tests/test_e2e_master.py
git commit -m "feat(ba): câblage run()/CLI brownfield + sélection de planner (BA)"
```

---

## Task 9 : test d'intégration brownfield de bout en bout

**Files:** Create `tests/test_brownfield_e2e.py`.

- [ ] **Step 1: Write the test**

```python
"""Bout-en-bout brownfield (branche A) : NoOnramp → remédiation → D → E avec fakes.

Vérifie : reprise d'un repo cible, baseline capturée, backlog de remédiation, gate de
non-régression effectif, HITL 2 non franchi par défaut (rien n'est mergé)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from conductor.cadrage import cadrer
from conductor.contracts import StoryOutcome
from conductor.onramp import select_onramp
from conductor.onramp.no_onramp import NoOnramp
from conductor.planners.remediation import RemediationPlanner
from conductor.sprint_config import preparer_sprint
from conductor.supervisor import superviser


class _CodeRunner:
    def __init__(self, rc: int) -> None:
        self.rc = rc

    def run(self, command: str, cwd: Path) -> int:
        return self.rc


class _Linter:
    def lint_json(self, design_md: Path) -> dict[str, Any]:
        return {"findings": []}


class _FakeBad:
    def __init__(self, outcomes: list[StoryOutcome]) -> None:
        self._outcomes = outcomes

    def run_sprint(self, layout: object) -> list[StoryOutcome]:
        return self._outcomes

    def remediate(self, story_id: str, layout: object) -> StoryOutcome:
        return StoryOutcome(story_id=story_id, code_ok=True, pr_url=f"pr/{story_id}")


def _design_pass(_o: StoryOutcome) -> Any:
    from conductor.contracts import GateVerdict

    return GateVerdict(gate="design", passed=True)


class _ApproveGate:
    def approve(self, checkpoint: str, payload: object) -> bool:
        return True


def test_brownfield_remediation_end_to_end(tmp_path: Path) -> None:
    # repo cible existant, avec CI code ROUGE à la baseline → une story de remédiation
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    mission = cadrer("assainir le CRM", mode="brownfield", existing_repo=tmp_path, intent="remediation")

    onramp = select_onramp(mission)
    assert isinstance(onramp, NoOnramp)
    # on reconstruit un NoOnramp avec runners injectés (code rouge, design vert)
    substrate = NoOnramp(code_runner=_CodeRunner(1), design_linter=_Linter()).prepare(mission, tmp_path)
    assert substrate.baseline == {"code": False, "design": True}

    plan = RemediationPlanner().plan(substrate)
    assert any("CI code" in s.title for s in plan.stories)
    plan = plan.model_copy(update={"hitl1_approved": True})  # HITL 1 approuvé (simulé)

    layout = preparer_sprint(plan, tmp_path, baseline=substrate.baseline)
    assert layout.baseline == {"code": False, "design": True}

    # BAD répare la story (code repasse vert) → ready, et HITL 2 requis avant tout merge
    bad = _FakeBad([StoryOutcome(story_id="R1", code_ok=True, pr_url="pr/R1")])
    report = superviser(layout, bad=bad, design_check=_design_pass, hitl=_ApproveGate())
    assert report.results[0].status == "ready-for-review"
    assert report.merged is False  # jamais d'auto-merge (décision 07)
```

- [ ] **Step 2: Run, expect PASS** — `uv run pytest tests/test_brownfield_e2e.py -v`.

- [ ] **Step 3: Full gate + commit**

```bash
uv run ruff check . && uv run mypy && uv run pytest
git add tests/test_brownfield_e2e.py
git commit -m "test(ba): intégration brownfield de bout en bout (branche A) (BA)"
```

---

## Définition de fin (gate de sortie BA)

- [ ] `uv run ruff check .` clean · `uv run mypy` success · `uv run pytest` tout vert
- [ ] Greenfield inchangé (tests B0/Epic 3 toujours verts)
- [ ] `conductor run "<idée>" --mode brownfield --repo <path> --intent remediation` produit un backlog de remédiation et s'arrête à HITL 1, puis HITL 2 (rien n'est mergé)
- [ ] Le gate de non-régression bloque une story qui ferait passer un check vert au rouge

---

## Self-Review (effectuée)

**Couverture spec (BA) :** `NoOnramp` + marqueurs + baseline (T2) ; ingestion heuristique = baseline déterministe, pas d'agent en BA (T2/T6) ; `RegressionGate` do-no-harm (T3) intégré en E (T5) ; `RemediationPlanner` v1 tests/CI+design (T6) ; `ComplementPlanner` + composition (T7) ; backlog composable via D/E (T7/T8) ; câblage brownfield + 2 HITL préservés (T8/T9). HITL-0 (carte d'archi) n'est PAS requis en BA (repo forge connu) — relève de BC/BB, conforme à la spec.

**Placeholders :** aucun — code réel à chaque step.

**Cohérence des types :** `capture_baseline → dict[str, bool]` (T2) = `BadSprintLayout.baseline` (T4) = entrée d'`evaluate_regression` (T3) = `current`/`baseline` dans `superviser` (T5). `GateName` élargi à `"regression"` (T3) cohérent avec `GateVerdict(gate="regression")`. Planners implémentent le protocole `BmadPlanner.plan(substrate) -> BmadPlan` (T6/T7) consommé par `lancer_planification(substrate, planner=...)` (existant) via `_select_planner` (T8). `select_onramp(mission)` (T2) ↔ `run()` (T8). `NoOnramp.prepare(config, dest)` satisfait le protocole `Onramp` (B0).
