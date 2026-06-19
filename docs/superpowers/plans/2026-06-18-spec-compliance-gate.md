# Gate de conformité au spec — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax. Toujours afficher la sortie des gates.

**Goal:** Greffer un gate de conformité au spec (juge remédiable) entre le double gate et HITL 2 dans le superviseur, avec persistance des findings dans `SPEC_FINDINGS.md`.

**Architecture:** Miroir du pattern des 3 effets réels (Protocol + `Default*` déterministe + `ClaudeCli*` opt-in + `resolve_*` + fakes). Le verdict spec rejoint `_passes` → remédiation bornée (3 retries) → `blocked`. Défaut = pass-through déterministe (CI inchangée). Opt-in `CONDUCTOR_ENABLE_SPEC_REVIEW`.

**Tech Stack:** Python 3.11+, pydantic v2, pytest, ruff, mypy --strict, uv. Branche `feat/spec-compliance-gate` (depuis main). Spec : [docs/superpowers/specs/2026-06-18-spec-compliance-gate-design.md](../specs/2026-06-18-spec-compliance-gate-design.md).

**Convention CWD :** toutes les commandes s'exécutent depuis `digitai-saas-forge/` (racine du package conductor).

---

## Task 1 : `SpecVerdict` (contracts)

**Files:** Modify `conductor/contracts.py`; Test `tests/test_spec_compliance.py` (create).

- [ ] **Step 1: failing test (create `tests/test_spec_compliance.py`)**
```python
"""Gate de conformité au spec : verdict, reviewer, persistance, intégration superviseur."""

from __future__ import annotations

from conductor.contracts import SpecVerdict


def test_specverdict_from_findings_over_build_only_passes() -> None:
    v = SpecVerdict.from_findings([{"kind": "over-build", "criterion": "x", "detail": "y"}])
    assert v.passed is True
    assert len(v.findings) == 1


def test_specverdict_from_findings_under_build_fails() -> None:
    v = SpecVerdict.from_findings([{"kind": "under-build", "criterion": "x", "detail": "y"}])
    assert v.passed is False


def test_specverdict_from_findings_empty_passes() -> None:
    assert SpecVerdict.from_findings([]).passed is True
```

- [ ] **Step 2:** `uv run pytest tests/test_spec_compliance.py -v` → FAIL (ImportError `SpecVerdict`).

- [ ] **Step 3: add `SpecVerdict` to `conductor/contracts.py`** (après `GateVerdict`)
```python
class SpecVerdict(BaseModel):
    """Verdict de conformité au spec d'une story.

    `under-build` (critère non tenu) est bloquant ; `over-build` (comportement non demandé) est
    consultatif. `passed` est faux dès qu'il existe ≥1 finding `under-build`.
    """

    passed: bool
    findings: list[dict[str, str]] = Field(default_factory=list)
    log_ref: str = ""

    @classmethod
    def from_findings(cls, findings: list[dict[str, str]], *, log_ref: str = "") -> "SpecVerdict":
        blocking = any(f.get("kind") == "under-build" for f in findings)
        return cls(passed=not blocking, findings=findings, log_ref=log_ref)
```

- [ ] **Step 4:** `uv run pytest tests/test_spec_compliance.py -v` → PASS (3).

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/contracts.py tests/test_spec_compliance.py
git commit -m "feat(spec-gate): SpecVerdict (under-build bloquant, over-build consultatif)"
```

---

## Task 2 : `SpecComplianceReviewer` + `DefaultSpecReviewer` + branchement `_passes`

**Files:** Modify `conductor/supervisor.py`; Test (append) `tests/test_spec_compliance.py`.

Contexte : `superviser` reçoit un `spec_reviewer` (résolu si None) et la liste des `stories` (pour retrouver les `acceptance` depuis `outcome.story_id`). Le prédicat `_passes` gagne `spec_ok`.

- [ ] **Step 1: failing test (append `tests/test_spec_compliance.py`)**
```python
from pathlib import Path

from conductor.contracts import BadConfig, BadSprintLayout, Story, StoryOutcome
from conductor.supervisor import DefaultSpecReviewer, superviser


class _StubBad:
    """BadRunner factice : 1 story verte, remédiation idempotente."""

    def __init__(self, outcome: StoryOutcome) -> None:
        self._outcome = outcome

    def run_sprint(self, layout: BadSprintLayout) -> list[StoryOutcome]:
        return [self._outcome]

    def remediate(self, story_id: str, layout: BadSprintLayout) -> StoryOutcome:
        return self._outcome


class _FailingSpecReviewer:
    """Toujours un under-build → spec_ok=False."""

    def review(self, story: Story, outcome: StoryOutcome, cwd: Path) -> object:
        from conductor.contracts import SpecVerdict

        return SpecVerdict.from_findings([{"kind": "under-build", "criterion": "c", "detail": "d"}])


def _layout(tmp_path: Path) -> BadSprintLayout:
    return BadSprintLayout(
        project_root=tmp_path,
        epics_md=tmp_path / "epics.md",
        sprint_status_yaml=tmp_path / "s.yaml",
        bmad_config_yaml=tmp_path / "c.yaml",
        config=BadConfig(),
    )


def test_default_spec_reviewer_passes(tmp_path: Path) -> None:
    v = DefaultSpecReviewer().review(Story(id="1", epic="e", title="t"), StoryOutcome(story_id="1", code_ok=True), tmp_path)
    assert v.passed is True


def test_spec_failure_blocks_story(tmp_path: Path) -> None:
    outcome = StoryOutcome(story_id="1", code_ok=True, pr_url="http://pr/1")
    report = superviser(
        _layout(tmp_path),
        bad=_StubBad(outcome),
        design_check=lambda _o: __import__("conductor.contracts", fromlist=["GateVerdict"]).GateVerdict(gate="design", passed=True),
        hitl=type("_G", (), {"approve": lambda self, *a: True})(),
        spec_reviewer=_FailingSpecReviewer(),
        stories=[Story(id="1", epic="e", title="t", acceptance=["c"])],
    )
    assert report.results[0].status == "blocked"  # under-build non résolu → blocked après retries
```

- [ ] **Step 2:** `uv run pytest tests/test_spec_compliance.py -v` → FAIL (ImportError `DefaultSpecReviewer` / signature `superviser`).

- [ ] **Step 3: modify `conductor/supervisor.py`**

Add imports (en tête, avec les autres) :
```python
from pathlib import Path

from conductor.contracts import (
    BadSprintLayout,
    GateVerdict,
    SpecVerdict,
    SprintReport,
    Story,
    StoryOutcome,
    StoryResult,
)
```
Add the Protocol + default (après `DesignCheck = ...`) :
```python
class SpecComplianceReviewer(Protocol):
    """Juge la conformité d'une PR de story à ses critères d'acceptation."""

    def review(self, story: Story, outcome: StoryOutcome, cwd: Path) -> SpecVerdict: ...


class DefaultSpecReviewer:
    """Pass-through déterministe : aucune revue, aucun finding (comportement par défaut)."""

    def review(self, story: Story, outcome: StoryOutcome, cwd: Path) -> SpecVerdict:
        return SpecVerdict(passed=True)
```
Extend `superviser` signature (ajouter deux paramètres avant `max_retries`) :
```python
def superviser(
    layout: BadSprintLayout,
    *,
    bad: BadRunner | None = None,
    design_check: DesignCheck | None = None,
    hitl: HumanGate | None = None,
    spec_reviewer: SpecComplianceReviewer | None = None,
    stories: list[Story] | None = None,
    max_retries: int = GATE_MAX_RETRIES,
) -> SprintReport:
```
Inside, after the `gate = ...` / `check = ...` lines, resolve the reviewer + build the lookup :
```python
    if spec_reviewer is not None:
        reviewer: SpecComplianceReviewer = spec_reviewer
    else:
        from conductor.harness.resolve import resolve_spec_reviewer

        reviewer = resolve_spec_reviewer()
    story_by_id = {s.id: s for s in (stories or [])}

    def _story_for(o: StoryOutcome) -> Story:
        return story_by_id.get(o.story_id) or Story(id=o.story_id, epic="", title="")
```
Extend `_passes` to add `spec_ok` :
```python
    def _passes(o: StoryOutcome) -> bool:
        design_ok = check(o).passed
        current = {"code": o.code_ok, "design": design_ok}
        no_regression = evaluate_regression(layout.baseline or {}, current).passed
        spec_ok = reviewer.review(_story_for(o), o, layout.project_root).passed
        return o.code_ok and design_ok and no_regression and spec_ok
```

- [ ] **Step 4:** `uv run pytest tests/test_spec_compliance.py -v` → PASS. Full suite (show output) — les tests superviseur existants restent verts (le défaut résolu est pass-through quand `CONDUCTOR_ENABLE_SPEC_REVIEW` n'est pas à 1 ; cf. Task 3). Si la suite tourne sans `claude`, `resolve_spec_reviewer` renvoie `DefaultSpecReviewer`.

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/supervisor.py tests/test_spec_compliance.py
git commit -m "feat(spec-gate): reviewer Protocol + Default + branchement _passes (remédiable)"
```

---

## Task 3 : `resolve_spec_reviewer()` (opt-in)

**Files:** Modify `conductor/harness/resolve.py`; Test (append) `tests/test_spec_compliance.py`.

- [ ] **Step 1: failing test (append `tests/test_spec_compliance.py`)**
```python
import pytest

from conductor.harness.resolve import resolve_spec_reviewer
from conductor.supervisor import DefaultSpecReviewer


def test_resolve_spec_reviewer_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CONDUCTOR_ENABLE_SPEC_REVIEW", raising=False)
    assert isinstance(resolve_spec_reviewer(), DefaultSpecReviewer)


def test_resolve_spec_reviewer_env_zero_is_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_ENABLE_SPEC_REVIEW", "0")
    assert isinstance(resolve_spec_reviewer(), DefaultSpecReviewer)


def test_resolve_spec_reviewer_on_without_claude_is_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONDUCTOR_ENABLE_SPEC_REVIEW", "1")
    monkeypatch.setattr("conductor.harness.resolve.shutil.which", lambda _name: None)
    assert isinstance(resolve_spec_reviewer(), DefaultSpecReviewer)
```

- [ ] **Step 2:** `uv run pytest tests/test_spec_compliance.py -k resolve_spec -v` → FAIL (ImportError).

- [ ] **Step 3: modify `conductor/harness/resolve.py`**

In the `TYPE_CHECKING` block, add the import :
```python
if TYPE_CHECKING:
    from conductor.bmad_bridge import BmadPlanner
    from conductor.supervisor import BadRunner, SpecComplianceReviewer
```
Append the resolver :
```python
def resolve_spec_reviewer() -> SpecComplianceReviewer:
    """ClaudeCliSpecReviewer si CONDUCTOR_ENABLE_SPEC_REVIEW=1 ET `claude` présent ; sinon défaut."""
    from conductor.harness.spec_reviewer import ClaudeCliSpecReviewer
    from conductor.supervisor import DefaultSpecReviewer

    if os.environ.get("CONDUCTOR_ENABLE_SPEC_REVIEW") == "1" and shutil.which("claude") is not None:
        return ClaudeCliSpecReviewer()
    return DefaultSpecReviewer()
```

- [ ] **Step 4:** `uv run pytest tests/test_spec_compliance.py -k resolve_spec -v` → PASS (3). (Le test `on_without_claude` ne déclenche pas l'import de `spec_reviewer` car `which` renvoie None ; l'import est lazy.)

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/harness/resolve.py tests/test_spec_compliance.py
git commit -m "feat(spec-gate): resolve_spec_reviewer (opt-in CONDUCTOR_ENABLE_SPEC_REVIEW)"
```

---

## Task 4 : `ClaudeCliSpecReviewer` (harness, réel)

**Files:** Create `conductor/harness/spec_reviewer.py`; Test (append) `tests/test_spec_compliance.py`.

Miroir de `ClaudeSubagentAnalyzer` : prompt → `CliRunner.run` → parse JSON → fallback gracieux (ne bloque pas en cas d'échec d'interprétation : do-no-harm).

- [ ] **Step 1: failing test (append `tests/test_spec_compliance.py`)**
```python
from conductor.harness.spec_reviewer import ClaudeCliSpecReviewer


class _FakeCli:
    def __init__(self, raw: str) -> None:
        self._raw = raw
        self.prompts: list[str] = []

    def run(self, prompt: str, cwd: Path) -> str:
        self.prompts.append(prompt)
        return self._raw


def test_claude_spec_reviewer_parses_under_build(tmp_path: Path) -> None:
    cli = _FakeCli('{"findings": [{"kind": "under-build", "criterion": "c", "detail": "d", "severity": "moyenne"}]}')
    v = ClaudeCliSpecReviewer(runner=cli).review(
        Story(id="1", epic="e", title="t", acceptance=["c"]), StoryOutcome(story_id="1", code_ok=True, pr_url="http://pr/1"), tmp_path
    )
    assert v.passed is False
    assert "c" in cli.prompts[0]  # critère injecté dans le prompt


def test_claude_spec_reviewer_invalid_json_falls_back_to_pass(tmp_path: Path) -> None:
    v = ClaudeCliSpecReviewer(runner=_FakeCli("pas du json")).review(
        Story(id="1", epic="e", title="t", acceptance=["c"]), StoryOutcome(story_id="1", code_ok=True), tmp_path
    )
    assert v.passed is True  # do-no-harm : interprétation indisponible → ne bloque pas
```

- [ ] **Step 2:** `uv run pytest tests/test_spec_compliance.py -k claude_spec -v` → FAIL (module absent).

- [ ] **Step 3: create `conductor/harness/spec_reviewer.py`**
```python
"""ClaudeCliSpecReviewer — revue de conformité au spec par un sous-agent `claude`.

Confronte les critères d'acceptation d'une story au diff de sa PR. Renvoie un SpecVerdict
(under-build bloquant, over-build consultatif). En cas d'échec d'interprétation (erreur runner ou
JSON invalide), retombe sur `passed=True` (do-no-harm : on ne bloque pas une story sur un juge muet).
"""

from __future__ import annotations

import json
from pathlib import Path

from conductor.contracts import SpecVerdict, Story, StoryOutcome
from conductor.harness.claude_cli import CliRunner, SubprocessClaudeCli

_PROMPT = (
    "Tu es un reviewer de CONFORMITÉ AU SPEC. Story : « {title} ». Critères d'acceptation :\n"
    "{criteria}\n"
    "Confronte le diff de la PR ({pr_url}) à ces critères. Réponds UNIQUEMENT par un objet JSON : "
    '{{"findings": [{{"kind": "under-build"|"over-build", "criterion": "...", '
    '"detail": "...", "severity": "faible|moyenne|élevée"}}]}}. '
    "under-build = critère non tenu ; over-build = comportement non demandé. Aucun texte hors JSON."
)


class ClaudeCliSpecReviewer:
    """Implémente SpecComplianceReviewer : revue réelle via le CLI `claude`."""

    def __init__(self, *, runner: CliRunner | None = None) -> None:
        self._runner: CliRunner = runner or SubprocessClaudeCli()

    def review(self, story: Story, outcome: StoryOutcome, cwd: Path) -> SpecVerdict:
        criteria = "\n".join(f"- {c}" for c in story.acceptance) or "- (aucun critère listé)"
        prompt = _PROMPT.format(title=story.title, criteria=criteria, pr_url=outcome.pr_url or "")
        try:
            raw = self._runner.run(prompt, cwd)
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("réponse non-objet")
            findings = data.get("findings", [])
            if not isinstance(findings, list):
                raise ValueError("findings non-liste")
        except (RuntimeError, ValueError, json.JSONDecodeError):
            return SpecVerdict(passed=True)
        norm = [
            {str(k): str(v) for k, v in f.items()} for f in findings if isinstance(f, dict)
        ]
        return SpecVerdict.from_findings(norm)
```

- [ ] **Step 4:** `uv run pytest tests/test_spec_compliance.py -k claude_spec -v` → PASS (2).

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/harness/spec_reviewer.py tests/test_spec_compliance.py
git commit -m "feat(spec-gate): ClaudeCliSpecReviewer (réel, fallback do-no-harm)"
```

---

## Task 5 : registre `SPEC_FINDINGS.md` + persistance par le superviseur

**Files:** Create `conductor/findings.py`; Create `docs/superpowers/templates/SPEC_FINDINGS.md`; Modify `conductor/supervisor.py`; Test (append) `tests/test_spec_compliance.py`.

Statut : under-build → `traité` si la story finit `ready-for-review`, sinon `non-traité` ; over-build → toujours `non-traité`. Les findings sont capturés à la **première** revue de chaque story (point de détection).

- [ ] **Step 1: failing test (append `tests/test_spec_compliance.py`)**
```python
from conductor.findings import FindingRecord, render_findings_md


def test_render_findings_md_has_status_column() -> None:
    md = render_findings_md([
        FindingRecord(id="SF-1", story="1", kind="under-build", criterion="c", detail="d", severity="moyenne", status="traité", note="corrigé"),
        FindingRecord(id="SF-2", story="1", kind="over-build", criterion="x", detail="y", severity="faible", status="non-traité", note=""),
    ])
    assert "| statut |" in md
    assert "traité" in md and "non-traité" in md
    assert "SF-1" in md and "SF-2" in md


def test_supervisor_writes_findings_file_with_status(tmp_path: Path) -> None:
    outcome = StoryOutcome(story_id="1", code_ok=True, pr_url="http://pr/1")
    superviser(
        _layout(tmp_path),
        bad=_StubBad(outcome),
        design_check=lambda _o: __import__("conductor.contracts", fromlist=["GateVerdict"]).GateVerdict(gate="design", passed=True),
        hitl=type("_G", (), {"approve": lambda self, *a: True})(),
        spec_reviewer=_FailingSpecReviewer(),  # under-build non résolu → blocked → non-traité
        stories=[Story(id="1", epic="e", title="t", acceptance=["c"])],
    )
    findings_md = (tmp_path / "SPEC_FINDINGS.md").read_text(encoding="utf-8")
    assert "under-build" in findings_md
    assert "non-traité" in findings_md  # story blocked → finding non-traité
```

- [ ] **Step 2:** `uv run pytest tests/test_spec_compliance.py -k "findings or writes_findings" -v` → FAIL (module/comportement absents).

- [ ] **Step 3: create `conductor/findings.py`**
```python
"""Registre persistant des findings de conformité au spec (SPEC_FINDINGS.md).

Statut `traité`/`non-traité` pour reprise manuelle ultérieure (HITL 2, ou pré-vol du run suivant).
Rien n'est effacé : on bascule le statut, on conserve l'historique.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

_HEADER = (
    "# SPEC_FINDINGS — conformité au spec\n\n"
    "> Statut : `traité` (corrigé en remédiation) / `non-traité` (à reprendre manuellement).\n\n"
    "| id | story | kind | critère | détail | sévérité | statut | note |\n"
    "|----|-------|------|---------|--------|----------|--------|------|\n"
)


class FindingRecord(BaseModel):
    """Une ligne du registre SPEC_FINDINGS.md."""

    id: str
    story: str
    kind: str  # under-build | over-build
    criterion: str
    detail: str
    severity: str
    status: str  # traité | non-traité
    note: str = ""


def render_findings_md(records: list[FindingRecord]) -> str:
    """Rend le registre complet en Markdown (table à colonne `statut`)."""
    rows = "".join(
        f"| {r.id} | {r.story} | {r.kind} | {r.criterion} | {r.detail} | "
        f"{r.severity} | {r.status} | {r.note} |\n"
        for r in records
    )
    return _HEADER + rows


def write_findings(path: Path, records: list[FindingRecord]) -> None:
    """Écrit le registre sur disque (écrase : la liste fournie est l'état courant complet)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_findings_md(records), encoding="utf-8")
```

- [ ] **Step 4: create the template `docs/superpowers/templates/SPEC_FINDINGS.md`**
```markdown
<!-- TEMPLATE — instancié par run à la racine sous SPEC_FINDINGS.md (écrit par le superviseur). -->
# SPEC_FINDINGS — conformité au spec

> Statut : `traité` (corrigé en remédiation) / `non-traité` (à reprendre manuellement, ex. HITL 2
> ou pré-vol du run suivant). Rien n'est effacé : on bascule le statut, on conserve l'historique.

| id | story | kind | critère | détail | sévérité | statut | note |
|----|-------|------|---------|--------|----------|--------|------|
| SF-1 | <story> | under-build | <critère> | <détail> | moyenne | traité | corrigé au retry |
| SF-2 | <story> | over-build | <critère> | <détail> | faible | non-traité | à reprendre |
```

- [ ] **Step 5: modify `conductor/supervisor.py`** — capturer les findings et écrire le registre.

Add import (en tête) :
```python
from conductor.findings import FindingRecord, write_findings
```
Dans `superviser`, remplacer la boucle `for outcome in runner.run_sprint(layout):` par une version qui capture les findings de première revue et accumule les enregistrements :
```python
    results: list[StoryResult] = []
    all_ready = True
    records: list[FindingRecord] = []
    next_id = 0

    for outcome in runner.run_sprint(layout):
        first = reviewer.review(_story_for(outcome), outcome, layout.project_root)
        attempts = 1
        passed = _passes(outcome)
        while not passed and attempts <= max_retries:
            outcome = runner.remediate(outcome.story_id, layout)  # noqa: PLW2901
            attempts += 1
            passed = _passes(outcome)

        status = "ready-for-review" if passed else "blocked"
        if not passed:
            all_ready = False
        results.append(
            StoryResult(
                story_id=outcome.story_id, status=status, attempts=attempts, pr_url=outcome.pr_url
            )
        )
        for f in first.findings:
            next_id += 1
            kind = f.get("kind", "")
            resolved = kind == "under-build" and status == "ready-for-review"
            records.append(
                FindingRecord(
                    id=f"SF-{next_id}",
                    story=outcome.story_id,
                    kind=kind,
                    criterion=f.get("criterion", ""),
                    detail=f.get("detail", ""),
                    severity=f.get("severity", ""),
                    status="traité" if resolved else "non-traité",
                    note="corrigé en remédiation" if resolved else "à reprendre manuellement",
                )
            )

    if records:
        write_findings(layout.project_root / "SPEC_FINDINGS.md", records)
```
(Garder le `hitl2 = ...` et le `return SprintReport(...)` inchangés après la boucle. La double revue — `first` pour capture, `_passes` pour le verdict — est volontaire : `first` fige les findings au point de détection.)

- [ ] **Step 6:** `uv run pytest tests/test_spec_compliance.py -v` → PASS (tous). Full suite (show output) — verte : sans opt-in, le reviewer est pass-through → `first.findings` vide → aucun `SPEC_FINDINGS.md` écrit (comportement inchangé).

- [ ] **Step 7: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/findings.py conductor/supervisor.py docs/superpowers/templates/SPEC_FINDINGS.md tests/test_spec_compliance.py
git commit -m "feat(spec-gate): registre SPEC_FINDINGS.md (statut traité/non-traité)"
```

---

## Task 6 : note pilote (playbooks)

**Files:** Modify `docs/superpowers/unattended-run-playbook.md`; Modify `docs/conductor-run-playbook.md`.

- [ ] **Step 1: unattended-run-playbook — ajouter le gate spec côté PRÉSERVÉ de la frontière.**
Dans la table « cérémonie / gouvernance », sous la ligne « Non-régression », insérer :
```
| Gate spec-compliance (opt-in `CONDUCTOR_ENABLE_SPEC_REVIEW`) | — |
```

- [ ] **Step 2: conductor-run-playbook (EN) — note pilote** (après la section « Real BMAD planning (pilot) », ajouter) :
```markdown
## Real spec-compliance gate (pilot)

The spec-compliance gate is **off by default** (the supervisor runs the dual gate + non-regression
only). To enable a per-story **spec-conformance review** via `claude -p`, set
`CONDUCTOR_ENABLE_SPEC_REVIEW=1` (requires `claude` authenticated). It compares each story's
acceptance criteria to its PR diff: an **under-build** (unmet criterion) blocks the story (it joins
the bounded 3-retry remediation, then `blocked`); an **over-build** (behavior beyond spec) is
advisory. All findings are persisted to `SPEC_FINDINGS.md` with a `traité`/`non-traité` status for
later manual pickup. No merge is affected; HITL 2 is unchanged.
```

- [ ] **Step 3: full gate (doc-only, show output)** `uv run ruff check . ; uv run mypy ; uv run pytest -q` (tout vert).

- [ ] **Step 4: commit**
```
git add docs/superpowers/unattended-run-playbook.md docs/conductor-run-playbook.md
git commit -m "docs(spec-gate): note pilote + frontière (gate spec côté gouvernance)"
```

---

## Définition de fin
- [ ] ruff clean · mypy success · pytest vert (sans `claude` : reviewer pass-through).
- [ ] `SpecVerdict` (under-build bloquant / over-build consultatif) ; gate intégré à `_passes`.
- [ ] `resolve_spec_reviewer` opt-in `CONDUCTOR_ENABLE_SPEC_REVIEW` ; défaut déterministe.
- [ ] `ClaudeCliSpecReviewer` réel avec fallback do-no-harm.
- [ ] `SPEC_FINDINGS.md` écrit avec statut traité/non-traité quand des findings existent.
- [ ] Invariants merge intacts (`auto_pr_merge=false`, HITL 2, `SprintReport.merged=False`).

## Self-Review
**Couverture spec :** T1→SpecVerdict (§3) ; T2→Protocol+Default+`_passes` (§3,§4) ; T3→resolve opt-in (§2C,§3) ; T4→ClaudeCliSpecReviewer (§3) ; T5→SPEC_FINDINGS.md (§7) ; T6→note pilote+frontière (§7 séquencement). **Placeholders :** `<story>`/`<critère>` dans le template = variables de gabarit. **Cohérence des noms :** `SpecVerdict.from_findings`, `SpecComplianceReviewer.review(story, outcome, cwd)`, `resolve_spec_reviewer`, `FindingRecord`, `write_findings`, env `CONDUCTOR_ENABLE_SPEC_REVIEW` — identiques dans toutes les tâches.
