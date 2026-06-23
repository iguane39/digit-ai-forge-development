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

À coller dans une session Claude Code **ouverte dans le dossier de ton projet** (ou un dossier vide
pour un nouveau). **Aucune variable à remplir** : il localise/met à jour la forge, analyse le dossier,
déduit le contexte et te **propose** quoi faire avant d'exécuter.

```
# Mission — Run digit-ai-saas-forge (porte d'entrée auto-détectée)

Tu t'exécutes DANS le dossier courant. Tu n'as AUCUNE variable à me faire remplir : tu localises et
mets à jour la forge, tu analyses le dossier courant, tu DÉDUIS le contexte et tu me PROPOSES quoi
faire, puis tu attends ma validation avant toute exécution. La forge est un OUTIL EXTERNE — on ne
l'installe pas dans le projet. Ne viole aucun garde-fou.

## Phase 0 — Forge & préflight (automatique)
1. Localise une copie de la forge `digit-ai-saas-forge` :
   - cherche un clone existant (dossier courant, parent/voisin, ou `~/.saas-forge/digit-ai-saas-forge`) ;
   - trouvé → `git -C <forge> checkout main && git -C <forge> pull --ff-only` ;
   - absent → `git clone https://github.com/iguane39/digit-ai-saas-forge ~/.saas-forge/digit-ai-saas-forge`.
   Puis `uv sync` dans la forge. Annonce le chemin retenu (FORGE) + `git -C <forge> log --oneline -1`.
2. Préflight (fail-fast) : `gh auth status` + `export GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token)` ;
   `claude`, `uv`, `node`/`npx`, `git`, réseau. Renvoie une table OK/KO.

## Phase A — Diagnostic du dossier courant + PROPOSITION (n'exécute rien encore)
Analyse le dossier courant SANS le modifier, pour déduire le contexte :
- vide / aucun marqueur de projet → **Nouveau** (greenfield).
- marqueurs forge conformes (pyproject + DESIGN.md + CI) + artefacts `_bmad-output/` → **Continuation**
  d'un projet déjà démarré avec la méthode.
- repo existant non conforme (un marqueur manque, stack quelconque) → **Externe** (à normaliser).
Lis aussi : l'historique git et le dernier tag `run/<slug>/epic-<n>`, `_bmad-output/planning-artifacts/epics.md`
(stories déjà faites), un éventuel `PLAN.md`, et l'état des gates (baseline verte/rouge).
→ PRÉSENTE-moi alors : (1) le **contexte détecté** + les preuves trouvées ; (2) l'**intention proposée**
  (démarrer un nouveau SaaS / poursuivre avec les prochaines EPICs / remédier les rouges / onboarder un
  externe) ; (3) un **aperçu** de ce qui serait planifié ; (4) le **mode** suggéré (standard gouverné ou
  unattended « lance et reviens »). Si une baseline est rouge → signale-la (HITL-0) avec la question :
  cibler ces rouges, ou seulement « ne pas aggraver » ? **ATTENDS ma validation (ou ma correction).**

## Phase B — Exécution (après ma validation)
- Effets réels (run pilote) : `export CONDUCTOR_USE_CLAUDE_ANALYZER=1 CONDUCTOR_ENABLE_REAL_BMAD=1 CONDUCTOR_ENABLE_SPEC_REVIEW=1 CONDUCTOR_ENABLE_REAL_BAD=1`.
- Lance le conductor depuis la forge, ciblant le dossier courant :
  - **Nouveau** : `uv run --project "<FORGE>" python -m conductor run "<idée validée>"`
  - **Continuation** : `uv run --project "<FORGE>" python -m conductor run "<features validées>" --mode brownfield --repo "$(pwd)" --intent complement`
  - **Externe** : `uv run --project "<FORGE>" python -m conductor run "<objectif validé>" --mode brownfield --repo "$(pwd)" --intent <remediation|complement|both>`
- Flux : onramp → BMAD → **HITL 1** (valide PRD/archi) → sprint `/bad` sous double gate + gate
  spec-compliance + non-régression → **HITL 2** (PR-ready). À chaque HITL : récap, STOP, attends mon « go ».
- Si j'ai choisi le mode unattended : suis `<FORGE>/docs/superpowers/unattended-run-playbook.md`
  (2 gates globaux, politique de merge A/B/C, notifications) — n'invoque AUCUN arrêt de cérémonie
  (ni le gate « relis la spec » du brainstorming) : auto-valide, journalise, enchaîne.

## Défauts des skills (ne pas redemander)
- **Exécution = subagent-driven, TOUJOURS, jamais demandé** : ne pose PAS le choix subagent/inline
  du skill writing-plans (préférence « multi-agents par défaut ») — dans les deux modes.
- **finishing-a-branch** : pas de menu en cours de run (merge local si gate vert ; merge `main` à la revue finale).

## Bascule de mode à tout moment
- En mode **standard**, à CHAQUE arrêt de cérémonie (revue de spec, « démarrer l'EPIC suivante ? »,
  menu de fin de branche), propose TOUJOURS — en plus des options normales —
  **« Passer en mode unattended (ne plus me redemander, enchaîner jusqu'à la revue finale) »**. Si
  je la choisis : journalise la bascule et supprime les arrêts de cérémonie pour la suite. Permet de
  démarrer en gouverné puis de passer en auto, ou de rattraper un mode oublié.
- Les gates de **gouvernance** (HITL produit, revue finale, double gate, bloqueurs durs) restent
  quel que soit le mode.

## Garde-fous (NON négociables)
- 2 HITL préservés ; `auto_pr_merge=false` ; aucun merge sur `main` sans ma revue.
- Merges locaux par EPIC autorisés SI double gate vert ; merge GitHub = humain, à la fin.
- `/bad` uniquement sur un repo dont `main` est branch-protected ; jamais sur du code sensible sans revue.
- Ne supprime aucun garde-fou ; ne devine pas en silence sur l'irréversible (→ stop). Ne modifie rien
  en Phase A (diagnostic en lecture seule).
- Findings du gate spec persistés dans `SPEC_FINDINGS.md` (statut traité/non-traité).

## Sortie attendue
RUN LOG : version de la forge, contexte détecté + preuves, intention validée, baseline (+ rouges
signalés), EPICs planifiées / done / blocked, décisions, PR PR-ready (non mergées), findings spec,
coût/temps approximatifs.
```

## Quand lire les détails
- **Phases A→E, classification de pièces jointes, sections pilote** → [conductor-run-playbook](conductor-run-playbook.md).
- **Sous-mode autonome (2 gates, merge A/B/C, notifications, reprise)** → [unattended-run-playbook](superpowers/unattended-run-playbook.md).
- **Pilotes manuels des effets réels** → [docs/pilots/](pilots/).
