# Brownfield BC — Branche C (repos compatibles cible) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Onboarder un repo FastAPI **compatible cible mais non généré par la forge** : détecter la distance (A vs C), **normaliser** (créer `DESIGN.md` manquant, déclarer le harness CI manquant), produire une **carte d'archi** (ingestion hybride), poser **HITL-0**, puis dérouler le flux unifié.

**Architecture:** `detect_distance(repo)` route brownfield vers `NoOnramp` (A, déjà conforme) ou `AdapterOnramp` (C, à normaliser). `AdapterOnramp` normalise puis capture la baseline et la carte d'archi via un `Analyzer` injectable (heuristique par défaut ; variante sous-agent = stub harness). `require_hitl0` ajoute le 3ᵉ point de validation (carte/normalisation) avant la planification. Réutilise massivement BA (baseline, RegressionGate, planners, supervisor). Greenfield et branche A inchangés.

**Tech Stack:** Python 3.11+, pydantic v2, pytest, ruff, mypy --strict, uv. Paquet `digitai-saas-forge/conductor`. Pré-requis : BA mergé. Branche : `epic-bc-branch-c`.

---

## File Structure

- **Create** `conductor/onramp/detect.py` — `detect_distance(repo) -> Literal["A","C"]`.
- **Create** `conductor/onramp/analyzer.py` — `Analyzer` protocol, `HeuristicAnalyzer`, `SubagentAnalyzer` (stub harness).
- **Create** `conductor/onramp/adapter_onramp.py` — `AdapterOnramp` (normalise + baseline + arch_map + dégradation déclarée).
- **Modify** `conductor/onramp/__init__.py` — `select_onramp` route brownfield via `detect_distance`.
- **Modify** `conductor/governance.py` — `require_hitl0(subject, payload, gate)`.
- **Modify** `conductor/__main__.py` — `run()` pose HITL-0 en brownfield avant la planification.
- **Tests** : `tests/test_detect.py`, `tests/test_analyzer.py`, `tests/test_adapter_onramp.py`, `tests/test_bc_e2e.py` (create) ; `tests/test_onramp.py`, `tests/test_governance*`/e2e (modify as needed).

Commandes depuis `digitai-saas-forge/`. **Toujours afficher la sortie des gates** (jamais `>/dev/null`).

---

## Task 1 : `detect_distance` + routage A/C

**Files:** Create `conductor/onramp/detect.py`; Modify `conductor/onramp/__init__.py`; Test `tests/test_detect.py`.

- [ ] **Step 1: failing test `tests/test_detect.py`**
```python
"""Détection de la distance à la cible : A (déjà conforme) vs C (à normaliser)."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.cadrage import cadrer
from conductor.onramp import select_onramp
from conductor.onramp.adapter_onramp import AdapterOnramp
from conductor.onramp.detect import detect_distance
from conductor.onramp.no_onramp import NoOnramp


def _fastapi_repo(tmp: Path, *, with_design: bool, with_ci: bool) -> Path:
    (tmp / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    if with_design:
        (tmp / "design").mkdir(parents=True, exist_ok=True)
        (tmp / "design" / "DESIGN.md").write_text("# DESIGN\n", encoding="utf-8")
    if with_ci:
        (tmp / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
        (tmp / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    return tmp


def test_complete_target_repo_is_distance_a(tmp_path: Path) -> None:
    repo = _fastapi_repo(tmp_path, with_design=True, with_ci=True)
    assert detect_distance(repo) == "A"


def test_fastapi_missing_design_is_distance_c(tmp_path: Path) -> None:
    repo = _fastapi_repo(tmp_path, with_design=False, with_ci=True)
    assert detect_distance(repo) == "C"


def test_non_fastapi_repo_raises_for_bb(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="BB"):
        detect_distance(tmp_path)  # ni pyproject ni marqueurs


def test_select_onramp_routes_distance_a_to_no_onramp(tmp_path: Path) -> None:
    _fastapi_repo(tmp_path, with_design=True, with_ci=True)
    mission = cadrer("i", mode="brownfield", existing_repo=tmp_path)
    assert isinstance(select_onramp(mission), NoOnramp)


def test_select_onramp_routes_distance_c_to_adapter(tmp_path: Path) -> None:
    _fastapi_repo(tmp_path, with_design=False, with_ci=True)
    mission = cadrer("i", mode="brownfield", existing_repo=tmp_path)
    assert isinstance(select_onramp(mission), AdapterOnramp)
```

- [ ] **Step 2:** run `uv run pytest tests/test_detect.py -v` → FAIL (modules missing).

- [ ] **Step 3a: create `conductor/onramp/detect.py`**
```python
"""Détection de la distance à la cible pour router la bretelle brownfield.

A : repo déjà conforme à la cible (pyproject + DESIGN.md + CI) → NoOnramp.
C : repo FastAPI-compatible mais incomplet (pyproject présent, DESIGN.md ou CI manquant)
    → AdapterOnramp (normalisation).
Sinon (pas de pyproject) : hors périmètre BA/BC → relève de BB (stack non-FastAPI).
Heuristique pure (décision spec : faits durs déterministes).
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal


def _has_ci(repo: Path) -> bool:
    wf = repo / ".github" / "workflows"
    return wf.is_dir() and any(wf.glob("*.yml")) or any(wf.glob("*.yaml")) if wf.is_dir() else False


def detect_distance(repo: Path) -> Literal["A", "C"]:
    """Classe le repo : 'A' (déjà cible) ou 'C' (à normaliser). Lève si non-FastAPI (→ BB)."""
    if not (repo / "pyproject.toml").exists():
        raise ValueError(
            f"Repo non reconnu comme cible FastAPI (pyproject.toml absent) dans {repo} : "
            "stack arbitraire → relève de l'epic BB (BuilderOnramp)."
        )
    has_design = (repo / "design" / "DESIGN.md").exists()
    has_ci = _has_ci(repo)
    return "A" if (has_design and has_ci) else "C"
```
NOTE: simplify `_has_ci` to avoid operator-precedence confusion — use:
```python
def _has_ci(repo: Path) -> bool:
    wf = repo / ".github" / "workflows"
    if not wf.is_dir():
        return False
    return any(wf.glob("*.yml")) or any(wf.glob("*.yaml"))
```
Use this clearer version in the file.

- [ ] **Step 3b: route in `conductor/onramp/__init__.py`** — replace `select_onramp`:
```python
def select_onramp(mission: MissionConfig) -> Onramp:
    """greenfield → Scaffold ; brownfield → NoOnramp (A) ou AdapterOnramp (C) selon la distance."""
    if mission.mode == "greenfield":
        return ScaffoldOnramp()
    assert mission.existing_repo is not None  # garanti par cadrer() ; mypy narrowing
    distance = detect_distance(mission.existing_repo)
    return NoOnramp() if distance == "A" else AdapterOnramp()
```
Add imports at top: `from conductor.onramp.adapter_onramp import AdapterOnramp` and `from conductor.onramp.detect import detect_distance`. Add `AdapterOnramp` to `__all__`. (The `assert` here is acceptable as a mypy-narrowing of an invariant already enforced by `cadrer()`; keep it on one line ≤100 chars.)

- [ ] **Step 4:** run `uv run pytest tests/test_detect.py -v` → PASS (5). Then full suite (visible output).

- [ ] **Step 5: verify (show output) & commit**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/onramp/detect.py conductor/onramp/__init__.py tests/test_detect.py
git commit -m "feat(bc): detect_distance + routage A/C (BC)"
```

---

## Task 2 : `Analyzer` (carte d'archi hybride)

**Files:** Create `conductor/onramp/analyzer.py`; Test `tests/test_analyzer.py`.

- [ ] **Step 1: failing test `tests/test_analyzer.py`**
```python
"""Ingestion : carte d'archi. HeuristicAnalyzer (faits durs) par défaut ; SubagentAnalyzer = harness."""

from __future__ import annotations

from pathlib import Path

import pytest

from conductor.onramp.analyzer import HeuristicAnalyzer, SubagentAnalyzer


def test_heuristic_analyzer_lists_top_level(tmp_path: Path) -> None:
    (tmp_path / "backend").mkdir()
    (tmp_path / "frontend").mkdir()
    (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
    arch = HeuristicAnalyzer().analyze(tmp_path)
    assert "backend" in arch["top_level"]
    assert "frontend" in arch["top_level"]
    assert arch["has_pyproject"] is True


def test_subagent_analyzer_requires_harness(tmp_path: Path) -> None:
    with pytest.raises(NotImplementedError, match="harness"):
        SubagentAnalyzer().analyze(tmp_path)
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: create `conductor/onramp/analyzer.py`**
```python
"""Ingestion hybride — carte d'archi d'un repo existant.

HeuristicAnalyzer : faits durs déterministes (structure top-level, présence pyproject) —
testable hors-ligne, base de la carte. SubagentAnalyzer : interprétation par un sous-agent
Claude Code (dette, conventions) — nécessite le harness ; stub ici (branché en production).
Décision spec : BC = ingestion hybride (faits heuristiques + interprétation agent).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class Analyzer(Protocol):
    def analyze(self, repo_path: Path) -> dict[str, Any]: ...


class HeuristicAnalyzer:
    """Faits durs : structure de premier niveau + marqueurs. Déterministe."""

    def analyze(self, repo_path: Path) -> dict[str, Any]:
        top_level = sorted(p.name for p in repo_path.iterdir()) if repo_path.is_dir() else []
        return {
            "top_level": top_level,
            "has_pyproject": (repo_path / "pyproject.toml").exists(),
            "has_frontend": (repo_path / "frontend").is_dir(),
        }


class SubagentAnalyzer:
    """Interprétation par un sous-agent Claude Code (carte d'archi enrichie, dette).

    Nécessite le harness Claude Code ; point d'intégration matérialisé (cf. DefaultBadRunner).
    """

    def analyze(self, repo_path: Path) -> dict[str, Any]:
        raise NotImplementedError(
            "SubagentAnalyzer nécessite le harness Claude Code (ingestion par sous-agent). "
            "Utiliser HeuristicAnalyzer hors harness."
        )
```

- [ ] **Step 4:** run `uv run pytest tests/test_analyzer.py -v` → PASS (2). Full suite.

- [ ] **Step 5: commit**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/onramp/analyzer.py tests/test_analyzer.py
git commit -m "feat(bc): Analyzer hybride (heuristique + stub sous-agent) (BC)"
```

---

## Task 3 : `AdapterOnramp` (normalisation + baseline + carte + dégradation)

**Files:** Create `conductor/onramp/adapter_onramp.py`; Test `tests/test_adapter_onramp.py`.

- [ ] **Step 1: failing test `tests/test_adapter_onramp.py`**
```python
"""AdapterOnramp (branche C) : normalise un repo FastAPI incomplet vers le contrat cible."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from conductor.cadrage import cadrer
from conductor.onramp.adapter_onramp import AdapterOnramp
from conductor.profiles import FASTAPI_SAAS


class _CodeRunner:
    def __init__(self, rc: int) -> None:
        self.rc = rc

    def run(self, command: str, cwd: Path) -> int:
        return self.rc


class _Linter:
    def lint_json(self, design_md: Path) -> dict[str, Any]:
        return {"findings": []}


def _repo(tmp: Path) -> Path:
    (tmp / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    return tmp


def _onramp() -> AdapterOnramp:
    return AdapterOnramp(code_runner=_CodeRunner(0), design_linter=_Linter())


def test_adapter_creates_missing_design_md(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    substrate = _onramp().prepare(cadrer("i", mode="brownfield", existing_repo=repo), repo)
    assert (repo / "design" / "DESIGN.md").exists()  # normalisation : DESIGN.md créé
    assert any("DESIGN.md" in note for note in substrate.declared_degradation)


def test_adapter_captures_baseline_and_archmap(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    substrate = _onramp().prepare(cadrer("i", mode="brownfield", existing_repo=repo), repo)
    assert substrate.profile is FASTAPI_SAAS
    assert substrate.baseline == {"code": True, "design": True}
    assert substrate.arch_map is not None and substrate.arch_map["has_pyproject"] is True


def test_adapter_declares_missing_ci(tmp_path: Path) -> None:
    repo = _repo(tmp_path)  # pas de .github/workflows
    substrate = _onramp().prepare(cadrer("i", mode="brownfield", existing_repo=repo), repo)
    assert any("CI" in note for note in substrate.declared_degradation)


def test_adapter_requires_pyproject(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="BB"):
        _onramp().prepare(cadrer("i", mode="brownfield", existing_repo=tmp_path), tmp_path)
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: create `conductor/onramp/adapter_onramp.py`**
```python
"""AdapterOnramp — bretelle brownfield « branche C » : repo FastAPI compatible à normaliser.

Normalise vers le contrat de la cible (crée un DESIGN.md par défaut s'il manque),
DÉCLARE ce qui ne peut être tenu (ex. harness CI absent), capture la carte d'archi (ingestion
hybride) et la baseline APRÈS normalisation. Ne migre pas la stack (B-standard).
"""

from __future__ import annotations

from pathlib import Path

from conductor.contracts import MissionConfig
from conductor.gates.code_gate import CommandRunner
from conductor.gates.design_gate import DesignLinter
from conductor.onramp.analyzer import Analyzer, HeuristicAnalyzer
from conductor.onramp.base import Substrate
from conductor.onramp.detect import _has_ci
from conductor.onramp.no_onramp import capture_baseline
from conductor.profiles import FASTAPI_SAAS

_DEFAULT_DESIGN_MD = """---
name: Imported Project
colors:
  primary: "#2563eb"
  ink: "#0f172a"
typography:
  heading: "Roboto"
  body: "DM Sans"
---

# Design System (importé)

Charte minimale créée par AdapterOnramp (branche C). À compléter par la charte réelle du projet.
"""


class AdapterOnramp:
    """Branche C : normalise un repo FastAPI incomplet, puis capture baseline + carte d'archi."""

    def __init__(
        self,
        *,
        code_runner: CommandRunner | None = None,
        design_linter: DesignLinter | None = None,
        analyzer: Analyzer | None = None,
    ) -> None:
        self._code_runner = code_runner
        self._design_linter = design_linter
        self._analyzer = analyzer or HeuristicAnalyzer()

    def prepare(self, config: MissionConfig, dest: Path) -> Substrate:
        repo = dest
        if not (repo / "pyproject.toml").exists():
            raise ValueError(
                f"AdapterOnramp (C) attend un repo FastAPI (pyproject.toml absent) dans {repo} : "
                "stack arbitraire → relève de l'epic BB."
            )
        notes: list[str] = []

        # Normalisation : créer un DESIGN.md par défaut s'il manque.
        design_md = repo / FASTAPI_SAAS.design_md_path
        if not design_md.exists():
            design_md.parent.mkdir(parents=True, exist_ok=True)
            design_md.write_text(_DEFAULT_DESIGN_MD, encoding="utf-8")
            notes.append("DESIGN.md créé par normalisation (à compléter).")

        # Dégradation déclarée : harness CI absent (non créé automatiquement en BC).
        if not _has_ci(repo):
            notes.append("Harness CI absent : le gate code s'appuiera sur un harness à fournir.")

        arch_map = self._analyzer.analyze(repo)
        baseline = capture_baseline(
            repo, FASTAPI_SAAS, code_runner=self._code_runner, design_linter=self._design_linter
        )
        return Substrate(
            repo_path=repo,
            profile=FASTAPI_SAAS,
            design_md_path=design_md,
            baseline=baseline,
            arch_map=arch_map,
            declared_degradation=notes,
        )
```

- [ ] **Step 4:** run `uv run pytest tests/test_adapter_onramp.py -v` → PASS (4). Full suite.

- [ ] **Step 5: commit**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/onramp/adapter_onramp.py tests/test_adapter_onramp.py
git commit -m "feat(bc): AdapterOnramp (normalisation + baseline + carte + dégradation) (BC)"
```

---

## Task 4 : HITL-0 (validation carte/normalisation)

**Files:** Modify `conductor/governance.py`; Test (append) a governance test or create `tests/test_hitl0.py`.

- [ ] **Step 1: failing test `tests/test_hitl0.py`**
```python
"""HITL-0 : valider la normalisation / carte d'archi avant la planification (brownfield)."""

from __future__ import annotations

import pytest

from conductor.governance import HitlPending, require_hitl0


class _Approve:
    def approve(self, checkpoint: str, payload: object) -> bool:
        return True


class _Reject:
    def approve(self, checkpoint: str, payload: object) -> bool:
        return False


def test_hitl0_passes_when_approved() -> None:
    require_hitl0("carte d'archi", {"x": 1}, gate=_Approve())  # ne lève pas


def test_hitl0_pauses_when_rejected() -> None:
    with pytest.raises(HitlPending, match="HITL-0"):
        require_hitl0("carte d'archi", {"x": 1}, gate=_Reject())


def test_hitl0_default_gate_pauses() -> None:
    with pytest.raises(HitlPending):
        require_hitl0("carte d'archi", {"x": 1})
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: add to `conductor/governance.py`** (after `ManualGate`)
```python
def require_hitl0(subject: str, payload: object, *, gate: HumanGate | None = None) -> None:
    """Point HITL-0 (brownfield) : valider la normalisation / la carte d'archi avant le dev.

    Lève HitlPending si non approuvé (défaut ManualGate → pause). Optionnel/léger en C,
    fortement recommandé en B (dégradation déclarée à valider).
    """
    if not (gate or ManualGate()).approve(f"HITL-0 — {subject}", payload):
        raise HitlPending(f"HITL-0 — validation requise : {subject}")
```

- [ ] **Step 4:** run `uv run pytest tests/test_hitl0.py -v` → PASS (3). Full suite.

- [ ] **Step 5: commit**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/governance.py tests/test_hitl0.py
git commit -m "feat(bc): HITL-0 (validation carte/normalisation) (BC)"
```

---

## Task 5 : câbler HITL-0 dans `run()` (brownfield)

**Files:** Modify `conductor/__main__.py`; Test (append) `tests/test_e2e_master.py`.

- [ ] **Step 1: failing test (append `tests/test_e2e_master.py`)**
```python
def test_brownfield_run_pauses_at_hitl0(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Par défaut (ManualGate), un run brownfield s'arrête à HITL-0 après l'onramp."""
    from conductor.contracts import MissionConfig
    from conductor.governance import HitlPending
    from conductor.onramp.base import Substrate
    from conductor.profiles import FASTAPI_SAAS

    class _FakeOnramp:
        def prepare(self, config: MissionConfig, dest: Path) -> Substrate:
            return Substrate(repo_path=dest, profile=FASTAPI_SAAS, design_md_path=dest / "d.md")

    monkeypatch.setattr(cli, "select_onramp", lambda _m: _FakeOnramp())

    with pytest.raises(HitlPending, match="HITL-0"):
        cli.run("assainir", mode="brownfield", existing_repo=tmp_path)
```

- [ ] **Step 2:** run → FAIL (no HITL-0 in run()).

- [ ] **Step 3: wire HITL-0 in `conductor/__main__.py`**
- Add import: `from conductor.governance import require_hitl0`.
- In `run()`, right AFTER `substrate = select_onramp(mission).prepare(mission, target)` and BEFORE `plan = lancer_planification(...)`, insert:
```python
    if mission.mode == "brownfield":
        require_hitl0("normalisation & carte d'archi", substrate)  # HITL-0 (pause par défaut)
```

- [ ] **Step 4:** run the FULL gate (visible). The greenfield path is unaffected (HITL-0 only for brownfield). The existing greenfield `test_run_pauses_at_hitl1_by_default` still pauses at HITL-1 (greenfield skips HITL-0).

- [ ] **Step 5: commit**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/__main__.py tests/test_e2e_master.py
git commit -m "feat(bc): HITL-0 câblé dans run() pour le brownfield (BC)"
```

---

## Task 6 : test d'intégration BC de bout en bout

**Files:** Create `tests/test_bc_e2e.py`.

- [ ] **Step 1: write the test**
```python
"""Bout-en-bout BC : repo FastAPI externe sans DESIGN.md → AdapterOnramp normalise →
baseline → remédiation → D → E, rien n'est mergé."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from conductor.cadrage import cadrer
from conductor.contracts import GateVerdict, StoryOutcome
from conductor.onramp import select_onramp
from conductor.onramp.adapter_onramp import AdapterOnramp
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


def _design_pass(_o: StoryOutcome) -> GateVerdict:
    return GateVerdict(gate="design", passed=True)


class _ApproveGate:
    def approve(self, checkpoint: str, payload: object) -> bool:
        return True


def test_bc_external_repo_normalized_end_to_end(tmp_path: Path) -> None:
    # repo FastAPI externe SANS design/DESIGN.md → distance C → AdapterOnramp
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    mission = cadrer("compléter le SaaS", mode="brownfield", existing_repo=tmp_path)
    assert isinstance(select_onramp(mission), AdapterOnramp)

    substrate = AdapterOnramp(code_runner=_CodeRunner(0), design_linter=_Linter()).prepare(
        mission, tmp_path
    )
    assert (tmp_path / "design" / "DESIGN.md").exists()  # normalisé
    assert substrate.declared_degradation  # dégradation déclarée (CI absent)

    plan = RemediationPlanner().plan(substrate)
    plan = plan.model_copy(update={"hitl1_approved": True})
    layout = preparer_sprint(plan, tmp_path, baseline=substrate.baseline)

    bad = _FakeBad([StoryOutcome(story_id="C1", code_ok=True, pr_url="pr/C1")])
    report = superviser(layout, bad=bad, design_check=_design_pass, hitl=_ApproveGate())
    assert report.merged is False
```

- [ ] **Step 2:** run `uv run pytest tests/test_bc_e2e.py -v` → PASS.

- [ ] **Step 3: full gate (visible) + commit**
```
uv run ruff check . ; uv run mypy ; uv run pytest
git add tests/test_bc_e2e.py
git commit -m "test(bc): intégration BC de bout en bout (branche C) (BC)"
```

---

## Définition de fin (gate de sortie BC)

- [ ] ruff clean · mypy success · pytest tout vert (sortie visible)
- [ ] Greenfield + branche A inchangés (tests B0/BA toujours verts)
- [ ] Un repo FastAPI externe sans `DESIGN.md` est routé en C, normalisé (DESIGN.md créé), la dégradation (CI absent) est déclarée, et le flux A→E se déroule jusqu'aux HITL
- [ ] `select_onramp` route A vs C selon `detect_distance`

---

## Self-Review (effectuée)

**Couverture spec (BC) :** `AdapterOnramp` normalisation (T3) ; HITL-0 (T4) câblé en brownfield (T5) ; ingestion hybride = `HeuristicAnalyzer` + stub `SubagentAnalyzer` (T2) ; routage distance A/C (T1) ; dégradation déclarée (T3) ; e2e (T6). Réutilise baseline/RegressionGate/planners/supervisor de BA. AdapterOnramp ne migre pas la stack (B-standard).

**Placeholders :** aucun — code réel à chaque step.

**Cohérence des types :** `detect_distance -> Literal["A","C"]` (T1) consommé par `select_onramp` (T1) ; `Analyzer.analyze -> dict[str,Any]` (T2) → `Substrate.arch_map: dict[str,Any]|None` (existant) ; `AdapterOnramp.prepare(config,dest)->Substrate` satisfait `Onramp` ; `capture_baseline`/baseline `dict[str,bool]` cohérents avec BA ; `require_hitl0(subject,payload,*,gate)` (T4) appelé dans `run()` (T5). `_has_ci` réutilisé depuis `detect.py` par `adapter_onramp.py`.
