# Brownfield B0 — Fondations (les joints) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduire les abstractions brownfield (`TargetProfile`, `Onramp`, `Substrate`) et le mode greenfield/brownfield, **sans changer le comportement greenfield** (zéro régression).

**Architecture:** L'onramp généralise le scaffold-first : `ScaffoldOnramp` enveloppe le `scaffold.py` existant et produit un `Substrate` (repo + profil de cible + futures baseline/carte d'archi). Le pipeline A→E reçoit désormais un `Substrate` au lieu d'un `ScaffoldResult`. Le profil `fastapi-saas` réifie le comportement actuel. Les onramps brownfield (None/Adapter/Builder) sont des epics ultérieurs (BA/BC/BB) ; en B0, choisir `brownfield` lève une `NotImplementedError` explicite.

**Tech Stack:** Python 3.11+, pydantic v2, pytest, ruff, mypy --strict, uv. Travail dans le paquet `digitai-saas-forge/conductor`.

---

## File Structure

- **Create** `conductor/profiles.py` — `TargetProfile` (modèle) + l'instance canonique `FASTAPI_SAAS`. Responsabilité unique : décrire le contrat d'une stack.
- **Create** `conductor/onramp/__init__.py` — exports + `select_onramp(mode)`.
- **Create** `conductor/onramp/base.py` — `Substrate` (contrat de sortie d'onramp) + protocole `Onramp`.
- **Create** `conductor/onramp/scaffold_onramp.py` — `ScaffoldOnramp` (greenfield, enveloppe `scaffold.scaffold`).
- **Modify** `conductor/contracts.py` — ajoute `mode` à `MissionConfig`.
- **Modify** `conductor/cadrage.py` — paramètre `mode`.
- **Modify** `conductor/gates/code_gate.py` — `run_code_gate` lit `code_check` d'un `TargetProfile`.
- **Modify** `conductor/bmad_bridge.py` — `lancer_planification` / `BmadPlanner` prennent un `Substrate`.
- **Modify** `conductor/__main__.py` — `run()` sélectionne l'onramp selon le mode et fait circuler le `Substrate`.
- **Tests** : `tests/test_profiles.py`, `tests/test_onramp.py` (create) ; `tests/test_code_gate.py`, `tests/test_cadrage.py`, `tests/test_bmad_bridge.py`, `tests/test_e2e_master.py` (modify).

Toutes les commandes se lancent depuis `digitai-saas-forge/`.

---

## Task 1 : `TargetProfile` + profil `FASTAPI_SAAS`

**Files:**
- Create: `conductor/profiles.py`
- Test: `tests/test_profiles.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_profiles.py
"""Le TargetProfile réifie le contrat d'une stack ; FASTAPI_SAAS = la forge actuelle."""

from __future__ import annotations

from conductor.catalog import CATALOG
from conductor.profiles import FASTAPI_SAAS, TargetProfile


def test_fastapi_profile_reifies_current_behavior() -> None:
    assert FASTAPI_SAAS.name == "fastapi-saas"
    assert FASTAPI_SAAS.code_check == "uv run pytest"
    assert FASTAPI_SAAS.has_ui is True
    assert FASTAPI_SAAS.design_md_path == "design/DESIGN.md"
    assert FASTAPI_SAAS.brick_catalog is CATALOG  # le catalogue actuel devient le brick_catalog


def test_enforceable_reflects_gates() -> None:
    assert FASTAPI_SAAS.enforceable == {"code": True, "design": True}


def test_profile_without_code_check_disables_code_gate() -> None:
    p = TargetProfile(name="doc-only", code_check=None, has_ui=False)
    assert p.enforceable == {"code": False, "design": False}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_profiles.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'conductor.profiles'`.

- [ ] **Step 3: Write minimal implementation**

```python
# conductor/profiles.py
"""TargetProfile — le contrat d'une stack (gate code, applicabilité design, briques).

Le profil `fastapi-saas` réifie le comportement actuel de la forge (cf. spec brownfield).
`enforceable` décrit la part du contrat applicable — base de la dégradation déclarée (B).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from conductor.catalog import CATALOG, BrickSpec


class TargetProfile(BaseModel):
    name: str
    code_check: str | None  # commande du gate code ; None → gate code non applicable
    has_ui: bool  # le gate design s'applique-t-il ?
    design_md_path: str = "design/DESIGN.md"
    conventions: str = ""
    brick_catalog: dict[str, BrickSpec] = Field(default_factory=dict)

    @property
    def enforceable(self) -> dict[str, bool]:
        """Part du contrat réellement applicable (gates) pour cette stack."""
        return {"code": self.code_check is not None, "design": self.has_ui}


# Profil canonique = la forge actuelle (FastAPI + React, ruff/mypy/pytest, double gate).
FASTAPI_SAAS = TargetProfile(
    name="fastapi-saas",
    code_check="uv run pytest",
    has_ui=True,
    design_md_path="design/DESIGN.md",
    conventions="ruff + mypy strict; FastAPI + React; scaffold-first; double gate",
    brick_catalog=CATALOG,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_profiles.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Lint, type, commit**

```bash
uv run ruff check . && uv run mypy
git add conductor/profiles.py tests/test_profiles.py
git commit -m "feat(brownfield): TargetProfile + profil fastapi-saas (B0)"
```

---

## Task 2 : `code_gate` lit `code_check` d'un profil

**Files:**
- Modify: `conductor/gates/code_gate.py`
- Test: `tests/test_code_gate.py`

- [ ] **Step 1: Write the failing test (append to existing file)**

```python
# tests/test_code_gate.py — AJOUTER ces tests à la fin du fichier
from conductor.profiles import FASTAPI_SAAS, TargetProfile


def test_code_gate_uses_profile_code_check(tmp_path: Path) -> None:
    runner = FakeRunner(0)
    profile = TargetProfile(name="node-ts", code_check="npm test", has_ui=True)
    run_code_gate(tmp_path, profile=profile, runner=runner)
    assert runner.calls[0][0] == "npm test"  # commande issue du profil


def test_code_gate_profile_fastapi_runs_pytest(tmp_path: Path) -> None:
    runner = FakeRunner(0)
    run_code_gate(tmp_path, profile=FASTAPI_SAAS, runner=runner)
    assert runner.calls[0][0] == "uv run pytest"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_code_gate.py -v`
Expected: FAIL with `TypeError: run_code_gate() got an unexpected keyword argument 'profile'`.

- [ ] **Step 3: Modify `run_code_gate` to accept a profile**

Replace the `run_code_gate` function in `conductor/gates/code_gate.py` with:

```python
def run_code_gate(
    repo_path: Path,
    *,
    profile: "TargetProfile | None" = None,
    command: str = DEFAULT_CODE_CHECK,
    runner: CommandRunner | None = None,
) -> GateVerdict:
    """Lit le verdict de la CI pour le dépôt de story (passed = exit 0).

    La commande vient du `TargetProfile` si fourni (sinon `command`/défaut).
    """
    cmd = profile.code_check if (profile and profile.code_check) else command
    rc = (runner or SubprocessRunner()).run(cmd, repo_path)
    return GateVerdict(
        gate="code",
        passed=rc == 0,
        findings=[] if rc == 0 else [{"command": cmd, "returncode": str(rc)}],
        log_ref=str(repo_path),
    )
```

Add the import at the top of `conductor/gates/code_gate.py` (under `from __future__ import annotations`):

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from conductor.profiles import TargetProfile
```

- [ ] **Step 4: Run tests to verify they pass (incl. existing ones)**

Run: `uv run pytest tests/test_code_gate.py -v`
Expected: PASS (existing 3 + new 2 = 5 tests).

- [ ] **Step 5: Lint, type, commit**

```bash
uv run ruff check . && uv run mypy
git add conductor/gates/code_gate.py tests/test_code_gate.py
git commit -m "refactor(brownfield): code_gate lit code_check du TargetProfile (B0)"
```

---

## Task 3 : `Substrate` + protocole `Onramp`

**Files:**
- Create: `conductor/onramp/__init__.py`
- Create: `conductor/onramp/base.py`
- Test: `tests/test_onramp.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_onramp.py
"""Substrate = sortie d'onramp ; le protocole Onramp est structurel."""

from __future__ import annotations

from pathlib import Path

from conductor.onramp.base import Onramp, Substrate
from conductor.profiles import FASTAPI_SAAS


def test_substrate_defaults_baseline_and_archmap_to_none() -> None:
    s = Substrate(
        repo_path=Path("repo"),
        profile=FASTAPI_SAAS,
        design_md_path=Path("repo/design/DESIGN.md"),
    )
    assert s.baseline is None  # rempli en BA
    assert s.arch_map is None  # rempli en BC/BB


def test_fake_onramp_satisfies_protocol() -> None:
    class FakeOnramp:
        def prepare(self, config: object, dest: Path) -> Substrate:
            return Substrate(repo_path=dest, profile=FASTAPI_SAAS, design_md_path=dest / "d.md")

    onramp: Onramp = FakeOnramp()
    s = onramp.prepare(object(), Path("x"))
    assert s.profile is FASTAPI_SAAS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_onramp.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'conductor.onramp'`.

- [ ] **Step 3: Write minimal implementation**

```python
# conductor/onramp/base.py
"""Onramp — amène un projet au point où le contrat de la cible est applicable.

Généralise le scaffold-first : greenfield = onramp qui *génère* ; brownfield = onramp qui
*reprend/normalise/construit*. Sortie commune : un Substrate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field

from conductor.contracts import MissionConfig
from conductor.profiles import TargetProfile


class Substrate(BaseModel):
    """État prêt-à-planifier : un repo + son profil de cible (+ baseline/carte d'archi)."""

    repo_path: Path
    profile: TargetProfile
    design_md_path: Path
    baseline: dict[str, Any] | None = None  # statut des checks existants (capturé en BA)
    arch_map: dict[str, Any] | None = None  # carte d'architecture (remplie en BC/BB)
    declared_degradation: list[str] = Field(default_factory=list)  # dégradation explicite (B)


class Onramp(Protocol):
    """Prépare un Substrate à partir d'une mission et d'un répertoire de destination."""

    def prepare(self, config: MissionConfig, dest: Path) -> Substrate: ...
```

```python
# conductor/onramp/__init__.py
"""Onramps : sélection de la bretelle selon le mode/la distance à la cible."""

from __future__ import annotations

from conductor.onramp.base import Onramp, Substrate

__all__ = ["Onramp", "Substrate"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_onramp.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Lint, type, commit**

```bash
uv run ruff check . && uv run mypy
git add conductor/onramp/__init__.py conductor/onramp/base.py tests/test_onramp.py
git commit -m "feat(brownfield): Substrate + protocole Onramp (B0)"
```

---

## Task 4 : `ScaffoldOnramp` (greenfield) + `select_onramp`

**Files:**
- Create: `conductor/onramp/scaffold_onramp.py`
- Modify: `conductor/onramp/__init__.py`
- Test: `tests/test_onramp.py` (append)

- [ ] **Step 1: Write the failing test (append)**

```python
# tests/test_onramp.py — AJOUTER à la fin
import pytest

from conductor.cadrage import cadrer
from conductor.onramp import select_onramp
from conductor.onramp.scaffold_onramp import ScaffoldOnramp


class _FakeRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Path]] = []

    def run(self, command: str, cwd: Path) -> int:
        self.calls.append((command, cwd))
        return 0


def test_scaffold_onramp_generates_and_returns_substrate(tmp_path: Path) -> None:
    runner = _FakeRunner()
    substrate = ScaffoldOnramp(runner=runner).prepare(cadrer("un CRM"), tmp_path / "app")
    assert substrate.profile is FASTAPI_SAAS
    assert substrate.repo_path == tmp_path / "app"
    assert substrate.baseline is None  # greenfield : rien à préserver
    assert any("copier copy" in c for c, _ in runner.calls)  # scaffold-first exécuté


def test_select_onramp_greenfield_is_scaffold() -> None:
    assert isinstance(select_onramp("greenfield"), ScaffoldOnramp)


def test_select_onramp_brownfield_not_yet_implemented() -> None:
    with pytest.raises(NotImplementedError, match="BA"):
        select_onramp("brownfield")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_onramp.py -v`
Expected: FAIL with `ImportError: cannot import name 'select_onramp'` (and `scaffold_onramp` missing).

- [ ] **Step 3: Write minimal implementation**

```python
# conductor/onramp/scaffold_onramp.py
"""ScaffoldOnramp — la bretelle greenfield : génère le repo (enveloppe scaffold.scaffold)."""

from __future__ import annotations

from pathlib import Path

from conductor.contracts import MissionConfig
from conductor.onramp.base import Substrate
from conductor.profiles import FASTAPI_SAAS
from conductor.scaffold import CommandRunner, scaffold


class ScaffoldOnramp:
    def __init__(self, runner: CommandRunner | None = None) -> None:
        self._runner = runner

    def prepare(self, config: MissionConfig, dest: Path) -> Substrate:
        result = scaffold(config, dest, runner=self._runner)
        return Substrate(
            repo_path=result.repo_path,
            profile=FASTAPI_SAAS,
            design_md_path=result.design_md_path,
        )
```

Replace `conductor/onramp/__init__.py` with:

```python
# conductor/onramp/__init__.py
"""Onramps : sélection de la bretelle selon le mode/la distance à la cible."""

from __future__ import annotations

from conductor.onramp.base import Onramp, Substrate
from conductor.onramp.scaffold_onramp import ScaffoldOnramp

__all__ = ["Onramp", "ScaffoldOnramp", "Substrate", "select_onramp"]


def select_onramp(mode: str) -> Onramp:
    """Choisit la bretelle. brownfield (None/Adapter/Builder) arrive aux epics BA/BC/BB."""
    if mode == "greenfield":
        return ScaffoldOnramp()
    raise NotImplementedError(
        "Onramp brownfield à venir (epic BA : NoOnramp, puis BC/BB) — mode non supporté en B0."
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_onramp.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Lint, type, commit**

```bash
uv run ruff check . && uv run mypy
git add conductor/onramp/
git add tests/test_onramp.py
git commit -m "feat(brownfield): ScaffoldOnramp greenfield + select_onramp (B0)"
```

---

## Task 5 : `mode` dans `MissionConfig` + cadrage

**Files:**
- Modify: `conductor/contracts.py`
- Modify: `conductor/cadrage.py`
- Test: `tests/test_cadrage.py` (append)

- [ ] **Step 1: Write the failing test (append)**

```python
# tests/test_cadrage.py — AJOUTER à la fin


def test_cadrer_default_mode_is_greenfield() -> None:
    assert cadrer("idée").mode == "greenfield"


def test_cadrer_accepts_brownfield_mode() -> None:
    assert cadrer("idée", mode="brownfield").mode == "brownfield"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cadrage.py -v`
Expected: FAIL with `AttributeError: 'MissionConfig' object has no attribute 'mode'`.

- [ ] **Step 3a: Add `mode` to `MissionConfig`**

In `conductor/contracts.py`, inside `class MissionConfig`, add the field right after `idea: str`:

```python
    mode: Literal["greenfield", "brownfield"] = "greenfield"
```

(`Literal` is already imported in `contracts.py`.)

- [ ] **Step 3b: Thread `mode` through `cadrer`**

In `conductor/cadrage.py`, change the `cadrer` signature to add the parameter (after `idea`):

```python
def cadrer(
    idea: str,
    *,
    mode: Literal["greenfield", "brownfield"] = "greenfield",
    target: str = "fastapi-saas",
    brand_charter: Path = DEFAULT_CHARTER,
    style_slug: str = DEFAULT_STYLE,
    budget: str | None = None,
    deadline: str | None = None,
    bricks: list[BrickChoice] | None = None,
) -> MissionConfig:
```

Add `from typing import Literal` to the imports of `conductor/cadrage.py`. Then add `mode=mode,` to the `MissionConfig(...)` constructor call (right after `idea=idea.strip(),`).

- [ ] **Step 4: Run tests to verify they pass (incl. existing)**

Run: `uv run pytest tests/test_cadrage.py -v`
Expected: PASS (existing 6 + new 2 = 8 tests).

- [ ] **Step 5: Lint, type, commit**

```bash
uv run ruff check . && uv run mypy
git add conductor/contracts.py conductor/cadrage.py tests/test_cadrage.py
git commit -m "feat(brownfield): mode greenfield/brownfield dans MissionConfig + cadrage (B0)"
```

---

## Task 6 : le pont BMAD (C) consomme un `Substrate`

**Files:**
- Modify: `conductor/bmad_bridge.py`
- Test: `tests/test_bmad_bridge.py`

- [ ] **Step 1: Update the test to feed a `Substrate` (replace the `_scaffold` helper)**

In `tests/test_bmad_bridge.py`, replace the import block and the `_scaffold` helper:

```python
# Remplacer "from conductor.contracts import BmadPlan, ScaffoldResult" par :
from conductor.contracts import BmadPlan
from conductor.onramp.base import Substrate
from conductor.profiles import FASTAPI_SAAS

# Et la classe FakePlanner : son plan(self, scaffold) devient plan(self, substrate)
class FakePlanner:
    def plan(self, substrate: Substrate) -> BmadPlan:
        return BmadPlan(
            prd_path=Path("PRD.md"),
            architecture_path=Path("architecture.md"),
            epics_md=Path("_bmad-output/planning-artifacts/epics.md"),
        )


# Remplacer _scaffold(tmp) par :
def _substrate(tmp: Path) -> Substrate:
    return Substrate(repo_path=tmp, profile=FASTAPI_SAAS, design_md_path=tmp / "DESIGN.md")
```

Then replace the three call sites `_scaffold(tmp_path)` with `_substrate(tmp_path)` in the test functions.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_bmad_bridge.py -v`
Expected: FAIL (type/usage mismatch — `lancer_planification`/`DefaultBmadPlanner` still expect `ScaffoldResult`).

- [ ] **Step 3: Switch `bmad_bridge` to `Substrate`**

In `conductor/bmad_bridge.py`:

Replace the import `from conductor.contracts import BmadPlan, ScaffoldResult` with:

```python
from conductor.contracts import BmadPlan
from conductor.onramp.base import Substrate
```

Change the `BmadPlanner` protocol and `DefaultBmadPlanner.plan` and `lancer_planification` to take a `Substrate` (the only attribute used is `.repo_path`):

```python
class BmadPlanner(Protocol):
    """Produit un BmadPlan (PRD, architecture, epics) à partir d'un substrat."""

    def plan(self, substrate: Substrate) -> BmadPlan: ...


class DefaultBmadPlanner:
    def plan(self, substrate: Substrate) -> BmadPlan:
        subprocess.run(BMAD_INSTALL, cwd=substrate.repo_path, shell=True, check=False)
        epics = substrate.repo_path / EPICS_FILE
        if not epics.exists():
            raise HitlPending(
                "Planification BMAD à réaliser : produire "
                f"{EPICS_FILE} dans {substrate.repo_path}, puis approuver (HITL 1)."
            )
        return BmadPlan(
            prd_path=substrate.repo_path / PLANNING_DIR / "PRD.md",
            architecture_path=substrate.repo_path / PLANNING_DIR / "architecture.md",
            epics_md=epics,
        )


def lancer_planification(
    substrate: Substrate,
    *,
    planner: BmadPlanner | None = None,
    gate: HumanGate | None = None,
) -> BmadPlan:
    """C · brief → PRD → architecture → epics → stories ; suspend sur HITL 1."""
    plan = (planner or DefaultBmadPlanner()).plan(substrate)
    if not (gate or ManualGate()).approve("PRD & architecture (HITL 1)", plan):
        raise HitlPending("HITL 1 — validation du PRD & de l'architecture requise avant le dev.")
    return plan.model_copy(update={"hitl1_approved": True})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_bmad_bridge.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Lint, type, commit**

```bash
uv run ruff check . && uv run mypy
git add conductor/bmad_bridge.py tests/test_bmad_bridge.py
git commit -m "refactor(brownfield): le pont BMAD consomme un Substrate (B0)"
```

---

## Task 7 : recâbler `run()` sur l'onramp + garde anti-régression greenfield

**Files:**
- Modify: `conductor/__main__.py`
- Test: `tests/test_e2e_master.py`

- [ ] **Step 1: Rewrite the two e2e tests to go through the onramp**

In `tests/test_e2e_master.py`, replace `test_pipeline_order_is_wired_scaffold_first` and `test_run_pauses_at_hitl1_by_default` with:

```python
def test_pipeline_order_is_wired_scaffold_first(monkeypatch: pytest.MonkeyPatch) -> None:
    """run() câble A → onramp(B) → C → D → E ; l'onramp (scaffold-first) précède C."""
    from pathlib import Path

    from conductor.contracts import ScaffoldResult
    from conductor.onramp.base import Substrate
    from conductor.profiles import FASTAPI_SAAS

    calls: list[str] = []

    def rec(name: str) -> Callable[..., object]:
        def _f(*_a: object, **_k: object) -> object:
            calls.append(name)
            return object()

        return _f

    class RecOnramp:
        def prepare(self, config: object, dest: Path) -> Substrate:
            calls.append("B")
            return Substrate(repo_path=dest, profile=FASTAPI_SAAS, design_md_path=dest / "d.md")

    monkeypatch.setattr(cli, "cadrer", rec("A"))
    monkeypatch.setattr(cli, "select_onramp", lambda _mode: RecOnramp())
    monkeypatch.setattr(cli, "lancer_planification", rec("C"))
    monkeypatch.setattr(cli, "preparer_sprint", rec("D"))
    monkeypatch.setattr(cli, "superviser", rec("E"))

    cli.run("idée de test")
    assert calls == ["A", "B", "C", "D", "E"]


def test_run_pauses_at_hitl1_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Défaut greenfield : on neutralise l'onramp (pas de copier) et l'install BMAD (pas de npx) ;
    la logique réelle de C atteint le point HITL non approuvé → HitlPending."""
    from conductor.contracts import MissionConfig
    from conductor.governance import HitlPending
    from conductor.onramp.base import Substrate
    from conductor.profiles import FASTAPI_SAAS

    class FakeOnramp:
        def prepare(self, config: MissionConfig, dest: Path) -> Substrate:
            return Substrate(repo_path=dest, profile=FASTAPI_SAAS, design_md_path=dest / "d.md")

    monkeypatch.setattr(cli, "select_onramp", lambda _mode: FakeOnramp())
    monkeypatch.setattr("conductor.bmad_bridge.subprocess.run", lambda *a, **k: None)

    with pytest.raises(HitlPending):
        cli.run("un CRM pour artisans", workdir=tmp_path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_e2e_master.py -v`
Expected: FAIL with `AttributeError: <module 'conductor.__main__'> does not have the attribute 'select_onramp'`.

- [ ] **Step 3: Rewire `run()`**

In `conductor/__main__.py`, update the imports and `run()`:

Replace `from conductor.scaffold import scaffold` with:

```python
from conductor.onramp import select_onramp
```

Replace the body of `run()` with:

```python
def run(idea: str, *, workdir: Path = Path("generated")) -> None:
    """Orchestration de bout en bout : A → B (onramp) → C (HITL 1) → D → E (HITL 2)."""
    mission = cadrer(idea)  # A
    dest = workdir / _slug(idea)
    substrate = select_onramp(mission.mode).prepare(mission, dest)  # B — scaffold-first (greenfield)
    plan = lancer_planification(substrate)  # C — pose HITL 1 (pause si non approuvé)
    layout = preparer_sprint(plan, dest)  # D — placement & config (pas de graphe, S-1)
    superviser(layout)  # E — /bad + double gate, pose HITL 2
```

- [ ] **Step 4: Run the FULL suite to verify zero greenfield regression**

Run: `uv run ruff check . && uv run mypy && uv run pytest`
Expected: ruff clean, mypy success, **all tests pass** (les tests existants greenfield inchangés + nouveaux).

- [ ] **Step 5: Commit**

```bash
git add conductor/__main__.py tests/test_e2e_master.py
git commit -m "refactor(brownfield): run() passe par l'onramp (greenfield inchangé) (B0)"
```

---

## Définition de fin (gate de sortie B0)

- [ ] `uv run ruff check .` — clean
- [ ] `uv run mypy` — success (strict)
- [ ] `uv run pytest` — tout vert (greenfield identique + nouveaux tests)
- [ ] `conductor run "<idée>"` se comporte comme avant (scaffold-first via `ScaffoldOnramp`, pause à HITL 1)
- [ ] `select_onramp("brownfield")` lève une `NotImplementedError` explicite pointant vers BA

---

## Self-Review (effectuée)

**Couverture spec (B0) :** `TargetProfile` (T1), profil fastapi réifié + `catalog`→`brick_catalog` (T1), `code_gate` profile-aware (T2), `Substrate`+`Onramp` (T3), `ScaffoldOnramp` enveloppant scaffold (T4), `mode` cadrage/CLI (T5), pipeline sur Substrate (T6), recâblage + zéro régression greenfield (T7). Les onramps None/Adapter/Builder, l'ingestion, le RegressionGate et les planners brownfield relèvent de BA/BC/BB (hors B0) — `select_onramp("brownfield")` lève une erreur explicite en attendant.

**Placeholders :** aucun — chaque step contient le code réel.

**Cohérence des types :** `Substrate` (repo_path/profile/design_md_path/baseline/arch_map/declared_degradation) est défini en T3 et consommé identiquement en T4/T6/T7 ; `run_code_gate(..., profile=...)` (T2) cohérent avec `FASTAPI_SAAS.code_check` (T1) ; `select_onramp(mode)` (T4) ↔ `mission.mode` (T5) ↔ `run()` (T7) ; `lancer_planification(substrate)` (T6) ↔ appel dans `run()` (T7).
