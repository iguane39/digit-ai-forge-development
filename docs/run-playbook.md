# Run Playbook — porte d'entrée unique (tous contextes)

> **Commence ici.** Ce playbook est l'unique point d'entrée pour piloter digit-ai-forge-development, quel
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
| **Externe** | repo existant non conforme — **stack quelconque** (FastAPI incomplet, ou toute autre techno) | brownfield · `AdapterOnramp` (FastAPI incomplet) / `BuilderOnramp` (profil résolu) + HITL-0 | `remediation` / `complement` / `both` |
| **MàJ forge seule** | on veut juste rafraîchir l'outil | — | — (stop après Phase 0) |

Le routage est automatique (`select_onramp` : `detect_stack` + `detect_distance`). Le reste du
lifecycle est **identique** pour les trois configurations de construction.

**Stack quelconque (P-14/P-15).** Un repo externe n'a plus besoin d'être FastAPI ou node-ts : la
forge **résout un `TargetProfile`** par cascade — ① manifeste `.forge/profile.toml` → ② profil curé →
③ inférence heuristique (rôles/commandes détectés) → ④ analyse LLM (opt-in). Un repo full-stack
(ex. backend Flask dans `backend/` + front React dans `frontend/`, sans marqueur racine) est
onrampé via `BuilderOnramp` + HITL-0, là où il était rejeté. Erreur **seulement** si le repo
n'expose aucun signal exploitable → fournir un manifeste (voir ci-dessous).

### Manifeste opposable `.forge/profile.toml` (P-18)

Pour décrire explicitement la stack (prioritaire sur toute détection) :

```toml
name = "flask-react"
has_ui = true

[roles]                 # rôle -> répertoire
backend  = "backend"
frontend = "frontend"

[pkg_managers]          # rôle -> gestionnaire
backend  = "pip"
frontend = "npm"

[commands.backend]      # commandes par rôle ; clé absente = non applicable (skip tracé)
test = "pytest"
[commands.frontend]
test  = "npm test"
build = "npm run build"
```

## Le prompt opérateur générique (copy-paste)

À coller dans une session Claude Code **ouverte dans le dossier de ton projet** (ou un dossier vide
pour un nouveau). **Aucune variable à remplir** : il localise/met à jour la forge, analyse le dossier,
déduit le contexte et te **propose** quoi faire avant d'exécuter.

```
# Mission — Run digit-ai-forge-development (porte d'entrée auto-détectée)

Tu t'exécutes DANS le dossier courant. Tu n'as AUCUNE variable à me faire remplir : tu localises et
mets à jour la forge, tu analyses le dossier courant, tu DÉDUIS le contexte et tu me PROPOSES quoi
faire, puis tu attends ma validation avant toute exécution. La forge est un OUTIL EXTERNE — on ne
l'installe pas dans le projet. Ne viole aucun garde-fou.

## Phase 0 — Forge & préflight (automatique)
1. Localise une copie de la forge `digit-ai-forge-development` :
   - cherche un clone existant (dossier courant, parent/voisin, ou `~/.forge-development/digit-ai-forge-development`) ;
   - trouvé → `git -C <forge> checkout main && git -C <forge> pull --ff-only` ;
   - absent → `git clone https://github.com/iguane39/digit-ai-forge-development ~/.forge-development/digit-ai-forge-development`.
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
- Options de cadrage (facultatives, valables pour les trois cas) : `--charter <chemin/DESIGN.md>`
  (charte client), `--target <slug>` (cible de production), `--style <slug>` (style design),
  `--scope <chemin.json>` (scope SaaS build/buy par brique).
- **Codes de retour** : `0` run complet · `2` **pause HITL** (légitime, la question est imprimée en
  clair — ne la traite JAMAIS comme un échec) · `1` erreur. Sortie machine systématique dans
  `<repo cible>/_forge-output/run-report.json`.
- Flux : onramp → BMAD → **HITL 1** (valide PRD/archi) → sprint `/bad` sous double gate + gate
  spec-compliance + non-régression → **HITL 2** (PR-ready). À chaque HITL : récap, STOP, attends mon « go ».
- Si j'ai choisi le mode unattended : suis `<FORGE>/docs/superpowers/unattended-run-playbook.md`
  (2 gates globaux, politique de merge A/B/C, notifications) — n'invoque AUCUN arrêt de cérémonie
  (ni le gate « relis la spec » du brainstorming) : auto-valide, journalise, enchaîne.

## Défauts des skills (ne pas redemander)
- **Exécution = subagent-driven, TOUJOURS, jamais demandé** : ne pose PAS le choix subagent/inline
  du skill writing-plans (préférence « multi-agents par défaut ») — dans les deux modes.
- **finishing-a-branch** : pas de menu en cours de run (merge local si gate vert ; merge `main` à la revue finale).

## Bascule de mode à tout moment (avec portée)
- En mode **standard**, à CHAQUE arrêt de cérémonie, propose TOUJOURS — en plus des options
  normales — un choix de **portée d'autonomie** :
  1. **Pas à pas** (cette EPIC, puis je redemande) ;
  2. **Unattended — cette EPIC** (enchaîne ses sous-EPICs, re-checkpoint en fin d'EPIC) ;
  3. **Unattended — cette priorité** (toutes les EPICs de la priorité courante, re-checkpoint à la priorité suivante) ;
  4. **Unattended — tout** (jusqu'à la revue finale).
  Journalise la portée choisie ; enchaîne sans cérémonie jusqu'à la frontière, puis re-propose le
  choix (sauf « tout »). Permet d'avancer pas à pas, EPIC par EPIC, ou priorité par priorité.
- Les gates de **gouvernance** (HITL produit, revue finale, double gate, bloqueurs durs) restent
  quel que soit le choix.

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

## Sortie machine & codes de retour

Un run laisse une trace exploitable par un **outil** (CI, script, agent superviseur), en plus du
RUN LOG destiné à l'humain.

**Fichier** — `<repo cible>/_forge-output/run-report.json`, écrit dans les **trois** issues d'un run
(complet, pause HITL, échec) et écrasé à chaque run :

```json
{
  "status": "complete",
  "generated_at": "2026-08-04T12:30:45Z",
  "idea": "un CRM pour artisans",
  "mode": "greenfield",
  "target": "generated/un-crm-pour-artisans",
  "detail": "",
  "sprint": { "results": [], "hitl2_approved": false, "merged": false }
}
```

`status` vaut `complete` · `hitl-pending` · `error` ; `sprint` est le `SprintReport` de l'étape E,
`null` tant qu'elle n'a pas rendu son bilan ; `detail` porte la question HITL ou le message
d'erreur. `merged` reste verrouillé à `false` (décision 07).

**Codes de retour de `conductor run`**

| Code | Sens | Réaction attendue |
|---|---|---|
| `0` | run complet (E a rendu son bilan) | lire `run-report.json`, passer à la revue HITL 2 |
| `2` | **pause HITL** — pas un échec | traiter la question imprimée, approuver, relancer |
| `1` | erreur | lire `detail` (rapport) ou stderr, corriger, relancer |

Un `2` est une pause **par conception** : en automatisation ou en CI, ne le confonds pas avec un
échec (sinon la gouvernance HITL passe pour une panne).

## Options de cadrage du CLI

| Flag | Défaut | Rôle |
|---|---|---|
| `--mode` | `greenfield` | `greenfield` / `brownfield` |
| `--repo` | — | repo cible existant (exigé en brownfield) |
| `--intent` | `remediation` | `remediation` / `complement` / `both` |
| `--charter` | `design/DESIGN.md` | chemin du `DESIGN.md` client (charte de marque) |
| `--target` | `fastapi-saas` | slug de la cible de production |
| `--style` | `digitai` | slug du style design retenu |
| `--scope` | — | fichier JSON du scope SaaS (build/buy par brique) |

Format de `--scope` — une liste de briques, validée par les contrats pydantic ; un fichier
illisible, un JSON malformé ou un schéma non respecté sort en code `1` avec un message explicite
(aucune trace Python) :

```json
[
  { "name": "billing", "decision": "buy" },
  { "name": "analytics", "decision": "skip" }
]
```

`decision` ∈ `build` · `buy` · `skip`. Les briques de **t0** (`multi-tenancy`, `rbac`, `auth-sso`)
restent forcées en `build` quoi que contienne le fichier (décision canonique 05), et un nom hors
catalogue est rejeté tôt.

## Traçabilité des exigences (RV-1)

Convention éprouvée sur le premier produit réel construit via la forge (mode dégradé, 3 tranches
Opus, 581 tests), à présent standardisée : **chaque test cite l'identifiant de l'exigence qu'il
vérifie**, dans sa docstring ou son nom (`E-042`, ex. `test_facture_sans_client_E-042` ou
docstring `"""E-042 — une facture ne peut être créée sans client rattaché."""`).

- **Source des identifiants — arbitrage D-V3 (décidé le 11/08/2026, TF-0008)** : le référentiel
  amont **officiel** est `EXIGENCES.json` (forge-conception) — dans tout run de l'écosystème
  forge, il fait foi et n'a pas de concurrent : la décision n'est plus re-payée à chaque produit.
  BMAD n'est **pas un second amont** : c'est la voie de planification interne de cette forge
  (PRD/épics **dérivés** de l'amont quand l'écosystème est là) et la seule source admise en
  usage **standalone**, hors écosystème (`_bmad-output/planning-artifacts/epics.md`) — usage
  alors consigné comme dégradé au ledger du run.
- **Gate de complétude** : par grep — 100 % des exigences MVP doivent avoir **au moins un test**
  qui les cite. Un identifiant sans test citant fait échouer le gate.

```bash
# Exemple : exigences MVP jamais citées par un test (source EXIGENCES.json)
comm -23 <(jq -r '.[].id' EXIGENCES.json | sort -u) \
         <(grep -rhoE 'E-[0-9]{3}' backend/tests | sort -u)
```

> **Source unique des disciplines de livrable (TF-0007).** Les deux sections ci-dessous —
> auditabilité (RV-2) et disciplines de production (RV-3/RV-4, lois 1-4) — sont la référence
> unique de ce que doit respecter tout produit construit par cette forge. Elles ne se copient
> pas ailleurs : le `CLAUDE.md` du pilot et celui d'un produit y renvoient (lien), ils ne
> dupliquent pas cette prose. Toute évolution des disciplines se fait ici, une seule fois.

## Produit auditable — contrat avec l'auditeur aval (RV-2)

Checklist à appliquer **dès la construction**, pas seulement à l'audit : sur le premier produit
réel, l'auditabilité par `digit-ai-forge-tests` a été découverte trop tard (aller-retour évitable).
C'est un **contrat d'interopérabilité** avec l'auditeur de l'écosystème — cf. digit-ai-forge-tests,
`README.md`, section « Structure attendue du projet cible » (aucune section « Contrat du projet
audité » n'existe littéralement à ce jour côté forge-tests ; à créer si l'écosystème veut un point
d'ancrage dédié) :

- app exposée en **instance module** `app.main.app`, exercée par la suite (pas une fabrique
  recréée à la volée que l'auditeur ne peut pas importer).
- couche SQL **observable** : `Engine` SQLAlchemy (pas un driver bas niveau opaque à l'auditeur).
- contraintes nommées `<type>_<table>_<colonne>` (`ck_*`, `uq_*`).
- déclarations `responses=` / `status_code` **exactes** — ce que l'app émet doit être déclaré,
  pas seulement les cas heureux.
- migrations `-- +migrate Up/Down` exercées **aller/retour/rejeu**.

## Produit livrable — disciplines de production (RV-3, RV-4)

Retours de la production v0.1.0 du premier produit réel construit via la forge : trois défauts
constatés une fois livré — fixtures de démo visibles dans l'UI de production (aucune frontière
prod/démo n'était spécifiée), catalogues et tarifs de modèles IA codés en dur (périmés à la
livraison), CTA repris de la maquette sans être câblés. Généralisés en trois disciplines
vérifiables (rejointes ici par la loi 3, surface implicite, pour couvrir les quatre lois
transverses du pilot), à appliquer **dès la construction** — même logique que le contrat RV-2 :
découvrir ça à l'audit ou en prod coûte un aller-retour évitable.

- **Frontière démo/production.** Tout artefact de démonstration (fixtures, comptes, données
  simulées, endpoints de peuplement) vit derrière un drapeau d'environnement explicite
  (`*_MODE_DEMO` ou équivalent), absent par défaut. L'endpoint de peuplement de la qualif
  (utilisé par l'étape MEP du pilot) relève du **même régime** — ce n'est pas une exception
  silencieuse sous prétexte qu'il sert l'outillage de mise en production.

  Test : le build de production démarré sans le drapeau ne présente **aucune** donnée de
  démonstration — grep des marqueurs de fixtures dans le build + test d'UI vérifiant l'absence.

  ```bash
  # Exemple : marqueurs de démo qui fuiraient dans un build de prod sans le drapeau
  MODE_DEMO=0 <commande_build_prod>
  grep -rE '(fixture|demo|fournisseur-simule|jeu-de-mails)' <dossier_build> \
    && echo "FUITE DÉMO" || echo "OK"
  ```

- **Données volatiles en base.** Catalogues, tarifs, référentiels susceptibles de vieillir ne
  sont **jamais** des constantes du code — table éditable, avec date et source de relevé. Une
  donnée volatile est une donnée, pas du code (loi pilot) : un catalogue codé en dur est
  périmé dès la livraison, pas seulement à terme.

  Test : grep des littéraux suspects (noms de modèles, prix) hors migrations de peuplement
  datées.

  ```bash
  # Exemple : noms de modèles / tarifs en dur hors migration de peuplement
  grep -rnE '"(gpt-|claude-|gemini-)[a-z0-9.-]+"|[0-9]+[.,][0-9]{2}\s*(€|\$|USD|EUR)' \
    --include='*.py' backend/app | grep -v 'migrations/.*_seed_.*\.py'
  ```

- **Zéro affordance inerte.** Tout élément interactif présent dans les gabarits a un effet
  observable testé — câblé — ou n'est pas repris de la maquette. Toute affordance est câblée ou
  n'existe pas (loi pilot) : un bouton qui ne fait rien n'est pas un défaut mineur, c'est une
  promesse rompue envers l'utilisateur.

  Test : le pan `interface` de forge-tests (contrôle statique des affordances inertes, ajouté
  le 05/08/2026) passe à 100 % — chaque élément interactif des gabarits est nommé et jugé câblé.

  ```bash
  uv run --project "<forge-tests>" python -m forge_tests "<repo>" --pans interface --json
  # couverture interface : ratio 1.0 attendu, zéro élément inerte nommé
  ```

  Limites déclarées par le pan (`non_juge`) : « câblé » est une présomption par coïncidence de
  chaîne entre le gabarit et le JS du projet ; les composants `.jsx`/`.tsx`/`.vue`/`.svelte`
  sont hors périmètre du contrôle statique.

- **Surface implicite proposée d'office, jamais omise en silence (loi pilot, loi 3).** L'oubli
  n'existe pas : la surface implicite d'un SaaS (aide, onboarding, compte, favicon, états vides
  guidés) est proposée d'office en amont, à l'étape conception (`enumere-la-surface`), en
  exigences candidates. Le périmètre de cette forge est de ne jamais la faire disparaître
  silencieusement pendant la construction : ce que le PRD/BMAD reçoit en entrée doit ressortir
  soit construit et tracé (EXIGENCES.json / epics), soit explicitement écarté avec motif — jamais
  absent sans trace.

  Test : au HITL 1 (validation PRD/architecture), le PRD statue explicitement, un par un, sur les
  cinq éléments (aide, onboarding, compte, favicon, états vides guidés) — implémenté (tracé) ou
  écarté (motif consigné). Pas de grep fiable ici : la surface implicite est un contenu de PRD,
  pas un marqueur de code — la revue humaine du HITL 1 est le contrôle ; un des cinq éléments sans
  statut consigné bloque l'approbation.

## Quand lire les détails
- **Phases A→E, classification de pièces jointes, sections pilote** → [conductor-run-playbook](conductor-run-playbook.md).
- **Sous-mode autonome (2 gates, merge A/B/C, notifications, reprise)** → [unattended-run-playbook](superpowers/unattended-run-playbook.md).
- **Pilotes manuels des effets réels** → [docs/pilots/](pilots/).
