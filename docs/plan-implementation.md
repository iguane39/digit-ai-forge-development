# Plan d'implémentation — `digitai-saas-forge`

> Séquencé **sur le backlog d'amorçage du dossier fondateur** (Epics 0→3) et leurs gates de sortie.
> Modèle d'exécution : « à la BAD » — epic par epic, story → worktree → double gate.
> Références : [`PRD.md`](PRD.md) (FR/NFR/CS), [`architecture.md`](architecture.md) (modules/contrats), [`analyse.md`](analyse.md) (risques).

---

## 0. Pré-requis & dérisquage (avant Epic 1)

> Le dossier ne le prévoit pas explicitement, mais l'analyse (§8.2/8.3) montre que **le format d'entrée de BAD conditionne tout l'Epic 0→3**. Un spike est obligatoire.

| Spike | Objet | Sortie attendue | Bloque |
|---|---|---|---|
| **S-1** ✅ **FAIT** | Lire `stephenleo/bmad-autonomous-development` | **RÉSOLU** : BAD lit le backlog BMAD et construit le graphe lui-même → D devient un adapter de placement/config ; BAD = skill `/bad`. Voir [`spike-S1-bad-format.md`](spike-S1-bad-format.md) | ~~FR-D1/D3, Epic 0 & 3~~ débloqué |
| **S-1b** ✅ **FAIT** | Lire `skills/bad/SKILL.md` | **RÉSOLU** : layout `_bmad-output/{planning,implementation}-artifacts/`, statuts `sprint-status.yaml`, 15 clés `bad:` + défauts. Voir [`spike-S1-bad-format.md`](spike-S1-bad-format.md) §7bis | Epic 3 (3.1/3.2) débloqué |
| **S-2** ✅ **FAIT** | Tester `npx @google/design.md@0.3.0 lint` | **RÉSOLU** : CLI figée, 9 règles, JSON findings. **Piège** : exit code ne bloque que sur `error` → `design_gate.py` doit parser le JSON. Voir [`spike-S2-S3.md`](spike-S2-S3.md) §S-2 | FR-G2, Epic 2 |
| **S-3** ✅ **FAIT** | Greffer `full-stack-fastapi-template` via `copier` | **RÉSOLU** : H3 confirmée (template Copier, pas une dépendance). 11 briques + commandes connues ; multi-tenancy = `tenant_id` row-level. Voir [`spike-S2-S3.md`](spike-S2-S3.md) §S-3 | FR-B1, Epic 1 |

**Arbitrages** (PRD §9) : **TOUS TRANCHÉS** — voir [`decisions-execution.md`](decisions-execution.md). DE-1 dogfooding réel · DE-2 copie locale des styles · DE-3 3 retries · DE-4 « PR-ready » = checklist 6 items · (+ S-1 format BAD, S-3 `tenant_id` row-level). **Plus aucun bloqueur.**

---

## Epic 0 — Bootstrap

**Objectif** : poser le squelette du `conductor`, vendoriser BAD, paramétrer la cible.
**Gate de sortie (dossier)** : **CI verte sur un repo vide.**

| Story | Contenu | Fichiers-cibles | FR/NFR | Dépend de |
|---|---|---|---|---|
| **0.1** | Squelette `conductor/` (modules vides + contrats pydantic du §3) | `conductor/*.py`, `pyproject.toml` (uv) | NFR-1, NFR-8 | — |
| **0.2** | Vendoring du **skill BAD** au tag **`v1.2.0`** (markdown + scripts, pas un package pip) | `vendor/bad/`, note de version | NFR-2, risque 3 | S-1 ✅ |
| **0.3** | `copier.yml` de la cible (questions : tenant ? rbac ? sso ?) | `targets/fastapi-saas/copier.yml` | FR-A2, décision 08 | S-3 |
| **0.4** | CI minimale `double-gate.yml` (squelette, jobs déclarés) | `.github/workflows/double-gate.yml` | FR-G3 | — |
| **0.5** | Test d'intégration maître (placeholder qui casse au breaking change) | `tests/test_e2e_master.py` | NFR-3, risque 8 | 0.1 |
| **0.6** | **Dogfooding (DE-1)** : installer BMAD dans la forge (`npx bmad-method install --modules bmm,tea`) + brief d'amorçage = ce plan | `_bmad/`, `_bmad-output/` | DE-1 | 0.1 |

**Sortie de gate** : `ruff`/`mypy`/`pytest` verts sur le repo nu. Aucune logique métier encore (NFR-1 préservé).

---

## Epic 1 — Scaffold-first SaaS ✅ (branche `epic-1-scaffold-first`)

**Objectif** : générer un socle SaaS réel avec les briques de t0.
**Gate de sortie (dossier)** : **gate code (pytest + e2e).**
**Invariant** : cet epic s'exécute *avant* toute planification d'agent (décision 02).

| Story | Contenu | Fichiers-cibles | FR/NFR | Statut |
|---|---|---|---|---|
| **1.5** | `cadrage.py` (A) : produit `MissionConfig` ; force les briques de t0 ; rejette les briques inconnues | `conductor/cadrage.py` | FR-A1, FR-A2 | ✅ |
| **1.1** | `scaffold.py` (B) : `copier copy` (runner injectable) puis greffe des briques ; échoue dur si une commande casse | `conductor/scaffold.py` | FR-B1, FR-B2 | ✅ |
| **(cat.)** | Catalogue des 11 briques + résolution t0 forcées (spike S-3) | `conductor/catalog.py` | FR-B2/B3 | ✅ |
| **1.2** | Greffe **multi-tenancy** = **`tenant_id` row-level** (`alembic … "add tenancy"`) | `catalog.py` (recette) | FR-B3, §8.7 | ✅ recette |
| **1.3** | Greffe **RBAC** = **Casbin** (`uv add casbin`) | `catalog.py` (recette) | FR-B3 | ✅ recette |
| **1.4** | Greffe **auth/SSO** = **Authlib** (`uv add authlib`) | `catalog.py` (recette) | FR-B3 | ✅ recette |
| **1.6** | `code_gate.py` : délègue au harness (`uv run pytest`), verdict = exit 0 | `conductor/gates/code_gate.py` | FR-G1 | ✅ |

**Sortie de gate** : gate code vert (ruff + mypy strict + pytest 32/32) ; le scaffold force multi-tenant + RBAC + auth/SSO (**CS-3** garanti par `cadrer` + `resolve_bricks`, testé). Les *recettes* de greffe (commandes par brique) sont validées par runner factice ; leur exécution réelle sur un dépôt généré (copier + réseau) relève d'un test d'intégration ultérieur.

---

## Epic 2 — Axe design

**Objectif** : brancher le gate design et rendre l'UI *on-system*.
**Gate de sortie (dossier)** : **gate design (WCAG · refs).**

| Story | Contenu | Fichiers-cibles | FR/NFR | Statut |
|---|---|---|---|---|
| **2.1** | Job `design` **BLOQUANT** (`continue-on-error` retiré) ; invocation robuste `npx -p … designmd lint --format json` | `.github/workflows/double-gate.yml` | FR-G2/G3, risque 7 | ✅ |
| **2.2** | `run_design_gate` : linter injectable + politique de sévérité sur le JSON (⚠ l'exit code seul ne bloque pas — S-2.3) | `conductor/gates/design_gate.py` | FR-G2, FR-G3 | ✅ |
| **2.3** | `DESIGN.md` de référence (charte Digit-AI) — lint réel `errors:0, warnings:0` (3 notices `info`) | `design/DESIGN.md` | FR-G2, NFR-5 | ✅ |
| **2.4** | Style vendorisé **par copie locale** (SKILL.md + provenance, DE-2, sans CLI) | `design/styles/digitai-minimal/` | NFR-2, risque 6 | ✅ |
| **2.5** | `export_tokens` (css-tailwind / dtcg) via runner injectable | `conductor/tokens.py` | décision 08 | ✅ |

**Sortie de gate** : `design.md lint` réel vert sur `design/DESIGN.md` (errors:0, warnings:0) ; le gate est **bloquant** en CI et la politique de sévérité est testée (linter factice). **CS-5** vérifiable.
**Note risque 7** : `designmd spec` est cassé dans le bundle 0.3.0 (`spec.md` manquant) — manifestation concrète de l'« alpha, schéma mouvant ». Usage limité à `lint`/`export` (stables), version épinglée `@0.3.0`.

---

## Epic 3 — Boucle complète ✅ (branche `epic-3-boucle-complete`)

**Objectif** : `conductor run` de bout en bout, avec les 2 HITL câblés.
**Gate de sortie (dossier)** : **double gate + revue humaine.**

| Story | Contenu | Fichiers-cibles | FR/NFR | Statut |
|---|---|---|---|---|
| **3.1** | `bmad_bridge.py` (C) : `BmadPlanner` injectable (`DefaultBmadPlanner` installe `bmm,tea`, recense les artefacts) ; pose **HITL 1** → `HitlPending` si non approuvé | `conductor/bmad_bridge.py` | FR-C1, FR-C2 | ✅ |
| **(gouv.)** | `governance.py` : `HitlPending` + `HumanGate`/`ManualGate` (les 2 points HITL, décision 07) | `conductor/governance.py` | NFR-6 | ✅ |
| **3.2** | `sprint_config.py` (D) : écrit `_bmad-output/.../sprint-status.yaml` + section `bad:` de `_bmad/config.yaml` (`auto_pr_merge=False` verrouillé) ; exige HITL 1 | `conductor/sprint_config.py` | FR-D1/D2/D3 | ✅ |
| **3.3** | `supervisor.py` (E) : `BadRunner` injectable (invoque `/bad`), gate design par story | `conductor/supervisor.py` | FR-E1/E2/E3 | ✅ |
| **3.4** | Remédiation : **3 retries** (`GATE_MAX_RETRIES=3`) → story `blocked` + escalade (DE-3) | `conductor/supervisor.py` | FR-E5 | ✅ |
| **3.5** | **HITL 2** : `SprintReport.merged` verrouillé `False` ; merge seulement si gate humain approuve | `conductor/supervisor.py` | FR-E4, NFR-6 | ✅ |
| **3.6** | CLI `conductor run "<idée>"` câble A→E (pause à HITL 1 par défaut) | `conductor/__main__.py` | FR-CLI1 | ✅ |
| **3.7** | README (promesse, quickstart, décisions, gouvernance) | `README.md` (+ 5 trad.) | doc | ✅ |

**Sortie de gate** : la chaîne A→E est câblée et testée bout-en-bout par fakes ; **les 2 HITL sont effectifs** (pause `HitlPending` à HITL 1, `merged=False` sans HITL 2) ; la remédiation **3 retries** et le double gate par story sont testés. **CS-2/CS-4** vérifiés en logique. L'exécution réelle de BMAD/`/bad` requiert le harness Claude Code (interfaces `DefaultBmadPlanner`/`DefaultBadRunner` en place).

---

## Ordre de dépendances (vue macro)

```
S-1, S-2, S-3 (spikes)
        │
     Epic 0 ───► Epic 1 ───┐
        │                  ├─► Epic 3 ───► (critères de succès CS-1..5)
        └──► Epic 2 ───────┘
```

- **Epic 0** précède tout (squelette + vendoring).
- **Epic 1** et **Epic 2** sont largement **parallélisables** (axe code vs axe design — la symétrie du dossier).
- **Epic 3** est le point de convergence : il câble C/D/E et requiert que les deux gates (1.6, 2.2) existent.

---

## Traçabilité critères de succès → epics

| Critère (PRD §7) | Validé par |
|---|---|
| **CS-1** `conductor run` → PR-ready | Epic 3 (3.6) — *préalable : figer la définition §8.8* |
| **CS-2** Double gate vert | Epic 1 (1.6) + Epic 2 (2.2) + Epic 3 (3.3) |
| **CS-3** Multi-tenant + RBAC + auth/SSO | Epic 1 (1.2–1.4) |
| **CS-4** 2 HITL respectés | Epic 3 (3.1, 3.5) |
| **CS-5** Dépendances épinglées & vendorisées | Epic 0 (0.2) + Epic 2 (2.1, 2.4) |

---

## Garde-fous transverses (rappel, non négociables)

- **Scaffold-first** : Epic 1 *avant* Epic 3 (jamais d'agent avant le squelette).
- **Double gate** bloquant : aucun merge sans les deux jobs verts.
- **2 HITL** : aucune livraison automatique au-delà.
- **Vendoring au tag** + test d'intégration maître (0.5) cassant au breaking change upstream.
- **Maître mince** : refuser tout code qui réimplémente BMAD/BAD/template/design.md.

---

## Delta & questions ouvertes (à arbitrer avant de coder)

Ajouté par rapport au dossier fondateur :
- Un **spike de dérisquage S-1/S-2/S-3** en amont (le dossier ne le prévoit pas mais le risque 3 l'impose).
- Les **contrats d'interface pydantic** entre étapes (`architecture.md` §3).
- La **logique de remédiation de gate** (3.4) — non décrite par le dossier.
- La **parallélisation explicite** des axes code/design (Epics 1 & 2).

Décisions humaines requises avant Epic 1 : ~~format d'entrée BAD~~ ✅ *(résolu par S-1)*, **modèle de multi-tenancy**, **injection design CLI vs copie**, **nombre de retries**, **définition de « PR-ready »**, **confirmation du dogfooding BMAD** (cf. `PRD.md` §9).
