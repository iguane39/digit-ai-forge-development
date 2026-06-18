# Tech-debt consolidation #2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox steps. Toujours afficher la sortie des gates.

**Goal:** Résorber les 3 suivis tracés post-pont-réel, sans changer le comportement observable (sauf l'indication de troncature et la fusion epics.md). Greenfield + brownfield + pont réel inchangés ; gate vert maintenu.

**Tech Stack:** Python 3.11+, pydantic v2, pytest, ruff, mypy --strict, uv. Branche `epic-td2-consolidation` (depuis main).

---

## Task 1 : ellipsis sur stderr tronqué

**Files:** Create `conductor/harness/_text.py`; Modify `conductor/harness/claude_cli.py`, `conductor/harness/gh.py`; Test `tests/test_text.py`.

- [ ] **Step 1: failing test `tests/test_text.py`**
```python
"""clip : tronque proprement avec ellipsis (messages d'erreur lisibles)."""

from __future__ import annotations

from conductor.harness._text import clip


def test_clip_short_unchanged() -> None:
    assert clip("court", 100) == "court"


def test_clip_long_adds_ellipsis() -> None:
    out = clip("x" * 50, 10)
    assert out == "x" * 10 + "…"


def test_clip_exact_unchanged() -> None:
    assert clip("x" * 10, 10) == "x" * 10
```

- [ ] **Step 2:** run `uv run pytest tests/test_text.py -v` → FAIL.

- [ ] **Step 3: create `conductor/harness/_text.py`**
```python
"""Petits utilitaires texte pour les adapters du harness."""

from __future__ import annotations


def clip(text: str, limit: int) -> str:
    """Tronque `text` à `limit` caractères, en signalant la troncature par une ellipsis."""
    if len(text) <= limit:
        return text
    return text[:limit] + "…"
```

- [ ] **Step 3b:** use `clip` in the two stderr messages :
  - `conductor/harness/claude_cli.py` : add `from conductor.harness._text import clip`; replace `proc.stderr[:500]` (in the non-zero RuntimeError message) with `clip(proc.stderr, 500)`.
  - `conductor/harness/gh.py` : add `from conductor.harness._text import clip`; replace `proc.stderr[:500]` with `clip(proc.stderr, 500)`.

- [ ] **Step 4:** run `uv run pytest tests/test_text.py -v` → PASS (3). Full suite (show output) — existing claude_cli/gh tests still green (their nonzero tests use empty stderr, so `clip("",500)` == "").

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/harness/_text.py conductor/harness/claude_cli.py conductor/harness/gh.py tests/test_text.py
git commit -m "refactor(td2): clip() — ellipsis sur stderr tronqué (claude_cli + gh)"
```

---

## Task 2 : `CompositePlanner` écrit un `epics.md` fusionné sur disque

**Files:** Modify `conductor/planners/complement.py`; Test (append) `tests/test_planners.py`.

Contexte : `CompositePlanner.plan` concatène les `stories` en mémoire mais `epics_md` pointe sur le fichier du 1ᵉʳ planner ; pour `intent=both`, BAD lit `epics.md` sur DISQUE et raterait le contenu du 2ᵉ planner. On fusionne le contenu sur disque. Le 2ᵉ planner peut écrire sur le MÊME chemin → on lit le contenu du 1ᵉʳ AVANT de lancer le 2ᵉ.

- [ ] **Step 1: failing test (append `tests/test_planners.py`)**
```python
def test_composite_writes_merged_epics_on_disk(tmp_path: Path) -> None:
    a_file = tmp_path / "a_epics.md"
    a_file.write_text("# Remediation\n- R1\n", encoding="utf-8")
    b_file = tmp_path / "b_epics.md"
    b_file.write_text("# Complement\n- C1\n", encoding="utf-8")
    pa = BmadPlan(prd_path=tmp_path / "p", architecture_path=tmp_path / "ar", epics_md=a_file)
    pb = BmadPlan(prd_path=tmp_path / "p", architecture_path=tmp_path / "ar", epics_md=b_file)
    out = CompositePlanner(_StubPlanner(pa), _StubPlanner(pb)).plan(_substrate(tmp_path, {}))
    merged = out.epics_md.read_text(encoding="utf-8")
    assert "Remediation" in merged and "Complement" in merged  # union sur disque
```

- [ ] **Step 2:** run `uv run pytest tests/test_planners.py -v` → FAIL (merged file doesn't contain both).

- [ ] **Step 3: modify `CompositePlanner.plan`** in `conductor/planners/complement.py` :
```python
    def plan(self, substrate: Substrate) -> BmadPlan:
        a = self._first.plan(substrate)
        a_text = a.epics_md.read_text(encoding="utf-8") if a.epics_md.exists() else ""
        b = self._second.plan(substrate)  # peut écrire sur le même chemin que a
        b_text = b.epics_md.read_text(encoding="utf-8") if b.epics_md.exists() else ""
        a.epics_md.parent.mkdir(parents=True, exist_ok=True)
        a.epics_md.write_text(f"{a_text}\n{b_text}".strip() + "\n", encoding="utf-8")
        return a.model_copy(update={"stories": [*a.stories, *b.stories]})
```
(`epics_md` reste celui du 1ᵉʳ planner — désormais il contient l'union. Garder les imports/`ComplementPlanner` inchangés.)

- [ ] **Step 4:** run `uv run pytest tests/test_planners.py -v` → PASS (existing + new). Full suite (show output). The existing `test_composite_concatenates_stories` still passes (stories concat unchanged ; epics_md == p1.epics_md, now written with merged content — `e1.md`/`e2.md` in tmp don't exist so both texts empty → file created empty-ish, assertion on epics_md path + stories still holds).

- [ ] **Step 5: commit (show gate output)**
```
uv run ruff check . ; uv run mypy ; uv run pytest -q
git add conductor/planners/complement.py tests/test_planners.py
git commit -m "fix(td2): CompositePlanner fusionne epics.md sur disque (intent=both)"
```

---

## Task 3 : synchro des 3 sections « pilote » dans les 5 playbooks traduits

**Files:** Modify `docs/conductor-run-playbook.{fr,es,de,it,pt}.md`.

Le playbook EN (`docs/conductor-run-playbook.md`) contient 3 sections ajoutées que les traductions n'ont pas : « Real ingestion (pilot) », « Real autonomous sprint (`/bad`, pilot) », « Real BMAD planning (pilot) ». Les ajouter, traduites, à la fin de chacun des 5 fichiers (avant toute éventuelle licence/footer ; sinon en fin de fichier).

- [ ] **Step 1:** lire les 3 sections EN dans `docs/conductor-run-playbook.md` (à partir de « ## Real ingestion (pilot) »).
- [ ] **Step 2:** pour CHAQUE fichier `docs/conductor-run-playbook.{fr,es,de,it,pt}.md`, ajouter en fin de fichier les 3 sections traduites dans la langue du fichier. Conserver les noms techniques/commandes/variables d'env **inchangés** (`CONDUCTOR_USE_CLAUDE_ANALYZER`, `CONDUCTOR_ENABLE_REAL_BAD`, `CONDUCTOR_ENABLE_REAL_BMAD`, `RUN_CLAUDE_INTEGRATION`, `claude -p`, `gh pr list`, `--dangerously-skip-permissions`, HITL 1/2, `AUTO_PR_MERGE=false`). Traduire uniquement la prose. Titres de section traduits (ex. FR « ## Ingestion réelle (pilote) », « ## Sprint autonome réel (`/bad`, pilote) », « ## Planification BMAD réelle (pilote) »).
- [ ] **Step 3: full gate** (show output) `uv run ruff check . ; uv run mypy ; uv run pytest` (doc-only ; tout vert, l'intégration analyzer toujours *skipped*).
- [ ] **Step 4: commit**
```
git add docs/conductor-run-playbook.fr.md docs/conductor-run-playbook.es.md docs/conductor-run-playbook.de.md docs/conductor-run-playbook.it.md docs/conductor-run-playbook.pt.md
git commit -m "docs(td2): synchro des 3 sections pilote dans les 5 playbooks traduits"
```

---

## Définition de fin
- [ ] ruff clean · mypy success · pytest vert (analyzer integration *skipped*)
- [ ] stderr tronqué signalé par « … » ; `epics.md` composite contient l'union sur disque
- [ ] 6 playbooks alignés (EN + 5 traductions) sur les sections pilote
- [ ] Plus aucun suivi mineur tracé en suspens

## Self-Review
**Couverture :** ellipsis stderr (T1) ; epics.md composite (T2) ; playbook multilingue (T3) — les 3 suivis tracés. **Placeholders :** aucun. **Types :** `clip(str,int)->str` ; `CompositePlanner.plan` renvoie toujours un `BmadPlan` (epics_md = 1ᵉʳ planner, contenu fusionné).
