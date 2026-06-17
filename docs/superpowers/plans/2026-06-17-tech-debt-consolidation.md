# Tech-debt — Consolidation post-brownfield — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`). Toujours afficher la sortie des gates.

**Goal:** Résorber les suivis mineurs tracés pendant B0→BB, sans changer le comportement observable (sauf bornage explicite). Greenfield + A/C/B inchangés ; gate vert maintenu.

**Tech Stack:** Python 3.11+, pydantic v2, pytest, ruff, mypy --strict, uv. Branche : `epic-td-consolidation` (depuis `main`).

**Hors périmètre (reste tracé) :** fusion sur disque de `epics.md` pour `CompositePlanner` (`intent=both`) — à traiter quand le chemin « both » sera câblé bout-en-bout dans `run()`.

---

## Task 1 : factoriser `DEFAULT_DESIGN_MD`

**Files:** Create `conductor/onramp/defaults.py`; Modify `conductor/onramp/adapter_onramp.py`, `conductor/onramp/builder_onramp.py`.

- [ ] Créer `conductor/onramp/defaults.py` avec une constante publique `DEFAULT_DESIGN_MD` (le même contenu que les deux `_DEFAULT_DESIGN_MD` actuels, charte minimale importée).
- [ ] Dans `adapter_onramp.py` et `builder_onramp.py` : supprimer la constante locale `_DEFAULT_DESIGN_MD` et importer `from conductor.onramp.defaults import DEFAULT_DESIGN_MD` ; remplacer les usages.
- [ ] Comportement inchangé → les tests existants (`test_adapter_creates_missing_design_md`, `test_builder_creates_missing_design_md`) restent verts.
- [ ] `uv run ruff check . ; uv run mypy ; uv run pytest -q` (montrer la sortie) puis commit `refactor(td): factorise DEFAULT_DESIGN_MD (defaults.py)`.

---

## Task 2 : helper `has_pyproject` (dé-duplication du guard)

**Files:** Modify `conductor/onramp/detect.py`, `conductor/onramp/adapter_onramp.py`, `conductor/onramp/no_onramp.py`.

- [ ] Dans `detect.py`, ajouter `def has_pyproject(repo: Path) -> bool: return (repo / "pyproject.toml").exists()`.
- [ ] Remplacer les 3 occurrences littérales `(repo / "pyproject.toml").exists()` (dans `detect_distance`, `adapter_onramp.prepare`, `no_onramp.prepare`) par `has_pyproject(repo)`. **Conserver les messages d'erreur distincts** de chaque site (les tests matchent "marqueurs"/"BB").
- [ ] Comportement inchangé → tests existants verts.
- [ ] Gates (montrer la sortie) + commit `refactor(td): helper has_pyproject (dé-duplication du guard)`.

---

## Task 3 : borner `HeuristicAnalyzer` (scan top-level)

**Files:** Modify `conductor/onramp/analyzer.py`; Test (append) `tests/test_analyzer.py`.

- [ ] Test (échec d'abord) : créer 250 entrées dans un tmp_path, `analyze` renvoie `len(top_level) <= 200` et `arch["top_level_truncated"] is True` ; cas normal → `top_level_truncated` absent ou False.
- [ ] Implémenter une borne `_MAX_TOP_LEVEL = 200` : `names = sorted(...) ; truncated = len(names) > _MAX_TOP_LEVEL ; top_level = names[:_MAX_TOP_LEVEL]` ; ajouter `"top_level_truncated": truncated` au dict.
- [ ] Gates (montrer la sortie) + commit `feat(td): borne le scan top-level de HeuristicAnalyzer`.

---

## Task 4 : harmoniser le pattern de gate (`is not None`)

**Files:** Modify `conductor/bmad_bridge.py` (HITL-1), `conductor/supervisor.py` (HITL-2).

- [ ] Remplacer `(gate or ManualGate())` / `hitl or ManualGate()` par la forme `X if X is not None else ManualGate()` (cohérent avec `require_hitl0` déjà corrigé) — évite de jeter un gate falsy.
- [ ] Comportement inchangé (aucun gate n'override `__bool__` aujourd'hui) → tests HITL existants verts.
- [ ] Gates (montrer la sortie) + commit `refactor(td): harmonise le pattern de gate (is not None) en HITL-1/HITL-2`.

---

## Définition de fin
- [ ] ruff clean · mypy success · pytest tout vert (sortie visible)
- [ ] Zéro changement de comportement observable (hors bornage explicite de l'analyzer)
- [ ] Suivis tracés restants : `epics.md` composite (intent=both).
