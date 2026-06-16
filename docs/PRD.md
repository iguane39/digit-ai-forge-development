# PRD — `digitai-saas-forge` (framework maître)

> Format BMAD-METHOD, appliqué en **dogfooding** : on planifie la forge avec la méthode que la forge orchestre.
> Niveau : **P1 (méta-produit)** — le repo qui transforme une idée en SaaS de production.
> Sources : dossier fondateur du 16 juin 2026 + [`analyse.md`](analyse.md).

---

## 1. Vision

> **Une idée → un SaaS de production PR-ready, en une commande, sous double gouvernance code & design.**

`digitai-saas-forge` est une **couche d'orchestration mince** qui séquence des moteurs tiers éprouvés (BMAD-METHOD, BAD, full-stack-fastapi-template, design.md) pour mener une intention produit jusqu'à un dépôt SaaS structuré, testé et conforme à une charte — sans réécrire aucun de ces moteurs. Elle encode des partis-pris non négociables (`scaffold-first`, `double gate`, 2 HITL) qui garantissent la qualité par construction.

**Ce que ce n'est pas** : ni un framework applicatif, ni un fork de BMAD/BAD, ni un générateur no-code. C'est un *chef d'orchestre*.

---

## 2. Problème & justification

| Douleur | Conséquence aujourd'hui | Réponse de la forge |
|---|---|---|
| Le passage idée → code est artisanal et non reproductible | Délais, dette, qualité variable | Chaîne déterministe en 5 étapes |
| Les agents autonomes divergent de l'architecture cible | Code jetable, refactors | `scaffold-first` : structure figée avant tout agent |
| La qualité code et la cohérence design sont vérifiées tard (ou jamais) | Régressions, UI hors-charte | `double gate` bloquant à chaque merge |
| Réécrire les outils tiers = dette de maintenance | Équipe happée par l'infra | Maître mince, dépendances vendorisées au tag |

---

## 3. Personas

| Persona | Rôle | Interaction avec la forge |
|---|---|---|
| **Porteur d'idée** (dirigeant / PO / consultant Digit-AI) | Fournit l'intention produit + le brief | Entrée humaine (étape A) |
| **Architecte / mainteneur de la forge** | Maintient `conductor/`, les targets, le vendoring | Code P1, gère les upgrades upstream |
| **Validateur HITL** | Valide PRD/archi (HITL 1), revoit & merge (HITL 2) | Deux points de contrôle |
| **Agents BMAD/BAD** | Planifient et codent P2 de façon autonome | Consommateurs du scaffold + du contexte design |

---

## 4. Périmètre (scope)

### Inclus (v1)
- La couche `conductor/` (étapes A→E) et ses deux gates.
- Une cible paramétrable `targets/fastapi-saas/` (template + briques SaaS) via `copier.yml`.
- L'axe design : `DESIGN.md` lintable + styles vendorisés + gate `design.md@0.3.0`.
- Le vendoring de BAD au tag.
- Le backlog d'amorçage (Epics 0→3) câblé.
- Les 2 points HITL.

### Exclus (v1)
- Cibles non-FastAPI (mais l'architecture doit rester *paramétrable* — décision 08).
- L'usage en production sur un SaaS client réel (P2) au-delà d'une feature de validation.
- Un éventuel forking/amélioration des upstreams (interdit — décision 01).

---

## 5. Exigences fonctionnelles (FR)

> Numérotées pour traçabilité avec les epics du [`plan-implementation.md`](plan-implementation.md).

### Étape A — Cadrage
- **FR-A1** : à partir d'une idée + de contraintes (budget, délai, stack, scope SaaS, charte), produire une **configuration de mission** structurée et validable.
- **FR-A2** : la cible et la charte doivent être **paramétrables** (pas de valeur figée dans le code) — décision 08.

### Étape B — Scaffold-first
- **FR-B1** : générer le squelette de production (`full-stack-fastapi-template`) **avant tout appel d'agent** — décision 02.
- **FR-B2** : greffer les briques SaaS retenues (Toolkit) selon la décision build-vs-buy.
- **FR-B3** : inclure par défaut **multi-tenancy + RBAC + auth/SSO** (t0) — décision 05.

### Étape C — Pont BMAD
- **FR-C1** : lancer la planification BMAD-METHOD sur le scaffold et produire PRD, architecture, epics, stories priorisées.
- **FR-C2** : suspendre la chaîne sur **HITL 1** (validation humaine du PRD & de l'architecture) avant tout dev — décision 07.

### Étape D — Adapter de sprint *(révisé post-spike S-1 — voir [`spike-S1-bad-format.md`](spike-S1-bad-format.md))*
> **Correction** : BAD construit lui-même le graphe de dépendances depuis le backlog. D **ne compile pas** de graphe (cela réimplémenterait BAD).
- **FR-D1** : placer les artefacts BMAD (`epics`, `stories`, `sprint-status.yaml`) dans la **layout attendue par `/bad`**.
- **FR-D2** : écrire/fusionner la section `bad:` de `_bmad/config.yaml` et mapper les paramètres de mission vers les overrides runtime (`MAX_PARALLEL_STORIES`, `MODEL_STANDARD`, `MODEL_QUALITY`).
- **FR-D3** : forcer **`AUTO_PR_MERGE=false`** pour préserver HITL 2 (décision 07).

### Étape E — Superviseur + double gate
- **FR-E1** : lancer le sprint autonome BAD via **invocation du skill `/bad`** (1 worktree git/story ; pipeline 7 étapes fourni par BAD).
- **FR-E2** : injecter le contexte design (style pull) au dev de chaque story — décision 04.
- **FR-E3** : exécuter le **double gate** — aucune story mergée si CI code OU lint design échoue — décision 03.
- **FR-E4** : suspendre sur **HITL 2** (revue & merge final) — décision 07.
- **FR-E5** : sur échec d'un gate, relancer l'agent de story **jusqu'à 3 fois** (`gate_max_retries=3`) ; au-delà → story `blocked` + escalade HITL (DE-3, [`decisions-execution.md`](decisions-execution.md)).

### Gates
- **FR-G1 (code)** : déléguer à la CI du template (ruff, mypy --strict, pytest, Playwright e2e).
- **FR-G2 (design)** : déléguer à `npx @google/design.md@0.3.0 lint design/DESIGN.md` (contraste WCAG 2.2 AA, refs, on-system).
- **FR-G3** : le merge est bloqué si l'un des deux jobs échoue (`double-gate.yml`).

### CLI
- **FR-CLI1** : `conductor run "<idée>"` orchestre A→E de bout en bout.
- **FR-CLI2** : `uv sync` installe l'outillage ; le quickstart README tient en 2 commandes.

---

## 6. Exigences non fonctionnelles (NFR)

| # | Catégorie | Exigence |
|---|---|---|
| **NFR-1** | Minceur | `conductor/` ne réimplémente aucune logique de BMAD/BAD/template/design.md — il les invoque (décision 01). Métrique : aucun module ne dépasse le rôle d'*adapter/orchestrateur*. |
| **NFR-2** | Reproductibilité | Toutes les dépendances épinglées & vendorisées (BAD au tag, `design.md@0.3.0`, styles copiés) — décision 06. |
| **NFR-3** | Résilience upstream | Un **test d'intégration de bout en bout** casse au moindre breaking change upstream (risque 8). |
| **NFR-4** | Qualité code | ruff + mypy strict + pytest + Playwright verts comme definition of done (gate code). |
| **NFR-5** | Accessibilité | UI conforme **WCAG 2.2 AA**, vérifiée par le lint design (gate design). |
| **NFR-6** | Gouvernance | Exactement **2 points HITL**, ni plus ni moins ; aucune action de merge/livraison automatique au-delà (décision 07). |
| **NFR-7** | Adaptabilité | Cible (`copier.yml`) et charte (`DESIGN.md`) substituables sans toucher au `conductor/` (décision 08). |
| **NFR-8** | Portabilité | Stack dev : `uv`, Docker Compose dev/prod, Traefik, HTTPS. |

---

## 7. Critères de succès (mesurables)

| # | Critère | Mesure de validation |
|---|---|---|
| **CS-1** | `conductor run "<idée>"` → repo SaaS **PR-ready** | Checklist binaire de 6 items par story (DE-4, [`decisions-execution.md`](decisions-execution.md)) — automatisable via `gh pr view --json` |
| **CS-2** | Double gate vert | Les 2 jobs `double-gate.yml` passent sur la PR |
| **CS-3** | Socle SaaS présent | Multi-tenancy + RBAC + auth/SSO détectés dans le scaffold généré |
| **CS-4** | Gouvernance respectée | 2 pauses HITL effectives dans une exécution de bout en bout |
| **CS-5** | Dépendances maîtrisées | `vendor/bad/` au tag, `design.md.lock` = `@0.3.0`, `design/styles/` peuplé |

---

## 8. Hypothèses & dépendances

- ~~**H1** : le format d'entrée de BAD…~~ → **CONFIRMÉ par S-1** : BAD (skill `/bad`, tag `v1.2.0`) consomme le backlog BMAD (`epics`/`stories`/`sprint-status.yaml` + `_bmad/config.yaml`) et construit le graphe lui-même. Prérequis : BMAD `bmm,tea` installé, `gh` authentifié, `GITHUB_PERSONAL_ACCESS_TOKEN`.
- **H2** : `design.md@0.3.0` est installable et stable en usage CLI stateless.
- **H3** : `full-stack-fastapi-template` est greffable par `copier` sans réécriture.
- **H4** : les styles `awesome-design-skills` retenus sont copiables localement (vendoring) indépendamment de la CLI `typeui.sh`.
- **H5** *(nouveau)* : `/bad` est invocable de façon programmatique depuis `supervisor.py` (Claude Code headless) — à prototyper en Epic 3.

---

## 9. Questions ouvertes — TOUTES TRANCHÉES

| # | Question | Résolution |
|---|---|---|
| 1 | Dogfooding réel ? | ✅ **DE-1** : dogfooding réel (BMAD tourne sur la forge) |
| 2 | Format d'entrée BAD ? | ✅ **S-1** : BAD construit le graphe lui-même ([`spike-S1-bad-format.md`](spike-S1-bad-format.md)) |
| 3 | Injection design CLI vs copie ? | ✅ **DE-2** : copie locale, pas de CLI |
| 4 | Modèle multi-tenancy ? | ✅ **S-3** : `tenant_id` row-level ([`spike-S2-S3.md`](spike-S2-S3.md)) |
| 5 | Retries de gate ? | ✅ **DE-3** : 3 retries puis escalade HITL |
| 6 | Définition « PR-ready » ? | ✅ **DE-4** : checklist binaire 6 items |

Détail des arbitrages humains : [`decisions-execution.md`](decisions-execution.md). Aucun ne contourne une décision canonique. **→ Plus aucun bloqueur de conception : Epic 0 peut démarrer.**
