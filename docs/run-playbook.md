# Run Playbook — porte d'entrée unique (tous contextes)

> **Commence ici.** Ce playbook est l'unique point d'entrée pour piloter digit-ai-saas-forge, quel
> que soit le contexte : nouveau projet, mise à jour de la forge, continuation d'un projet généré,
> ou reprise d'un projet externe. Il **détecte le contexte** et **route** vers le bon flux.
>
> Détails de référence (liés depuis ici, pas à lire d'abord) :
> [conductor-run-playbook](conductor-run-playbook.md) (phases A→E, pièces jointes, sections pilote) ·
> [unattended-run-playbook](superpowers/unattended-run-playbook.md) (sous-mode autonome « lance et reviens »).

## La méthode en un écran

```
[0] Forge & préflight (toujours)  ── met à jour la forge (outil externe) + vérifie l'environnement
        │
[-1] Détecte le contexte ───────────┬── Nouveau (from scratch) ─▶ greenfield · ScaffoldOnramp
        │                           ├── Continuation (projet forge) ─▶ brownfield · NoOnramp · complement
        │                           ├── Externe (repo non conforme) ─▶ brownfield · Adapter/Builder + HITL-0
        │                           └── MàJ forge seule ─▶ stop après [0]
        ▼
[Commun] cadrage ─▶ BMAD ─▶ ⛔HITL 1 ─▶ sprint (double gate + gate spec + non-régression) ─▶ ⛔HITL 2
        │
[Mode] standard gouverné  OU  unattended « lance et reviens » (2 gates globaux, merge A/B/C, notifs)
```

**Principe clé.** La forge est un **outil externe** : on l'exécute depuis sa propre copie, on
n'installe rien dans le projet cible. Les évolutions de la forge s'appliquent **au run** (après
`git pull` de la forge), pas par modification du projet.

## Matrice de contexte (Phase −1)

| Contexte | Signal | Mode / Onramp | Intent |
|---|---|---|---|
| **Nouveau** | pas de repo cible (idée + pièces jointes) | greenfield · `ScaffoldOnramp` (scaffold-first) | — |
| **Continuation** | repo généré par la forge, conforme (pyproject + DESIGN.md + CI) | brownfield · `NoOnramp` (pas de scaffold, baseline) | `complement` |
| **Externe** | repo existant non conforme (un marqueur manque) | brownfield · `AdapterOnramp` (FastAPI incomplet) / `BuilderOnramp` (autre stack) + HITL-0 | `remediation` / `complement` / `both` |
| **MàJ forge seule** | on veut juste rafraîchir l'outil | — | — (stop après Phase 0) |

Le routage est automatique (`select_onramp` : `detect_stack` + `detect_distance`). Le reste du
lifecycle est **identique** pour les trois configurations de construction.

## Le prompt opérateur générique (copy-paste)

À coller dans une session Claude Code **ouverte dans le contexte de travail** (ton projet pour une
continuation/un externe ; un dossier vide ou le projet pilote pour un nouveau). Remplis les variables.

```
# Mission — Run digit-ai-saas-forge (porte d'entrée unique, tous contextes)

Tu pilotes digit-ai-saas-forge. La forge est un OUTIL EXTERNE : on l'exécute depuis sa copie,
on n'installe rien dans le projet cible. Détecte le contexte et route. Ne viole aucun garde-fou.

## Variables
- FORGE_PATH = {{ chemin local de la copie de la forge, ex. ~/dev/digit-ai-saas-forge }}
- INTENTION = {{ ce que tu veux : « nouveau SaaS … » | « ajouter les features … » | « mettre à jour la forge seulement » }}
- CIBLE = {{ chemin du repo existant (continuation/externe) ; vide si nouveau }}

## Phase 0 — Forge & préflight (toujours)
1. Mets à jour la forge : si FORGE_PATH existe → `cd "FORGE_PATH" && git checkout main && git pull --ff-only` ;
   sinon → `git clone https://github.com/iguane39/digit-ai-saas-forge "FORGE_PATH"`. Puis `uv sync`.
   Affiche `git -C "FORGE_PATH" log --oneline -1`.
2. Préflight (fail-fast) : `gh auth status` + `export GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token)` ;
   `claude`, `uv`, `node`/`npx`, `git`, réseau. Renvoie une table OK/KO.
3. Si INTENTION = « mettre à jour la forge seulement » → STOP ici (forge à jour, rien d'autre).

## Phase -1 — Détecte le contexte et route
- CIBLE vide → **Nouveau** (greenfield, ScaffoldOnramp). Si des pièces jointes (specs/contraintes)
  existent, classe-les d'abord (voir conductor-run-playbook, Phase −1) puis scaffold-first.
- CIBLE = repo conforme (pyproject + DESIGN.md + CI présents) → **Continuation** (brownfield,
  NoOnramp, intent=complement). On NE re-scaffolde PAS ; on capture la baseline.
- CIBLE = repo non conforme (un marqueur manque) → **Externe** (brownfield, Adapter/Builder).
  Normalisation + HITL-0 si dégradation déclarée ; choisis l'intent (remediation/complement/both).
- Baseline rouge à l'entrée → SIGNALE-la (declared_degradation) → HITL-0 : me demander si on cible
  aussi ces rouges ou si on « ne fait que ne pas aggraver ».

## Phase commune — cadrage → BMAD → HITL 1 → sprint → HITL 2
1. Propose un MissionConfig (justifié) ; pour continuation/externe, ne planifie QUE le nouveau /
   ce qui doit être remédié. Présente-le, ATTENDS ma validation.
2. Effets réels (run pilote) : `export CONDUCTOR_USE_CLAUDE_ANALYZER=1 CONDUCTOR_ENABLE_REAL_BMAD=1 CONDUCTOR_ENABLE_SPEC_REVIEW=1 CONDUCTOR_ENABLE_REAL_BAD=1`.
3. Lance : `uv run --project "FORGE_PATH" python -m conductor run "INTENTION" [--mode brownfield --repo "CIBLE" --intent <…>]`
   (omets `--mode/--repo/--intent` si Nouveau).
4. Flux : onramp → BMAD planifie → HITL 1 (valide PRD/archi) → sprint /bad sous double gate + gate
   spec-compliance + non-régression → HITL 2 (PR-ready). À CHAQUE HITL : récap, STOP, attends mon « go ».

## Choix du mode (à poser au début)
- **Standard gouverné** : s'arrête à chaque jalon. Détail : conductor-run-playbook.
- **Unattended « lance et reviens »** : 2 gates globaux (pré-vol + revue finale), politique de merge
  A/B/C, notifications aux jalons. Détail : superpowers/unattended-run-playbook.md (Phase −1 = la
  configuration détectée ci-dessus).

## Garde-fous (NON négociables)
- 2 HITL préservés ; `auto_pr_merge=false` ; aucun merge sur `main` sans ma revue.
- Merges locaux par EPIC autorisés SI double gate vert ; merge GitHub = humain, à la fin.
- `/bad` uniquement sur un repo dont `main` est branch-protected ; jamais sur du code sensible sans revue.
- Ne supprime aucun garde-fou ; ne devine pas en silence sur l'irréversible (→ stop).
- Findings du gate spec persistés dans `SPEC_FINDINGS.md` (statut traité/non-traité).

## Sortie attendue
RUN LOG : version de la forge, contexte détecté, baseline (+ rouges signalés), EPICs planifiées /
done / blocked, décisions, PR PR-ready (non mergées), findings spec, coût/temps approximatifs.
```

## Quand lire les détails
- **Phases A→E, classification de pièces jointes, sections pilote** → [conductor-run-playbook](conductor-run-playbook.md).
- **Sous-mode autonome (2 gates, merge A/B/C, notifications, reprise)** → [unattended-run-playbook](superpowers/unattended-run-playbook.md).
- **Pilotes manuels des effets réels** → [docs/pilots/](pilots/).
