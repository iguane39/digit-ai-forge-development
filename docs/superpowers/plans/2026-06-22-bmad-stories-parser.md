# B-3 · Parsing des stories BMAD — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development ou executing-plans. Checkbox steps. Toujours afficher la sortie des gates.

**Goal:** Parser `epics.md` en `list[Story]` (métadonnées seules) et peupler `BmadPlan.stories` dans `ClaudeCliBmadPlanner`, pour alimenter le gate spec-compliance.

**Architecture:** Fonction pure `parse_epics` (machine à états ligne par ligne) dans un nouveau module harness ; câblage dans le planner réel avec fallback `stories=[]`. **Ne reconstruit pas le graphe** (décision 01).

**Tech Stack:** Python 3.11+, pydantic v2 (`Story` existant), `re`, pytest, ruff, mypy --strict, uv. Branche `feat/bmad-stories-parser` (depuis main). Spec : [docs/superpowers/specs/2026-06-22-bmad-stories-parser-design.md](../specs/2026-06-22-bmad-stories-parser-design.md). CWD : `digitai-saas-forge/`.

---

## Task 1 : `parse_epics` (parser pur)

**Files:** Create `conductor/harness/epics_parser.py`; Test `tests/test_epics_parser.py`.

- [ ] **Step 1: failing tests (create `tests/test_epics_parser.py`)**
```python
"""Parser epics.md → list[Story] : métadonnées seules, tolérant, fallback []."""

from __future__ import annotations

from conductor.harness.epics_parser import parse_epics

_SAMPLE = """# Epic 6 : Authentification

## Story 6.1 : Connexion SSO
**GH Issue:** #142
### Acceptance Criteria
- L'utilisateur se connecte via le fournisseur SSO
- Un échec affiche un message clair

## Story 6.2 : Déconnexion
### Critères d'acceptation
- La session est invalidée côté serveur
"""


def test_parse_two_stories_with_acceptance() -> None:
    stories = parse_epics(_SAMPLE)
    assert [s.id for s in stories] == ["6.1", "6.2"]
    assert stories[0].title == "Connexion SSO"
    assert stories[0].gh_issue == 142
    assert "fournisseur SSO" in stories[0].acceptance[0]
    assert len(stories[0].acceptance) == 2
    assert stories[1].acceptance == ["La session est invalidée côté serveur"]


def test_story_without_acceptance_section() -> None:
    text = "# Epic 1\n## Story 1.1 : Sans critères\n"
    stories = parse_epics(text)
    assert stories[0].id == "1.1"
    assert stories[0].acceptance == []


def test_epic_id_not_taken_for_story() -> None:
    # "Epic 6" (sans point) ne doit pas devenir une story.
    assert parse_epics("# Epic 6 : Titre\n") == []


def test_empty_or_prose_yields_empty() -> None:
    assert parse_epics("") == []
    assert parse_epics("Juste de la prose sans story numérotée.\n") == []


def test_epic_label_attached_to_story() -> None:
    stories = parse_epics(_SAMPLE)
    assert "Authentification" in stories[0].epic
```

- [ ] **Step 2:** `uv run pytest tests/test_epics_parser.py -v` → FAIL (module absent).

- [ ] **Step 3: create `conductor/harness/epics_parser.py`**
```python
"""Parser tolérant de epics.md → list[Story] (métadonnées seules).

Machine à états ligne par ligne. N'extrait QUE des métadonnées plates (id, epic, title,
acceptance, gh_issue) — ne reconstruit PAS le graphe de dépendances (BAD le fait, décision 01).
Fonction pure, déterministe, sans réseau. Fallback : aucune story → [].
"""

from __future__ import annotations

import re

from conductor.contracts import Story

_EPIC_RE = re.compile(r"^#+\s*(?:epic|épique)\s*(\d+)\b[:\-\s]*(.*)$", re.IGNORECASE)
_STORY_RE = re.compile(
    r"^#+\s*(?:story|récit|user story)?\s*(\d+\.\d+)\b[:\-\s]*(.*)$", re.IGNORECASE
)
_GH_RE = re.compile(r"\*\*\s*GH Issue\s*:\s*\*\*\s*#?\s*(\d+)", re.IGNORECASE)
_BULLET_RE = re.compile(r"^\s*[-*]\s+(.+?)\s*$")
_HEADING_RE = re.compile(r"^\s*(?:#+|\*\*)")
_ACCEPTANCE_RE = re.compile(r"acceptance|critères?\s+d['’]acceptation", re.IGNORECASE)


def parse_epics(text: str) -> list[Story]:
    """Extrait les stories (sections de epics.md). Renvoie [] si aucune story `X.Y`."""
    stories: list[Story] = []
    current: dict[str, object] | None = None
    epic_label = ""
    in_acceptance = False

    def _flush() -> None:
        if current is not None:
            stories.append(
                Story(
                    id=str(current["id"]),
                    epic=str(current["epic"]),
                    title=str(current["title"]),
                    acceptance=list(current["acceptance"]),  # type: ignore[arg-type]
                    gh_issue=current["gh_issue"],  # type: ignore[arg-type]
                )
            )

    for raw in text.splitlines():
        line = raw.rstrip()
        story_m = _STORY_RE.match(line)
        if story_m:
            _flush()
            current = {
                "id": story_m.group(1),
                "title": story_m.group(2).strip(),
                "epic": epic_label,
                "acceptance": [],
                "gh_issue": None,
            }
            in_acceptance = False
            continue
        epic_m = _EPIC_RE.match(line)
        if epic_m:
            _flush()
            current = None
            epic_label = epic_m.group(2).strip() or f"epic-{epic_m.group(1)}"
            in_acceptance = False
            continue
        if current is None:
            continue
        gh_m = _GH_RE.search(line)
        if gh_m:
            current["gh_issue"] = int(gh_m.group(1))
            continue
        if _HEADING_RE.match(line):
            in_acceptance = bool(_ACCEPTANCE_RE.search(line))
            continue
        if in_acceptance:
            bullet_m = _BULLET_RE.match(line)
            if bullet_m:
                acceptance = current["acceptance"]
                assert isinstance(acceptance, list)
                acceptance.append(bullet_m.group(1))

    _flush()
    return stories
```

- [ ] **Step 4:** `uv run pytest tests/test_epics_parser.py -v` → PASS (5).

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/harness/epics_parser.py tests/test_epics_parser.py
git commit -m "feat(bmad): parse_epics — métadonnées de story depuis epics.md (tolérant, fallback [])"
```

---

## Task 2 : câbler `parse_epics` dans `ClaudeCliBmadPlanner`

**Files:** Modify `conductor/harness/bmad_planner.py`; Test (append) `tests/test_epics_parser.py` (ou le test bmad existant).

- [ ] **Step 1: failing test (append `tests/test_epics_parser.py`)**
```python
from pathlib import Path

from conductor.harness.bmad_planner import ClaudeCliBmadPlanner
from conductor.onramp.base import Substrate
from conductor.profiles import FASTAPI_SAAS


class _WritingCli:
    """Fake CliRunner : écrit un epics.md échantillon dans planning-artifacts au déclenchement."""

    def __init__(self, body: str) -> None:
        self._body = body

    def run(self, prompt: str, cwd: Path) -> str:
        planning = cwd / "_bmad-output" / "planning-artifacts"
        planning.mkdir(parents=True, exist_ok=True)
        (planning / "epics.md").write_text(self._body, encoding="utf-8")
        return "ok"


def _substrate(tmp: Path) -> Substrate:
    return Substrate(repo_path=tmp, profile=FASTAPI_SAAS, design_md_path=tmp / "DESIGN.md")


def test_planner_populates_stories(tmp_path: Path) -> None:
    plan = ClaudeCliBmadPlanner(cli=_WritingCli(_SAMPLE)).plan(_substrate(tmp_path))
    assert [s.id for s in plan.stories] == ["6.1", "6.2"]
    assert plan.hitl1_approved is False


def test_planner_unparseable_epics_yields_empty_stories(tmp_path: Path) -> None:
    plan = ClaudeCliBmadPlanner(cli=_WritingCli("prose sans story")).plan(_substrate(tmp_path))
    assert plan.stories == []  # fallback : juge pass-through, pas de régression
```

- [ ] **Step 2:** `uv run pytest tests/test_epics_parser.py -k planner -v` → FAIL (stories vide / non câblé).

- [ ] **Step 3: modify `conductor/harness/bmad_planner.py`**

Add import (en tête) :
```python
from conductor.harness.epics_parser import parse_epics
```
Dans `plan`, après le contrôle d'existence de `epics`, peupler `stories` :
```python
        return BmadPlan(
            prd_path=planning / "PRD.md",
            architecture_path=planning / "architecture.md",
            epics_md=epics,
            stories=parse_epics(epics.read_text(encoding="utf-8")),
        )
```

- [ ] **Step 4:** `uv run pytest tests/test_epics_parser.py -v` → PASS (tous). Full suite (show output) — les tests bmad existants restent verts (`stories` passe de `[]` à peuplé seulement quand un `epics.md` parseable est présent ; les fakes existants qui pré-créent un `epics.md` minimal sans story `X.Y` → `stories=[]`, inchangé).

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/harness/bmad_planner.py tests/test_epics_parser.py
git commit -m "feat(bmad): ClaudeCliBmadPlanner peuple stories via parse_epics (fallback [])"
```

---

## Définition de fin
- [ ] ruff clean · mypy success · pytest vert.
- [ ] `parse_epics` extrait id/epic/title/acceptance/gh_issue ; fallback `[]` sur texte non parseable.
- [ ] `ClaudeCliBmadPlanner.plan` peuple `stories` ; `HitlPending` si `epics.md` absent (inchangé).
- [ ] Aucun graphe reconstruit (métadonnées seules, décision 01 préservée).

## Self-Review
**Couverture spec :** T1 → `parse_epics` + heuristiques (§3,§4,§5) ; T2 → câblage planner + fallback (§3,§6). **Placeholders :** `_SAMPLE` est une fixture réelle. **Cohérence des noms :** `parse_epics(text)->list[Story]`, `Story` (contracts), `ClaudeCliBmadPlanner.plan` → `BmadPlan(stories=…)` — identiques dans les deux tâches.
