# Brownfield BB — Branche B (stack arbitraire, B-standard) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Hisser un repo d'une **stack non-FastAPI** (1ᵉʳ profil : `node-ts`) au **standard de la cible** (double gate, conventions) **dans sa stack d'origine** — pas de migration (B-standard) — avec dégradation déclarée et HITL-0 forcé.

**Architecture:** `detect_stack(repo)` reconnaît la stack (fastapi / node-ts / unknown). `profile_for_stack` mappe une stack à un `TargetProfile` (`NODE_TS` ajouté). `BuilderOnramp` résout le profil de la stack, normalise (DESIGN.md), capture la baseline via `profile.code_check` (ex. `npm test`), produit la carte d'archi, et **déclare la dégradation** (profil synthétisé, catalogue de briques vide, harness à fournir) → HITL-0 se déclenche (déjà conditionné à `declared_degradation`). Le routage `select_onramp` devient stack-aware : fastapi→No/Adapter (A/C), node-ts→Builder, unknown→erreur. Réutilise baseline/Analyzer/planners/supervisor/HITL-0. Greenfield + A + C inchangés.

**Tech Stack:** Python 3.11+, pydantic v2, pytest, ruff, mypy --strict, uv. Pré-requis : BC mergé. Branche : `epic-bb-branch-b`. **Toujours afficher la sortie des gates.**

---

## File Structure

- **Modify** `conductor/profiles.py` — ajoute `NODE_TS` + `profile_for_stack(stack) -> TargetProfile | None`.
- **Modify** `conductor/onramp/detect.py` — ajoute `detect_stack(repo) -> Literal["fastapi","node-ts","unknown"]`.
- **Create** `conductor/onramp/builder_onramp.py` — `BuilderOnramp`.
- **Modify** `conductor/onramp/__init__.py` — `select_onramp` stack-aware.
- **Tests** : `tests/test_profiles.py`, `tests/test_detect.py` (append) ; `tests/test_builder_onramp.py`, `tests/test_bb_e2e.py` (create) ; `tests/test_onramp.py`/e2e si besoin.

---

## Task 1 : profil `NODE_TS` + `profile_for_stack`

**Files:** Modify `conductor/profiles.py`; Test (append) `tests/test_profiles.py`.

- [ ] **Step 1: failing tests (append `tests/test_profiles.py`)**
```python
from conductor.profiles import NODE_TS, profile_for_stack


def test_node_ts_profile() -> None:
    assert NODE_TS.name == "node-ts"
    assert NODE_TS.code_check == "npm test"
    assert NODE_TS.has_ui is True
    assert NODE_TS.brick_catalog == {}  # pas de catalogue de briques pour node-ts (v1)


def test_profile_for_stack_maps_known_stacks() -> None:
    assert profile_for_stack("fastapi") is FASTAPI_SAAS
    assert profile_for_stack("node-ts") is NODE_TS
    assert profile_for_stack("rails") is None
```
(`FASTAPI_SAAS` is already imported in that test file.)

- [ ] **Step 2:** run `uv run pytest tests/test_profiles.py -v` → FAIL.

- [ ] **Step 3:** in `conductor/profiles.py`, after `FASTAPI_SAAS`, add:
```python
# Profil non-FastAPI (1ᵉʳ profil BB). B-standard : on hisse au contrat dans la stack d'origine.
NODE_TS = TargetProfile(
    name="node-ts",
    code_check="npm test",
    has_ui=True,
    design_md_path="design/DESIGN.md",
    conventions="Node/TypeScript ; npm test ; UI présente",
    brick_catalog={},
)

_PROFILES: dict[str, TargetProfile] = {"fastapi": FASTAPI_SAAS, "node-ts": NODE_TS}


def profile_for_stack(stack: str) -> TargetProfile | None:
    """Mappe une stack détectée à son TargetProfile (None si non supportée)."""
    return _PROFILES.get(stack)
```

- [ ] **Step 4:** run `uv run pytest tests/test_profiles.py -v` → PASS. Then full suite (show output).

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/profiles.py tests/test_profiles.py
git commit -m "feat(bb): profil NODE_TS + profile_for_stack (BB)"
```

---

## Task 2 : `detect_stack`

**Files:** Modify `conductor/onramp/detect.py`; Test (append) `tests/test_detect.py`.

- [ ] **Step 1: failing tests (append `tests/test_detect.py`)**
```python
from conductor.onramp.detect import detect_stack


def test_detect_stack_fastapi(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
    assert detect_stack(tmp_path) == "fastapi"


def test_detect_stack_node_ts(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    assert detect_stack(tmp_path) == "node-ts"


def test_detect_stack_unknown(tmp_path: Path) -> None:
    assert detect_stack(tmp_path) == "unknown"
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3:** in `conductor/onramp/detect.py`, add (keep `detect_distance` unchanged — it reste FastAPI-only, appelé seulement quand stack=fastapi) :
```python
def detect_stack(repo: Path) -> Literal["fastapi", "node-ts", "unknown"]:
    """Détecte la stack par marqueurs : pyproject.toml → fastapi ; package.json → node-ts."""
    if (repo / "pyproject.toml").exists():
        return "fastapi"
    if (repo / "package.json").exists():
        return "node-ts"
    return "unknown"
```
(Adjust the `Literal` import if needed — `Literal` is already imported.)

- [ ] **Step 4:** run `uv run pytest tests/test_detect.py -v` → PASS (existing 5 + new 3). Full suite.

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/onramp/detect.py tests/test_detect.py
git commit -m "feat(bb): detect_stack (fastapi/node-ts/unknown) (BB)"
```

---

## Task 3 : `BuilderOnramp`

**Files:** Create `conductor/onramp/builder_onramp.py`; Test `tests/test_builder_onramp.py`.

- [ ] **Step 1: failing test `tests/test_builder_onramp.py`**
```python
"""BuilderOnramp (branche B, B-standard) : hisse une stack non-FastAPI au contrat cible."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from conductor.cadrage import cadrer
from conductor.onramp.builder_onramp import BuilderOnramp
from conductor.profiles import NODE_TS


class _CodeRunner:
    def __init__(self, rc: int) -> None:
        self.rc = rc

    def run(self, command: str, cwd: Path) -> int:
        return self.rc


class _Linter:
    def lint_json(self, design_md: Path) -> dict[str, Any]:
        return {"findings": []}


def _node_repo(tmp: Path) -> Path:
    (tmp / "package.json").write_text("{}", encoding="utf-8")
    return tmp


def _onramp() -> BuilderOnramp:
    return BuilderOnramp(code_runner=_CodeRunner(0), design_linter=_Linter())


def test_builder_resolves_node_profile_and_declares_degradation(tmp_path: Path) -> None:
    repo = _node_repo(tmp_path)
    substrate = _onramp().prepare(cadrer("i", mode="brownfield", existing_repo=repo), repo)
    assert substrate.profile is NODE_TS
    assert substrate.declared_degradation  # profil synthétisé → dégradation déclarée (HITL-0)


def test_builder_creates_missing_design_md(tmp_path: Path) -> None:
    repo = _node_repo(tmp_path)
    _onramp().prepare(cadrer("i", mode="brownfield", existing_repo=repo), repo)
    assert (repo / "design" / "DESIGN.md").exists()


def test_builder_captures_baseline_with_node_code_check(tmp_path: Path) -> None:
    repo = _node_repo(tmp_path)
    captured: list[str] = []

    class _Rec:
        def run(self, command: str, cwd: Path) -> int:
            captured.append(command)
            return 0

    substrate = BuilderOnramp(code_runner=_Rec(), design_linter=_Linter()).prepare(
        cadrer("i", mode="brownfield", existing_repo=repo), repo
    )
    assert substrate.baseline == {"code": True, "design": True}
    assert captured == ["npm test"]  # baseline via le code_check du profil node-ts


def test_builder_rejects_unknown_stack(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="non gérée|unsupported|stack"):
        _onramp().prepare(cadrer("i", mode="brownfield", existing_repo=tmp_path), tmp_path)
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3: create `conductor/onramp/builder_onramp.py`**
```python
"""BuilderOnramp — bretelle brownfield « branche B » (B-standard).

Pour une stack non-FastAPI (1ᵉr profil : node-ts), résout le TargetProfile de la stack,
normalise vers le contrat (DESIGN.md), capture la baseline via le code_check du profil, et
DÉCLARE la dégradation (profil synthétisé, catalogue de briques vide, harness à fournir).
Ne migre pas le code vers FastAPI : on hisse au standard DANS la stack d'origine.
"""

from __future__ import annotations

from pathlib import Path

from conductor.contracts import MissionConfig
from conductor.gates.code_gate import CommandRunner
from conductor.gates.design_gate import DesignLinter
from conductor.onramp.analyzer import Analyzer, HeuristicAnalyzer
from conductor.onramp.base import Substrate
from conductor.onramp.detect import detect_stack, has_ci
from conductor.onramp.no_onramp import capture_baseline
from conductor.profiles import profile_for_stack

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

Charte minimale créée par BuilderOnramp (branche B). À compléter par la charte réelle.
"""


class BuilderOnramp:
    """Branche B : hisse une stack non-FastAPI au contrat cible (profil synthétisé)."""

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
        stack = detect_stack(repo)
        profile = profile_for_stack(stack)
        if profile is None or stack == "fastapi":
            raise ValueError(
                f"BuilderOnramp : stack '{stack}' non gérée par un profil dédié dans {repo} "
                "(FastAPI relève de NoOnramp/AdapterOnramp ; stack inconnue = non supportée)."
            )

        notes: list[str] = [
            f"Profil '{profile.name}' synthétisé : contrat hissé dans la stack d'origine (B-standard).",
            "Catalogue de briques vide pour cette stack (à enrichir).",
        ]

        design_md = repo / profile.design_md_path
        if profile.has_ui and not design_md.exists():
            design_md.parent.mkdir(parents=True, exist_ok=True)
            design_md.write_text(_DEFAULT_DESIGN_MD, encoding="utf-8")
            notes.append("DESIGN.md créé par normalisation (à compléter).")
        if not has_ci(repo):
            notes.append("Harness CI absent : gate code à fournir pour cette stack.")

        arch_map = self._analyzer.analyze(repo)
        baseline = capture_baseline(
            repo, profile, code_runner=self._code_runner, design_linter=self._design_linter
        )
        return Substrate(
            repo_path=repo,
            profile=profile,
            design_md_path=design_md,
            baseline=baseline,
            arch_map=arch_map,
            declared_degradation=notes,
        )
```

- [ ] **Step 4:** run `uv run pytest tests/test_builder_onramp.py -v` → PASS (4). Full suite.

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/onramp/builder_onramp.py tests/test_builder_onramp.py
git commit -m "feat(bb): BuilderOnramp (profil node-ts synthétisé + dégradation déclarée) (BB)"
```
NOTE: `_DEFAULT_DESIGN_MD` duplique celui d'`adapter_onramp.py` — duplication mineure assumée en v1 (suivi tracé : consolider le template DESIGN.md par défaut).

---

## Task 4 : `select_onramp` stack-aware

**Files:** Modify `conductor/onramp/__init__.py`; Test (append) `tests/test_detect.py`.

- [ ] **Step 1: failing tests (append `tests/test_detect.py`)**
```python
from conductor.onramp.builder_onramp import BuilderOnramp


def test_select_onramp_node_ts_is_builder(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    mission = cadrer("i", mode="brownfield", existing_repo=tmp_path)
    assert isinstance(select_onramp(mission), BuilderOnramp)


def test_select_onramp_unknown_stack_raises(tmp_path: Path) -> None:
    mission = cadrer("i", mode="brownfield", existing_repo=tmp_path)
    with pytest.raises(ValueError, match="non supportée|unknown|stack"):
        select_onramp(mission)
```

- [ ] **Step 2:** run → FAIL.

- [ ] **Step 3:** in `conductor/onramp/__init__.py`, add import `from conductor.onramp.builder_onramp import BuilderOnramp` and `from conductor.onramp.detect import detect_distance, detect_stack` (merge with existing detect import); add `"BuilderOnramp"` to `__all__`; replace `select_onramp` with:
```python
def select_onramp(mission: MissionConfig) -> Onramp:
    """greenfield → Scaffold ; brownfield → routage stack-aware.

    fastapi : NoOnramp (distance A) ou AdapterOnramp (distance C).
    node-ts (et futurs profils) : BuilderOnramp (B-standard).
    stack inconnue : non supportée.
    """
    if mission.mode == "greenfield":
        return ScaffoldOnramp()
    assert mission.existing_repo is not None  # garanti par cadrer() ; mypy narrowing
    repo = mission.existing_repo
    stack = detect_stack(repo)
    if stack == "fastapi":
        return NoOnramp() if detect_distance(repo) == "A" else AdapterOnramp()
    if stack == "node-ts":
        return BuilderOnramp()
    raise ValueError(
        f"Stack non supportée pour {repo} : ni FastAPI ni node-ts. "
        "Ajouter un profil (TargetProfile) + un cas de routage pour cette stack."
    )
```

- [ ] **Step 4:** run `uv run pytest tests/test_detect.py -v` → PASS. Full suite (show output). Existing fastapi routing tests still pass.

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/onramp/__init__.py tests/test_detect.py
git commit -m "feat(bb): select_onramp stack-aware (fastapi A/C, node-ts Builder) (BB)"
```

---

## Task 5 : test d'intégration BB de bout en bout

**Files:** Create `tests/test_bb_e2e.py`.

- [ ] **Step 1: write the test**
```python
"""Bout-en-bout BB : repo node-ts → BuilderOnramp (profil synthétisé, dégradation déclarée) →
baseline (npm test) → remédiation → D → E, rien n'est mergé ; HITL-0 forcé (dégradation)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from conductor.cadrage import cadrer
from conductor.contracts import GateVerdict, StoryOutcome
from conductor.governance import HitlPending, require_hitl0
from conductor.onramp import select_onramp
from conductor.onramp.builder_onramp import BuilderOnramp
from conductor.planners.remediation import RemediationPlanner
from conductor.profiles import NODE_TS
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


def test_bb_node_ts_end_to_end(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    mission = cadrer("assainir le SaaS node", mode="brownfield", existing_repo=tmp_path)
    assert isinstance(select_onramp(mission), BuilderOnramp)

    substrate = BuilderOnramp(code_runner=_CodeRunner(0), design_linter=_Linter()).prepare(
        mission, tmp_path
    )
    assert substrate.profile is NODE_TS
    assert substrate.declared_degradation
    # HITL-0 forcé (dégradation déclarée) : pause sans approbation
    try:
        require_hitl0("normalisation", substrate)
        raise AssertionError("HITL-0 aurait dû se déclencher")
    except HitlPending:
        pass

    plan = RemediationPlanner().plan(substrate).model_copy(update={"hitl1_approved": True})
    layout = preparer_sprint(plan, tmp_path, baseline=substrate.baseline)
    bad = _FakeBad([StoryOutcome(story_id="B1", code_ok=True, pr_url="pr/B1")])
    report = superviser(layout, bad=bad, design_check=_design_pass, hitl=_ApproveGate())
    assert report.merged is False
```

- [ ] **Step 2:** run `uv run pytest tests/test_bb_e2e.py -v` → PASS.

- [ ] **Step 3: full gate (show output) + commit**
```
uv run ruff check . ; uv run mypy ; uv run pytest
git add tests/test_bb_e2e.py
git commit -m "test(bb): intégration BB de bout en bout (node-ts) (BB)"
```

---

## Définition de fin (gate de sortie BB)

- [ ] ruff clean · mypy success · pytest tout vert (sortie visible)
- [ ] Greenfield + branches A & C inchangés (tests B0/BA/BC verts)
- [ ] Un repo `node-ts` est détecté, routé vers `BuilderOnramp`, profil `NODE_TS` synthétisé, baseline via `npm test`, dégradation déclarée, HITL-0 forcé, flux A→E jusqu'aux HITL
- [ ] Une stack inconnue lève une erreur explicite

---

## Self-Review (effectuée)

**Couverture spec (BB) :** détection de stack (T2) ; `BuilderOnramp` + profil synthétisé `node-ts` avec UI → exerce les deux gates (T1/T3) ; dégradation déclarée → HITL-0 forcé (T3, réutilise la condition BC) ; routage stack-aware (T4) ; e2e (T5) ; hôte GitHub d'abord (inchangé). Ne migre pas la stack (B-standard).

**Placeholders :** aucun.

**Cohérence des types :** `detect_stack -> Literal["fastapi","node-ts","unknown"]` (T2) consommé par `select_onramp` (T4) + `BuilderOnramp` (T3) ; `profile_for_stack -> TargetProfile | None` (T1) ; `NODE_TS.code_check="npm test"` → `capture_baseline` lance `npm test` (T3) ; `BuilderOnramp.prepare(config,dest)->Substrate` satisfait `Onramp` ; `declared_degradation` non vide → `require_hitl0` (BC) se déclenche. `has_ci` réutilisé (public depuis le correctif BC F4).

**Suivi mineur tracé :** `_DEFAULT_DESIGN_MD` dupliqué entre `adapter_onramp.py` et `builder_onramp.py` — consolider dans un module partagé ultérieurement.
