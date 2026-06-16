# Spike S-1 — Format d'entrée réel de BAD

> **Statut : RÉSOLU.** Question levée. Le résultat **invalide l'hypothèse centrale du dossier fondateur sur l'étape D**.
> Sources : audit interne Digit-AI (embarqué dans le dossier fondateur, BLOB #2, daté 15/06/2026) + dépôt réel `stephenleo/bmad-autonomous-development` (README `main`, vérifié).

---

## 1. Question du spike

> *Quel artefact `bmad-autonomous-development` (BAD) attend-il en entrée pour lancer son sprint autonome — un graphe de dépendances pré-construit, ou les stories BMAD brutes ?*

(Cf. [`analyse.md`](analyse.md) §8.2/8.3 et les 3 cas de [`architecture.md`](architecture.md) §5.)

---

## 2. Réponse (tranchée)

> **BAD lit directement le backlog de sprint BMAD et construit lui-même le graphe de dépendances. Il n'attend AUCUN graphe pré-construit.**

Citation du dépôt : *« Builds a dependency graph from your sprint backlog — maps story dependencies, syncs GitHub PR status, and identifies what's ready to work on. »*

→ C'est le **Cas 2** de [`architecture.md`](architecture.md) §5 : *« BAD lit directement les stories et ordonne lui-même → D quasi disparaît. »*

---

## 3. Ce que BAD attend réellement (entrée)

| Élément | Détail | Conséquence pour la forge |
|---|---|---|
| **Artefacts de sprint BMAD** | `epics`, `stories`, et un `sprint-status.yaml` | C'est la **sortie de l'étape C** (pont BMAD), à placer au bon endroit |
| **BMAD installé dans le projet** | `npx bmad-method install --modules bmm,tea` (`bmm` = méthode, `tea` = test architecture/ATDD) | À exécuter pendant le scaffold (B) ou le pont BMAD (C) |
| **Configuration** | section `bad:` dans `_bmad/config.yaml` | Le seul « réglage » que la forge produit pour BAD |
| **Invocation** | commande **`/bad`** (skill Claude Code), overrides runtime possibles | BAD est un **skill, pas une lib Python** |
| **Prérequis** | Git + GitHub CLI (`gh`) authentifié ; `export GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token)` | À provisionner par l'environnement d'exécution |
| **Sandbox (option)** | `enableWeakerNetworkIsolation: true` dans `.claude/settings.json` | À cadrer (sécurité, risque 4/8) |

**Overrides runtime** observés : `/bad MAX_PARALLEL_STORIES=2 AUTO_PR_MERGE=true MODEL_STANDARD=opus MODEL_QUALITY=…`

---

## 4. Pipeline interne de BAD (7 étapes — déjà fourni par BAD)

1. Génération de la spec de story (`MODEL_STANDARD`)
2. Génération du **test d'acceptation qui échoue** (ATDD — `MODEL_STANDARD`)
3. Implémentation du code (`MODEL_STANDARD`)
4. Revue qualité des tests + corrections (`MODEL_STANDARD`)
5. **Revue de code** + corrections (`MODEL_QUALITY`)
6. Commit, push, **PR, monitoring CI** (`MODEL_STANDARD`)
7. Revue du diff de PR + nettoyage (`MODEL_STANDARD`)

Pattern : coordinateur stateless + sous-agents isolés, **1 worktree git par story**, tier de modèle différencié par étape.

---

## 5. Impacts sur l'architecture (corrections à appliquer)

### 5.1 L'étape D (« compilateur de sprint ») s'effondre — **correction majeure**
Le dossier fondateur définissait D comme : *« transforme les stories BMAD en graphe de dépendances exécutable par BAD »*. **C'est redondant avec le cœur de BAD.** Construire un compilateur de graphe **réimplémenterait** la fonction première de BAD → violation directe de la **décision canonique 01** (maître mince, ne pas réécrire BAD).

**Ce qui reste de D** (réduit à un *adapter de placement & configuration*, pas un compilateur) :
- Garantir que la sortie de C atterrit dans la **layout attendue** par BAD (`epics`, `stories`, `sprint-status.yaml`).
- Écrire/fusionner la section `bad:` de `_bmad/config.yaml`.
- Mapper les paramètres de mission vers les overrides runtime (`MAX_PARALLEL_STORIES`, `MODEL_*`).

→ `sprint_compiler.py` devrait être **renommé** (ex. `sprint_config.py`) et **fortement allégé**. Le contrat `SprintGraph` de [`architecture.md`](architecture.md) §3 est **abandonné**.

### 5.2 BAD = skill Claude Code, pas une lib Python — **correction du modèle d'intégration**
`supervisor.py` (E) **n'importe pas** `vendor/bad/` comme module Python. Il **invoque le skill `/bad`** dans un harness Claude Code, avec overrides. Le « vendoring au tag » = vendoriser le **plugin** (markdown + scripts, tag `v1.2.0`), pas un package pip.

### 5.3 BAD fait déjà une partie du gate code — **clarifier la valeur ajoutée de la forge**
Le pipeline de BAD inclut déjà revue de tests (4), revue de code (5) et **monitoring CI** (6). Le `code_gate` du dossier est donc **partiellement redondant** avec BAD. La **vraie valeur ajoutée** du double gate de la forge est :
- le **gate DESIGN** (`design.md lint`) — que BAD **ne fait pas** ;
- l'**enforcement des 2 HITL** que BAD, en mode autonome, court-circuite.

### 5.4 `AUTO_PR_MERGE` doit rester **false** — **garde-fou HITL 2**
BAD peut auto-merger les PR (`AUTO_PR_MERGE=true`). La **décision 07** (HITL 2 : revue & merge final humain) impose que la forge force **`AUTO_PR_MERGE=false`**. C'est un mapping de configuration critique, pas une option.

### 5.5 Sécurité : autonomie au prix de permissions élargies
Le mode autonome requiert `--dangerously-skip-permissions` + isolation réseau assouplie. L'audit Digit-AI **déconseille explicitement** le mode totalement autonome sur un repo client. → cohérent avec la gouvernance HITL ; à cadrer dans la NFR-6 et l'étape E.

---

## 6. Dimensionnement réel de l'étape D

| Avant S-1 (hypothèse dossier) | Après S-1 (réalité) |
|---|---|
| Composant « glue à construire », risque technique central, potentiellement lourd (reverse-engineering d'un format) | **Adapter mince de placement + config YAML.** Risque technique **fortement réduit**. Le vrai travail se déplace vers le **pont BMAD (C)** : produire des artefacts BMAD valides dans la bonne layout. |

**Le risque 3 ne disparaît pas** : il se déplace de « format d'entrée inconnu » vers « dépendance à un skill mono-contributeur, mode autonome à permissions élargies ». La mitigation reste : vendoring au tag `v1.2.0` + test d'intégration de bout en bout.

---

## 7. Questions ouvertes restantes (hors périmètre S-1)

- **Format précis de `sprint-status.yaml`** et arborescence exacte attendue par `/bad` : à confirmer en lisant `skills/bad/SKILL.md` (572 lignes) du dépôt vendorisé (mini-spike S-1b, faible risque).
- **Harness d'invocation** : comment `supervisor.py` déclenche `/bad` de façon programmatique (sous-processus Claude Code headless ?) — à prototyper en Epic 3.
- `merge-config.py` (cité par l'audit, absent du README) : rôle exact dans la fusion de `_bmad/config.yaml` — à vérifier dans le dépôt.

---

## 7bis. Spike S-1b — Arborescence & schémas exacts (RÉSOLU)

> Source : `skills/bad/SKILL.md` du dépôt (lu directement). Précise — et **corrige** — l'arborescence que le dossier fondateur supposait (`backlog/seed.md`).

### Arborescence réellement attendue par `/bad`
```
{project-root}/
├── _bmad/
│   └── config.yaml                              # section bad: (BAD vérifie sa présence)
├── _bmad-output/
│   ├── planning-artifacts/
│   │   └── epics.md                             # epics + sections de stories + champ **GH Issue:**
│   └── implementation-artifacts/
│       └── sprint-status.yaml                   # statut courant de chaque story
└── .worktrees/                                  # WORKTREE_BASE_PATH (défaut) — 1 worktree/story
    └── story-{number}-{slug}/
```

> ⚠ **Écart avec le dossier fondateur** : le dossier prévoyait `backlog/seed.md`. La réalité est `_bmad-output/planning-artifacts/epics.md` + `_bmad-output/implementation-artifacts/sprint-status.yaml`. Le `seed.md` alimente la **planification BMAD (C)**, pas `/bad` directement. L'étape C doit **produire ses sorties dans `_bmad-output/`**.

### `sprint-status.yaml` — statuts (enum)
`backlog` → `ready-for-dev` → `atdd-done` → `in-progress` → `review` → `done`
(les sous-agents écrivent les mises à jour dans la **copie racine du repo**, pas dans le worktree).

### Stories
Vivent comme **sections de `epics.md`** ; chaque story porte un numéro/slug (`6.1` → `story-6-1-slug`) et un champ `**GH Issue:**` (optionnel en mode local). Validées via `validate story {number}-{slug}`.

### Graphe de dépendances (construit par BAD en Phase 0)
- Règle d'ordre **stricte** : *« only pick stories from the lowest incomplete epic. Never pick a story from epic N if any story in epic N-1 is not yet merged. »*
- Phase 0 émet : `ready_stories`, `blocked_stories`, `epic_completion_status`.
- Dépendances encodées dans la **structure des epics + métadonnées de story** (la forge n'a donc rien à compiler).

### Section `bad:` de `_bmad/config.yaml` — clés & défauts réels
| Clé | Défaut | | Clé | Défaut |
|---|---|---|---|---|
| `max_parallel_stories` | **3** | | `stale_timeout_minutes` | 60 |
| `worktree_base_path` | `.worktrees` | | `timer_support` | true |
| `model_standard` | **`sonnet`** | | `monitor_support` | true |
| `model_quality` | **`opus`** | | `api_*_threshold` | 80/95/80 |
| `retro_timer_seconds` | 600 | | `run_ci_locally` | **false** |
| `wait_timer_seconds` | 3600 | | `auto_pr_merge` | **`false`** |
| `context_compaction_threshold` | 80 | | | |

> **Bonne nouvelle gouvernance** : `auto_pr_merge` est déjà `false` par défaut. La forge doit néanmoins **le fixer explicitement** (défensif vs override) pour garantir HITL 2.
> **Mapping de mission** : `model_standard`/`model_quality` (tiers de modèle), `max_parallel_stories` (cadence), `run_ci_locally` (lien avec le gate code) sont les leviers que l'étape D doit exposer.

### Structure interne du skill (à vendoriser, tag `v1.2.0`)
`skills/bad/SKILL.md` + `assets/module-setup.md` + `references/coordinator/*` (timer, monitor, watchdog, gate-pre-continuation, gh-curl-fallback) + `references/subagents/*` (phase0-prompt, phase3-merge/cleanup, phase4-assessment, step6-ci-fallback). → c'est l'ensemble du dossier `skills/bad/` qui part dans `vendor/bad/`.

### Préconditions vérifiées par BAD avant Phase 0
1. Présence d'une section `bad` dans `_bmad/config.yaml` (sinon → `setup`).
2. Déclencheurs : `/bad`, ou langage naturel (« run BAD », « kick off the sprint »…).
3. Canal de notification (Telegram `<channel …>` sinon `terminal`).

---

## 8. Décisions à entériner (HITL)

1. **Abandonner le compilateur de graphe** (D) ; le remplacer par un adapter de placement/config. ✅ recommandé.
2. **Modèle d'intégration = invocation du skill `/bad`** (pas import Python). ✅ recommandé.
3. **Forcer `AUTO_PR_MERGE=false`** pour préserver HITL 2. ✅ non négociable (décision 07).
4. Reporter la valeur ajoutée du gate sur **design + HITL**, le gate code étant largement couvert par BAD.

> Ces corrections sont propagées dans [`architecture.md`](architecture.md), [`PRD.md`](PRD.md) et [`plan-implementation.md`](plan-implementation.md).
