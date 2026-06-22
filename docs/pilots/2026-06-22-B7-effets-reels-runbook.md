# Runbook pilote B-7 — Validation des 4 effets agentiques réels

> Procédure **manuelle** (tu l'exécutes ; je t'assiste). Valide que les effets opt-in se déclenchent
> et se comportent comme attendu sur du réel. Aucun run réel n'est automatisé en CI (par conception).

## Prérequis (fail-fast — si un point manque, STOP)
1. `claude` CLI authentifié (`claude` répond).
2. `gh auth status` OK + `export GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token)`.
3. **Repo cible jetable**, dont `main` est **branch-protected** (jamais de code client sensible).
4. Forge à jour : `cd digitai-saas-forge && uv sync`.

## Ordre — du moins au plus risqué (n'inverse pas)
On isole les sources d'échec : lecture seule → docs → lecture PR → mutation du repo.

| # | Effet | Opt-in | Risque | Ce qui doit se passer |
|---|-------|--------|--------|------------------------|
| 1 | **Analyzer** (ingestion) | `CONDUCTOR_USE_CLAUDE_ANALYZER=1` | Lecture seule | La carte d'archi est enrichie (résumé/conventions/dette) ; sinon fallback heuristique sans erreur |
| 2 | **BMAD** (planification) | `CONDUCTOR_ENABLE_REAL_BMAD=1` | Docs only | `_bmad-output/planning-artifacts/epics.md` produit ; **stories parsées** (B-3) non vides ; HITL 1 pause |
| 3 | **Spec-gate** (revue) | `CONDUCTOR_ENABLE_SPEC_REVIEW=1` | Lecture PR | Pour une story, un under-build connu est détecté ; findings dans `SPEC_FINDINGS.md` |
| 4 | **BAD** (sprint) | `CONDUCTOR_ENABLE_REAL_BAD=1` | **Mute le repo** | `/bad` ouvre des PR (jamais mergées) ; observation via `gh pr list` |

## Procédure par effet
Pour chacun : (a) activer l'opt-in, (b) lancer l'étape correspondante, (c) **comparer au fake**
(comportement par défaut sans l'opt-in), (d) noter le résultat ci-dessous.

- **Analyzer** : lancer l'onramp brownfield sur le repo cible avec `CONDUCTOR_USE_CLAUDE_ANALYZER=1`.
  Succès = `arch_map` contient l'interprétation sous-agent (clé `summary`/`conventions`), pas seulement
  les faits heuristiques.
- **BMAD** : `CONDUCTOR_ENABLE_REAL_BMAD=1`. Succès = `epics.md` existe ET `parse_epics` en extrait des
  stories (`id` `X.Y`, `acceptance` non vides). **Lève l'inconnue** « `claude -p` déclenche-t-il BMAD ? ».
- **Spec-gate** : `CONDUCTOR_ENABLE_SPEC_REVIEW=1`. Sur une story dont la PR ne tient pas un critère,
  succès = verdict `under-build` → remédiation, et ligne `non-traité`/`traité` dans `SPEC_FINDINGS.md`.
- **BAD** (en dernier) : `CONDUCTOR_ENABLE_REAL_BAD=1` sur le repo branch-protégé. Succès = PR ouvertes,
  `AUTO_PR_MERGE=false` respecté (rien mergé), HITL 2 pose la décision.

## Tableau de résultats (à remplir)
| Effet | Déclenché ? | Conforme au fake ? | Écart observé | Décision |
|-------|-------------|--------------------|---------------|----------|
| Analyzer | | | | |
| BMAD | | | | |
| Spec-gate | | | | |
| BAD | | | | |

## Sûreté (non négociable)
- Jamais sur du code client sensible. BAD **uniquement** sur un repo dont `main` est branch-protected.
- `--dangerously-skip-permissions` est confiné aux runners réels ; ne pas l'étendre.
- `auto_pr_merge=false` reste verrouillé ; aucun merge automatique attendu.

## Sortie de B-7
- Le tableau rempli + les écarts → alimentent **B-2** (flip défaut prod : ne flipper que ce qui est validé)
  et **B-6** (scoring findings, si volume réel observé).
- Confirme le **format réel de `epics.md`** → ajuste `parse_epics` (B-3) si le format diffère de l'échantillon.
