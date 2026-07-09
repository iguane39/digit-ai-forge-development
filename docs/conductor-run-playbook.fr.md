# Conductor Run — Playbook opérateur

> 🌍 [English](conductor-run-playbook.md) · [Français](conductor-run-playbook.fr.md) · [Español](conductor-run-playbook.es.md) · [Deutsch](conductor-run-playbook.de.md) · [Italiano](conductor-run-playbook.it.md) · [Português](conductor-run-playbook.pt.md)

> ↩ **Porte d'entrée :** commence par [run-playbook.md](run-playbook.md) — il détecte ton contexte (nouveau / continuation / externe / màj forge) et route ici pour le détail A→E.

Ce playbook est le prompt opérateur pour piloter un `conductor run` de bout en bout de la
Digit-AI SaaS Forge **depuis un autre projet Claude Code**, en joignant un dossier de
spécifications/contraintes. Le run est orchestré mais **gouverné** : il s'arrête à deux
points de validation humaine (HITL) par conception et ne merge jamais automatiquement.

## La méthodologie en un écran

```
pièces jointes ─▶ [−1] classification (périmètre vs contraintes)
              ─▶ [0]  préflight (gh/token, uv/node, réseau, clone forge)
              ─▶ [A]  cadrage → MissionConfig (11 briques build/buy, t0 forcées)  ⟲ valider
              ─▶ [B]  scaffold-first (copier + briques, AVANT tout agent)
              ─▶ [C]  planification BMAD (epics.md)                               ⛔ HITL 1
              ─▶ [D]  config sprint (sprint-status.yaml + bad:, auto_pr_merge=false)
              ─▶ [E]  sprint /bad + double gate (code + design) + 3 retries        ⛔ HITL 2
                      → Pull Requests PR-ready (jamais auto-mergées)
```

Garde-fous non négociables : **scaffold-first**, **double gate** (CI code + lint design),
**2 HITL**, **dépendances épinglées/vendorisées** (BAD `@v1.2.0`, `@google/design.md@0.3.0`),
**`auto_pr_merge=false`**.

## Le prompt opérateur (à coller dans l'autre projet Claude Code)

```markdown
# Mission — Piloter un `conductor run` (Digit-AI SaaS Forge) de l'idée au PR-ready

Tu es l'opérateur de la forge `digit-ai-saas-forge` dans CE projet. Tu vas mener un
périmètre produit jusqu'à des Pull Requests PR-ready, en orchestrant la chaîne A→E du
`conductor`. Tu n'es PAS autorisé à contourner ses garde-fous.

## Entrées (fournies en PIÈCE JOINTE)
Un ou plusieurs fichiers sont joints à ce message (specs, contraintes, notes techniques —
formats divers : md, pdf, docx, txt, images…). Ils ne sont PAS pré-triés.

Dépôt de la forge : https://github.com/iguane39/digit-ai-saas-forge
Dépôt cible des PR (où le SaaS sera généré) : {{ org/repo cible, ou "à créer" }}

## Phase −1 — Analyse & classification des pièces jointes
Lis INTÉGRALEMENT chaque pièce jointe, puis sépare le contenu en deux catégories — sans
rien inventer ni rien perdre :
- **PÉRIMÈTRE (le "quoi")** : intention produit, utilisateurs/personas, fonctionnalités,
  user stories, règles métier, écrans/parcours, données, critères de succès produit.
- **CONTRAINTES (le "comment / dans quel cadre")** : pile technique imposée, intégrations,
  sécurité/conformité (RGPD, multi-tenancy, RBAC, SSO…), performance, hébergement,
  budget, délai, charte/marque & design, exigences de tests/CI, dépendances autorisées.
Règles de tri :
- Une exigence ambiguë → classe-la dans les deux et signale-la comme **à arbitrer**.
- Une info ni périmètre ni contrainte → liste-la en **"hors cadre / à ignorer"**.
- Si plusieurs fichiers se contredisent, **remonte le conflit** (ne tranche pas seul).
→ Rends un **tableau de classification** (Source fichier · Extrait · Catégorie · Remarque)
et ATTENDS ma validation de ce tri avant le préflight. C'est la base de tout le reste.

## Cadre NON négociable (garde-fous de la forge)
- **Scaffold-first** : le squelette de production existe avant tout agent (étape B avant C).
- **Double gate** : aucune story livrée si la CI code OU le lint design échoue.
- **2 points HITL** : (1) après la planification BMAD, (2) avant tout merge. À CHAQUE
  HITL tu t'ARRÊTES, tu présentes un résumé décisionnel, et tu ATTENDS ma validation
  explicite. Ces arrêts sont voulus — ce ne sont pas des pannes.
- **`auto_pr_merge=false`** : tu n'auto-mergeras JAMAIS. Tu ne t'auto-approuves pas les HITL.
- **Règle de merge** : l'intégration par EPIC est **automatique & locale** (seulement si le double gate est vert) ; le seul merge **humain** est vers GitHub/`main`, **une fois, à la fin** (HITL 2). Une EPIC bloquée n'est pas mergée.
- **Dépendances épinglées/vendorisées** : BAD `@v1.2.0`, `@google/design.md@0.3.0`.
- "Bout en bout" = orchestré sans intervention manuelle HORS des 2 HITL prévus.

## Phase 0 — Préflight (fail-fast : si un point échoue, ARRÊTE et dis-le)
1. `gh auth status` OK et `GITHUB_PERSONAL_ACCESS_TOKEN` exporté (`export GITHUB_PERSONAL_ACCESS_TOKEN=$(gh auth token)`).
2. `uv`, `node`/`npx`, `git`, accès réseau (npx/copier/bmad) disponibles.
3. Forge récupérable : clone le dépôt et `uv sync` dans `digitai-saas-forge/`.
4. Confirme le dépôt cible des PR et le dossier de destination du SaaS généré.
→ Rends un tableau "préflight OK/KO" avant de continuer.

## Phase A — Cadrage (mapping = le vrai travail)
À partir du PÉRIMÈTRE et des CONTRAINTES validés en Phase −1, PROPOSE un `MissionConfig` :
- `idea` : une phrase de synthèse du produit (PAS les pièces jointes entières).
- `target` : cible (défaut `fastapi-saas`).
- `saas_scope` : pour CHACUNE des 11 briques, une décision `build`/`buy`/`skip` JUSTIFIÉE
  par les pièces jointes. Rappel : `multi-tenancy`, `rbac`, `auth-sso` sont FORCÉES en
  `build` (t0). Relie chaque décision à une contrainte ou un besoin identifié.
- `brand_charter` + `style_slug` : si aucune charte n'est jointe, signale-le et propose
  d'utiliser le `DESIGN.md` par défaut (le gate design tournera dessus) — à valider.
- `budget`/`deadline` et `max_parallel_stories` (plafonne, défaut 2-3) pour borner le coût.
- Liste les exigences du périmètre que tu n'as PAS su mapper (zone grise).
→ PRÉSENTE ce `MissionConfig` et ATTENDS ma validation avant la Phase B (cadrage = checkpoint).

## Phase B — Scaffold-first
Génère le squelette via `copier` + greffe les briques retenues (t0 incluses). Vérifie que
le harness CI (gate code) est en place. N'invoque AUCUN agent avant la fin de B.

**Configuration de départ (routage onramp).** Le « scaffold-first » se généralise en un *onramp*
choisi par `select_onramp` selon la provenance du projet — tous produisent le même substrate, donc
les phases C→E sont identiques pour les trois :
- **From scratch** (`--mode greenfield`) → `ScaffoldOnramp` : génère le squelette (cette section).
- **Continuation** d'un projet généré par la forge (`--mode brownfield`, repo déjà conforme) →
  `NoOnramp` : PAS de scaffold ; capture une baseline qui alimente le gate de non-régression ;
  ne planifie que les EPICs nouvelles.
- **Projet externe** (`--mode brownfield`, repo à normaliser) → `AdapterOnramp` (FastAPI incomplet)
  ou `BuilderOnramp` (**stack quelconque**, profil résolu par cascade — manifeste `.forge/profile.toml`
  → curé → inférence heuristique → LLM opt-in ; P-14/P-15) + HITL-0 si dégradation déclarée ; puis
  `--intent remediation|complement|both`.

## Phase C — Pont BMAD → HITL 1
`npx bmad-method install --modules bmm,tea`, puis produis la planification dans
`_bmad-output/planning-artifacts/epics.md` (PRD, architecture, epics, stories).
→ **HITL 1** : présente un résumé du PRD + architecture + liste d'epics/stories.
ARRÊTE-toi. N'écris la config de sprint qu'après mon "go".

## Phase D — Adapter de sprint
Écris `_bmad-output/implementation-artifacts/sprint-status.yaml` et la section `bad:` de
`_bmad/config.yaml` avec **`auto_pr_merge: false`**, `max_parallel_stories` plafonné, tiers
de modèles. Ne compile PAS de graphe (BAD le construit lui-même).

## Phase E — Superviseur (sprint sous double gate)
Invoque le skill `/bad` (1 worktree/story, pipeline 7 étapes, code gate interne) avec
`AUTO_PR_MERGE=false`. Pour chaque story :
- Gate design : `npx --yes -p @google/design.md@0.3.0 designmd lint --format json` PUIS
  applique la politique de sévérité (NE te fie PAS à l'exit code : un échec WCAG peut sortir
  en `warning` → exit 0). Bloque sur contraste/refs/sections manquantes même en `warning`.
- En cas d'échec d'un gate : jusqu'à **3 retries** de l'agent, sinon story `blocked` + escalade.
→ **HITL 2** : présente les PR PR-ready (checklist : PR ouverte non mergée, double gate vert,
corps généré, issue liée, mergeable=clean, assignée à revue) et les stories `blocked`.
ARRÊTE-toi. NE merge rien.

## Sortie attendue & journal
- Un **journal de run** : classification des pièces jointes, statut par phase, décisions de
  cadrage, stories ready vs blocked, liens des PR, coût/temps approximatifs, zones grises.
- Rappelle où vit le SaaS généré et comment REPRENDRE après chaque HITL.
- Si le périmètre est gros : propose d'abord un **slice MVP / premier epic**, fais-le valider,
  puis étends — plutôt que de lancer tout le sprint d'un coup.

## Interdits (referme les portes)
- Ne traite pas les pièces jointes sans les avoir lues et classées (Phase −1). Ne colle pas
  un document entier comme `idea`. Ne saute pas le préflight. Ne force pas
  `auto_pr_merge=true`. Ne t'auto-approuve aucun HITL. N'ignore aucune contrainte sans la
  signaler en zone grise. Ne forke pas BMAD/BAD/le template/design.md.
```

## Ingestion réelle (pilote)

L'ingestion est heuristique par défaut (déterministe, sans réseau). Pour activer le
**sous-agent analyseur réel** (`claude -p`), définissez `CONDUCTOR_USE_CLAUDE_ANALYZER=1`
(requiert le CLI `claude` authentifié). Le test d'intégration conditionnel documente le
chemin : `RUN_CLAUDE_INTEGRATION=1 uv run pytest tests/test_claude_integration.py`.

## Sprint autonome réel (`/bad`, pilote)

Le sprint BAD autonome est **désactivé par défaut**. Pour l'activer, définissez
`CONDUCTOR_ENABLE_REAL_BAD=1` (requiert `claude` et `gh` authentifiés). Posture de sécurité :
le run s'appuie sur l'isolation native de BAD (un worktree git par story),
`AUTO_PR_MERGE=false` est verrouillé par type (il ne merge jamais automatiquement), et HITL 2
contrôle encore chaque merge. `/bad` s'exécute avec `--dangerously-skip-permissions` et une
isolation réseau assouplie — **ne l'exécutez que sur un dépôt dont la branche `main` est
protégée ; jamais sur du code client sensible sans revue.** Les résultats sont observés via
`gh pr list` (la source de vérité) et mappés aux résultats par story.

## Planification BMAD réelle (pilote)

La planification BMAD est collectée par défaut (`DefaultBmadPlanner` installe BMAD et lit les
artefacts ; HITL 1 se met en pause si absent). Pour activer la **planification BMAD autonome**
via `claude -p`, définissez `CONDUCTOR_ENABLE_REAL_BMAD=1` (requiert `claude` authentifié).
Elle ne produit que des documents de planification sous `_bmad-output/planning-artifacts/` et
est toujours contrôlée par **HITL 1** avant tout développement — aucun code n'est modifié et
rien n'est mergé à ce stade. Avec les trois options activées
(`CONDUCTOR_USE_CLAUDE_ANALYZER`, `CONDUCTOR_ENABLE_REAL_BMAD`, `CONDUCTOR_ENABLE_REAL_BAD`),
la chaîne `A→E` complète s'exécute pour de vrai, en s'arrêtant toujours aux deux HITL.

## Gate de conformité au spec réel (pilote)

Le gate de conformité au spec est **désactivé par défaut** (le superviseur n'applique que le double
gate + la non-régression). Pour activer une **revue de conformité par story** via `claude -p`,
définir `CONDUCTOR_ENABLE_SPEC_REVIEW=1` (nécessite `claude` authentifié). Il confronte les critères
d'acceptation de chaque story au diff de sa PR : un **under-build** (critère non tenu) bloque la
story (elle rejoint la remédiation bornée à 3 retries, puis `blocked`) ; un **over-build**
(comportement au-delà du spec) est consultatif. Tous les findings sont persistés dans
`SPEC_FINDINGS.md` avec un statut `traité`/`non-traité` pour reprise manuelle ultérieure. Aucun
merge n'est affecté ; HITL 2 est inchangé.
