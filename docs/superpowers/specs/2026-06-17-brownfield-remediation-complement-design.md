# Design — Brownfield : remédiation & complément de périmètre

> Date : 2026-06-17 · Statut : **validé en brainstorming, prêt pour le plan d'implémentation**
> Portée : étendre `digitai-saas-forge` pour traiter des **projets existants** — remédiation et/ou
> compléments (fonctionnels et techniques) — en réutilisant la colonne d'orchestration A→E,
> la gouvernance (2 HITL, `auto_pr_merge=false`) et le double gate.

## 1. Objectif & contexte

La forge est aujourd'hui **greenfield** : l'étape B (`scaffold-first`) génère un nouveau repo via
`copier`, et la planification (C) part d'un brief vierge. On veut traiter l'**existant** :

- **Remédiation** — corriger/assainir un code existant (bugs, sécurité, dette, conformité
  tests/CI/design, montée de version).
- **Complément de périmètre** — ajouter du *nouveau* sur une base existante (features = complément
  fonctionnel ; nouvelles briques/infra = complément technique).

**Décision de cadrage : un seul flux brownfield unifié, pas deux pipelines.** Remédiation et
complément ne diffèrent que par *la façon dont le backlog est dérivé* ; ils partagent ~80 % du flux
et **se composent** dans un même sprint (un seul backlog, un seul graphe BAD).

## 2. Insight unificateur — l'onramp généralise le scaffold-first

Le `scaffold-first` n'est qu'un cas particulier d'une notion plus large : **amener un projet au point
où le contrat de la cible (double gate + conventions) est applicable** — la **bretelle (`Onramp`)**.
Selon la **distance à la cible**, la bretelle fait plus ou moins de travail :

| Stratégie | Cas | Rôle |
|---|---|---|
| `Scaffold` | greenfield (forge actuelle) | génère le repo depuis zéro (`scaffold.py`) |
| `None` | **A** — SaaS forge | no-op : vérifie les marqueurs cible, capture la baseline |
| `Adapter` | **C** — compatible cible | normalise : harness CI, `DESIGN.md`, conventions |
| `Builder` | **B** — repo quelconque (**B-standard**) | détecte la stack → résout/synthétise un profil, pose les gates *dans la stack d'origine*, **déclare la dégradation** |

→ **Greenfield et brownfield sont le même flux.** `scaffold-first` = l'onramp `Scaffold`.

**B-standard (décidé)** : « revenir à la cible » = revenir au **standard** de la cible (le contrat
qualité), **dans la stack d'origine** du projet — pas migrer le code vers FastAPI. Chaque nouvelle
stack = **un profil de plus**, le reste est réutilisé. La **B-migration** (réécrire vers la stack
cible) est explicitement **hors périmètre**.

## 3. Architecture — pipeline unifié & deux joints composables

```
A  Cadrage        → mode (greenfield/brownfield), planner(s), onramp (selon distance à la cible)
B  Onramp+Ingest  → normalise le repo · résout le TargetProfile · capture la BASELINE · carte d'archi   [HITL-0 optionnel]
C  Plan (BMAD)    → planner(s) : Remediation et/ou Complement → epics.md                                 ⛔ HITL 1
D  Sprint config  → bad: config (profile-aware), auto_pr_merge=false
E  Superviseur    → /bad · gate code (via profil) · gate design (conditionnel) · gate NON-RÉGRESSION · 3 retries   ⛔ HITL 2
```

Deux **joints enfichables** qui se composent :
- **`Onramp`** (distance à la cible) — *nouveau*, généralise `scaffold.py`.
- **`BmadPlanner`** (intention) — *existe déjà* (protocole Epic 3) ; on ajoute deux implémentations.

**Réutilisé tel quel** : colonne C/D/E (`bmad_bridge`, `sprint_config`, `supervisor`), gouvernance
(`governance` : 2 HITL, `auto_pr_merge` verrouillé), politique de sévérité de `gates/design_gate`,
boucle 3 retries/escalade, protocole `BadRunner`.

## 4. Composants

### 4.1 `TargetProfile` (nouveau) — le contrat d'une stack
```
name            # "fastapi-saas" | "rails" | "node-ts" | …
code_check      # commande du gate code : "uv run pytest" | "bundle exec rspec" | "npm test"
has_ui          # le gate design s'applique-t-il ?
design_md_path  # convention d'emplacement du DESIGN.md (si has_ui)
conventions     # règles que les agents DOIVENT respecter
brick_catalog   # recettes build/buy valides pour la stack (FastAPI = les 11 ; autres = sous-ensemble/vide)
enforceable     # part du contrat réellement applicable (base de la dégradation déclarée)
```
Le profil `fastapi-saas` = la forge actuelle réifiée (`catalog.py` → `brick_catalog`).

### 4.2 Onramps (nouveau module `conductor/onramp/`)
Protocole : `prepare(repo, mission) -> Substrate`, où
`Substrate = (repo_path, profile, baseline, arch_map, design_md_path)`.
- `ScaffoldOnramp` : enveloppe `scaffold.py` (greenfield).
- `NoOnramp` (A) : vérifie marqueurs cible + capture baseline.
- `AdapterOnramp` (C) : normalise vers le profil supporté (harness CI, `DESIGN.md`, conventions).
- `BuilderOnramp` (B) : détecte la stack → résout/synthétise un `TargetProfile` → pose les gates
  dans la stack d'origine → calcule et **déclare `enforceable`**.

### 4.3 Ingestion / carte d'archi (nouveau) — moteur **hybride** (décision)
Analyse le repo → carte d'archi + conventions vérifiées (modules, entrées, tests, nommage).
Derrière un protocole `Analyzer` (effet injecté). **Moteur hybride** :
- **Heuristiques (déterministes)** établissent les *faits durs* — stack, présence/statut tests & CI,
  hôte git, présence d'UI. Ce sont eux qui pilotent `enforceable` (dégradation déclarée) et la
  détection de stack ; testables à 100 % (fonction pure sur un listing de fichiers).
- **Sous-agent** n'*interprète* que par-dessus ces faits — carte d'archi, dette, conventions
  implicites — validé à HITL-0 (anti-hallucination).

Déploiement progressif : **100 % heuristique en BA** (suffisant pour les SaaS forge), **sous-agent
branché en BC/BB**, sans rien casser (même protocole `Analyzer`).

### 4.4 Gate de non-régression — « do no harm » (nouveau, `gates/regression_gate`)
Baseline (statut vert/rouge des checks existants) capturée à l'onramp. À l'étape E, une story est
**bloquée si un check précédemment vert passe au rouge** (→ 3 retries puis escalade). Garde-fou propre
au brownfield. Fonction **pure** : `(baseline_verte, verdict_courant) → bloque?`.

### 4.5 Planners (joint existant, étendu)
- `RemediationPlanner` : *piloté par l'analyse* — compare l'existant au contrat du profil → stories de
  correctif. **Périmètre v1 (décision) : tests/CI + conformité design uniquement** — les deux dimensions
  déjà mesurables sans outillage neuf (la baseline capturée à l'onramp + le gate `design.md` existant).
  Sécurité, dette, montée de version arrivent en incréments ultérieurs (chacun = une dimension d'audit
  de plus, même logique de dégradation déclarée).
- `ComplementPlanner` : *piloté par l'intention* — specs + carte d'archi → stories de feature insérées
  dans l'archi en place.
- **Composables** : backlog mixte possible ; dépendances inter-epics pour « stabiliser avant d'étendre ».

### 4.6 Refactors légers
- `code_gate` lit `code_check` depuis le `TargetProfile` (au lieu de `uv run pytest` en dur).
- `catalog.py` devient le `brick_catalog` du profil `fastapi-saas`.

## 5. Gouvernance & gestion d'erreur

### Points HITL
| Point | Quand | Bloque | Branches |
|---|---|---|---|
| **HITL-0 (carte d'archi)** *optionnel* | après ingestion | la planif tant que carte + `enforceable` non validés | B (forcé), C (léger), A (sautable) |
| **HITL-1 (PRD/archi)** | après C | le dev | les 3 |
| **HITL-2 (revue & merge)** | après E | le merge | les 3 |

HITL-0 = garde-fou anti *garbage-in* (carte fausse ⇒ backlog pollué). Paramétrable.

### Dégradation déclarée (jamais silencieuse)
`BuilderOnramp` calcule `enforceable` et l'affiche à HITL-0 : pas de tests/CI → « gate code n/a » (+
proposition de bootstrap) ; pas d'UI → « gate design n/a » ; hôte non-GitHub → « `/bad` indisponible,
sortie en patchs/branches ». Règle (risque 8 du dossier) : **aucune réduction de périmètre silencieuse**.

### Do-no-harm, fail-fast, idempotence
- `auto_pr_merge=false` verrouillé : rien ne touche `main` sans HITL-2.
- Onramp échoue (stack non détectée, repo inaccessible, baseline rouge d'emblée) → **fail-fast avant
  toute modification** ; baseline rouge signalée (demander si la remédiation cible aussi ces rouges).
- Idempotence : ré-exécution sur un repo déjà onrampé → re-détecte l'état et reprend.
- Isolation : 1 worktree/story (BAD) ; escalade après 3 retries.

## 6. Stratégie de test

Même discipline que la forge : effets externes derrière protocoles injectables, **fakes en test**,
zéro réseau en unitaire ; ruff + mypy strict + pytest ; double gate vert (dogfooding).

- **Unitaires purs/injectables** : `TargetProfile` (+ `enforceable`) ; détection de stack = fonction
  pure sur une liste de fichiers ; onramps via `CommandRunner`/`Analyzer` factices (assertions sur les
  commandes émises) ; `RegressionGate` pur (vert→rouge bloque, rouge→rouge n'aggrave pas, vert→vert
  passe) ; planners via le protocole `BmadPlanner` + effet injecté (composition + ordre inter-epics) ;
  `code_gate` lit la commande du profil ; test que la dégradation est **déclarée** (`has_ui=False` ⇒
  « gate design n/a »).
- **Intégration (fixtures locales, sans réseau)** : trois repos-fixtures dans `tests/fixtures/` via
  `tmp_path` — A (marqueurs forge → `NoOnramp`), C (FastAPI sans `DESIGN.md`/CI → `AdapterOnramp`),
  B (micro-repo d'une autre stack → `BuilderOnramp` + dégradation). `/bad` et BMAD restent derrière
  leurs fakes.
- **CI** : aucun nouveau workflow ; le job `code` couvre le paquet `conductor`, le job `design` reste
  vert sur le `DESIGN.md` de la forge.

## 7. Séquencement de construction (A→C→B)

| Epic | Contenu | Gate de sortie |
|---|---|---|
| **B0 · Fondations** | `TargetProfile` ; extraire le profil `fastapi-saas` (`catalog.py` → `brick_catalog`) ; refactor `code_gate` (lit `code_check`) ; protocole `Onramp` + `Substrate` ; `ScaffoldOnramp` (enveloppe `scaffold.py`) ; `mode` greenfield/brownfield au cadrage/CLI | **Greenfield identique** (zéro régression), abstractions en place, pytest vert |
| **BA · Branche A** | `NoOnramp` (marqueurs + baseline) ; **ingestion heuristique** ; `RegressionGate` ; `RemediationPlanner` (v1 : tests/CI + design) + `ComplementPlanner` ; backlog composable via D/E | Remédier/étendre un SaaS forge de bout en bout (fakes), non-régression effective, 2 HITL intacts |
| **BC · Branche C** | `AdapterOnramp` (normalise) ; HITL-0 léger ; ingestion **hybride** (sous-agent branché) sur un repo externe compatible | Onboarder un repo FastAPI non-forge, le normaliser, dérouler le flux unifié |
| **BB · Branche B** (B-standard) | détection de stack ; `BuilderOnramp` ; **profil `node-ts`** (1ᵉʳ profil non-FastAPI, avec UI → exerce les deux gates) ; dégradation déclarée ; HITL-0 forcé ; hôte GitHub d'abord | Hisser `node-ts` au standard de la cible avec dégradation déclarée |

Chaque epic = branche → PR → double gate → revue (HITL). On peut s'arrêter à n'importe quelle branche
avec de la valeur livrée.

## 8. Hors périmètre (assumé, non silencieux)

- **B-migration** (réécrire vers la stack cible) — écarté ; projets de migration au cas par cas.
- **Profils multiples** au-delà du premier en BB — chacun = epic ultérieur.
- **Hôtes non-GitHub** (GitLab/Bitbucket/Azure DevOps) — déclarés indisponibles tant qu'un adaptateur
  d'hôte n'existe pas.

## 9. Décisions (post-revue)

- **Moteur d'analyse de l'ingestion = hybride** : heuristiques déterministes pour les faits durs
  (stack, tests/CI, hôte, UI → pilotent `enforceable`), sous-agent pour l'interprétation (carte,
  dette), validé à HITL-0. 100 % heuristique en BA, sous-agent branché en BC/BB (§4.3).
- **Première stack de BB = `node-ts`** : stack réellement différente *et* dotée d'une UI → exerce les
  deux gates (code + design). Stacks suivantes = profils ultérieurs.
- **`RemediationPlanner` v1 = tests/CI + conformité design** : les deux dimensions déjà mesurables
  sans outillage neuf (baseline + gate design existant). Sécurité, dette, montée de version =
  incréments ultérieurs (§4.5).

> Décisions intégrées le 2026-06-17 ; aucune question ouverte bloquante restante pour le plan.
