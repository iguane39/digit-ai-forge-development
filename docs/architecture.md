# Architecture technique — `conductor/` (framework maître mince)

> Niveau P1. Décrit les modules, leurs **contrats d'interface** (laissés implicites par le dossier — [`analyse.md`](analyse.md) §8.1) et l'intégration des dépendances vendorisées.
> Principe directeur (décision 01 / NFR-1) : **le conductor n'implémente aucune logique métier des moteurs — il les adapte, les invoque et les contraint.**
>
> **⚠ Mise à jour post-spike S-1** ([`spike-S1-bad-format.md`](spike-S1-bad-format.md)) : BAD lit le backlog BMAD et **construit lui-même le graphe de dépendances**. L'étape D n'est donc **pas** un compilateur de graphe (cela réimplémenterait BAD = violation décision 01) mais un **adapter de placement & configuration**. BAD est par ailleurs un **skill Claude Code (`/bad`)**, pas une lib Python. Les sections §2/§3/§4/§5 ci-dessous intègrent cette correction.

---

## 1. Vue d'ensemble

```
                 idée + contraintes (humain)
                          │
   ┌──────────────────────▼───────────────────────────────────────┐
   │  conductor/  (couche mince — orchestration uniquement)         │
   │                                                                │
   │   A cadrage.py ─► B scaffold.py ─► C bmad_bridge.py            │
   │                                        │ (HITL 1)              │
   │                                        ▼                       │
   │                    D sprint_compiler.py ─► E supervisor.py     │
   │                                                 │ (HITL 2)     │
   │                              ┌──────────────────┴────────┐     │
   │                         gates/code_gate.py   gates/design_gate.py │
   └───────────┬───────────────────┬───────────────────┬───────────┘
               │ invoque           │ délègue            │ délègue
        targets/fastapi-saas   template CI         design.md@0.3.0
        + vendor/bad/          (ruff/mypy/pytest/  (lint WCAG/refs/
        + design/styles/        playwright)         tokens)
```

Chaque étape est un **adapter** : il traduit une structure de données interne vers/depuis un moteur tiers. Le flux est un **pipeline typé** : la sortie de chaque étape est l'entrée de la suivante (contrats §3).

---

## 2. Rôle de chaque module

| Module | Étape | Responsabilité | Délègue à | N'implémente PAS |
|---|---|---|---|---|
| `cadrage.py` | A | Valide l'idée + contraintes → `MissionConfig` | (humain + validation) | aucune logique de génération |
| `scaffold.py` | B | Génère le squelette + greffe les briques | `copier` + `targets/fastapi-saas/` | la logique du template |
| `bmad_bridge.py` | C | Lance BMAD-METHOD (`bmm,tea`) sur le scaffold ; collecte PRD/archi/`epics`/`stories` ; pose HITL 1 | BMAD-METHOD | la méthode de planification |
| `sprint_config.py` *(ex-`sprint_compiler.py`)* | D | Place les artefacts BMAD dans la layout attendue par `/bad` (`epics`, `stories`, `sprint-status.yaml`) ; écrit la section `bad:` de `_bmad/config.yaml` ; mappe les overrides runtime | (adapter mince) | **le graphe de dépendances (BAD le construit lui-même)** |
| `supervisor.py` | E | **Invoque le skill `/bad`** epic par epic ; injecte le design ; orchestre le gate design ; pose HITL 2 ; force `AUTO_PR_MERGE=false` | BAD skill (`vendor/bad/`, tag `v1.2.0`) | la boucle d'exécution & le pipeline 7 étapes (fournis par BAD) |
| `gates/code_gate.py` | — | Lit le verdict CI (largement couvert par l'étape 6 de BAD) | CI template / GitHub Actions | les tests eux-mêmes |
| `gates/design_gate.py` | — | Lance `lint --format json`, **parse le JSON et applique une politique de sévérité** (l'exit code seul ne bloque pas — cf. piège S-2.3) — **vraie valeur ajoutée du double gate** | `design.md@0.3.0` | le linter (9 règles) |

> **Correction S-1** : `sprint_compiler.py` n'est PAS « la glue/le compilateur de graphe » que le dossier décrivait. BAD construit le graphe depuis le backlog. D devient un **adapter de placement & config** ; le travail réel se déplace vers C (produire des artefacts BMAD valides). Voir §5 et [`spike-S1-bad-format.md`](spike-S1-bad-format.md).

---

## 3. Contrats d'interface entre étapes (à valider — §8.1 de l'analyse)

> Schémas proposés (Python/pydantic). Ce sont des **propositions de contrat**, à figer en HITL avant l'Epic 1.

### A → B : `MissionConfig`
```python
class BrickChoice(BaseModel):
    name: str                  # "multi-tenancy", "rbac", "auth-sso", "billing"...
    decision: Literal["build", "buy", "skip"]

class MissionConfig(BaseModel):
    idea: str                  # l'intention produit brute
    target: str = "fastapi-saas"      # cible paramétrable (décision 08)
    budget: str | None
    deadline: str | None
    saas_scope: list[BrickChoice]     # multi-tenancy/rbac/auth-sso forcés à t0 (décision 05)
    brand_charter: Path        # chemin vers le DESIGN.md client
    style_slug: str            # style awesome-design-skills retenu
```

### B → C : `ScaffoldResult`
```python
class ScaffoldResult(BaseModel):
    repo_path: Path
    bricks_installed: list[str]
    ci_harness_ready: bool     # le contrat code est en place
    design_md_path: Path       # DESIGN.md greffé, lintable
```

### C → D : `BmadPlan`
```python
class Story(BaseModel):
    id: str
    epic: str
    title: str
    acceptance: list[str]
    depends_on: list[str] = []   # dépendances déclarées par BMAD si dispo
    wsjf: float | None = None

class BmadPlan(BaseModel):
    prd_path: Path
    architecture_path: Path
    stories: list[Story]
    hitl1_approved: bool         # FR-C2 : porte HITL 1
```

### D → E : ~~`SprintGraph`~~ → `BadSprintLayout` (**révisé post-S-1**)
> Le contrat `SprintGraph` est **abandonné** : BAD ne consomme pas de graphe, il le construit lui-même depuis le backlog. D ne produit donc pas un graphe mais s'assure que le backlog est **bien placé et configuré**.
> Chemins et défauts **confirmés par S-1b** ([`spike-S1-bad-format.md`](spike-S1-bad-format.md) §7bis).
```python
class BadConfig(BaseModel):
    # section bad: de _bmad/config.yaml — défauts réels de BAD v1.2.0
    max_parallel_stories: int = 3
    worktree_base_path: str = ".worktrees"
    model_standard: str = "sonnet"
    model_quality: str = "opus"
    run_ci_locally: bool = False
    auto_pr_merge: bool = False        # FORCÉ false → préserve HITL 2 (décision 07)
    # (+ timers/watchdog/seuils API : retro_timer_seconds=600, stale_timeout_minutes=60, …)

class BadSprintLayout(BaseModel):
    project_root: Path                 # où /bad sera invoqué
    epics_md: Path                     # _bmad-output/planning-artifacts/epics.md (stories = sections)
    sprint_status_yaml: Path           # _bmad-output/implementation-artifacts/sprint-status.yaml
    bmad_config_yaml: Path             # _bmad/config.yaml AVEC section bad: (précondition BAD)
    config: BadConfig
    # ⚠ écart dossier : PAS de backlog/seed.md ici — seed.md alimente la planif BMAD (C),
    #    qui DOIT écrire ses sorties dans _bmad-output/. BAD construit le graphe lui-même.
```
Statuts de story (`sprint-status.yaml`) : `backlog → ready-for-dev → atdd-done → in-progress → review → done`. Règle d'ordre imposée par BAD : *epic le plus bas non terminé d'abord ; jamais une story d'epic N si epic N-1 n'est pas mergé*.

### E → gates : `GateVerdict`
```python
class GateVerdict(BaseModel):
    gate: Literal["code", "design"]
    passed: bool
    findings: list[dict]         # design.md émet du JSON lisible par agent
    log_ref: str
```

---

## 4. Intégration des dépendances vendorisées (NFR-2 / décision 06)

| Dépendance | Emplacement | Épinglage | Mode d'invocation |
|---|---|---|---|
| **BAD** | `vendor/bad/` | **tag `v1.2.0`**, plugin/skill vendorisé (markdown + scripts) | **invocation du skill `/bad`** (harness Claude Code) depuis `supervisor.py` — *pas* un import Python. Prérequis : `gh` authentifié + `GITHUB_PERSONAL_ACCESS_TOKEN` |
| **design.md** | `design.md.lock` | `@0.3.0` (npm) | `npx @google/design.md@0.3.0 lint …` (CLI stateless) depuis `design_gate.py` |
| **awesome-design-skills** | `design/styles/` | styles **copiés** (pas de CLI) | lecture locale par `supervisor.py` au dev de story (arbitrage §8.4) |
| **full-stack-fastapi-template** | `targets/fastapi-saas/` | version figée dans `copier.yml` | `copier copy` depuis `scaffold.py` |
| **BMAD-METHOD** | (invoqué) | version épinglée | `bmad_bridge.py` |

**Garde-fou anti-dette (NFR-3 / risque 8)** : un test d'intégration `tests/test_e2e_master.py` exécute `conductor run` sur une idée triviale et **échoue au moindre breaking change** d'un upstream. C'est le filet de sécurité de la décision 06.

---

## 5. L'étape D — résolue par le spike S-1

> **Spike S-1 exécuté → cas 2 confirmé** ([`spike-S1-bad-format.md`](spike-S1-bad-format.md)) : *BAD lit le backlog BMAD et construit le graphe de dépendances lui-même.*

Conséquences :
1. **Pas de compilateur de graphe.** Construire un DAG côté forge réimplémenterait BAD → violation décision 01. Le contrat `SprintGraph` est abandonné (§3).
2. **D = adapter de placement & config** (`sprint_config.py`) : artefacts BMAD dans la layout attendue + `_bmad/config.yaml` (section `bad:`) + overrides runtime. Risque technique **fortement réduit**.
3. **Le travail réel se déplace vers C** : produire des artefacts BMAD (`epics`, `stories`, `sprint-status.yaml`) valides et complets. C'est là que se concentre désormais l'effort.
4. **Test de contrat** : vérifier que `/bad` démarre et reconnaît le backlog produit (test d'intégration, pas un test de format de graphe).

---

## 6. Les deux gates (décision 03 / `double-gate.yml`)

```yaml
name: double-gate
on: [pull_request]
jobs:
  code:     # gate code — harness du template (FR-G1)
    steps: [ruff, mypy --strict, pytest, playwright e2e]
  design:   # gate design — adopté tel quel, épinglé (FR-G2)
    steps:
      # ⚠ NE PAS se fier à l'exit code (warnings → exit 0, cf. S-2.3) :
      - run: npx @google/design.md@0.3.0 lint --format json design/DESIGN.md > findings.json
      - run: python -m conductor.gates.design_gate findings.json   # politique de sévérité forge
  # merge bloqué si l'un des deux jobs échoue (FR-G3)
```

- Les gates sont **parallèles** et **indépendants** : symétrie code/design.
- `code_gate.py` / `design_gate.py` sont des **adapters de lecture de verdict** côté `conductor` (pour la boucle E locale) ; la CI GitHub est l'autorité de blocage du merge.
- **Remédiation (FR-E5, §8.6)** : sur échec, `supervisor.py` relance l'agent de story (N retries bornés, paramétrable) ; au-delà, escalade en HITL.
- **Note S-1 — répartition de la valeur** : le pipeline interne de BAD couvre déjà revue de tests (étape 4), revue de code (5) et **monitoring CI** (6). Le `code_gate` de la forge est donc en grande partie **redondant avec BAD** — il sert de *filet de confirmation*. La **valeur ajoutée nette du double gate est le gate DESIGN** (que BAD ne fait pas) **+ l'enforcement des HITL**. `supervisor.py` doit invoquer `/bad` avec **`AUTO_PR_MERGE=false`** pour que la PR s'arrête à HITL 2 (décision 07).

---

## 7. Points de gouvernance humaine (décision 07 / NFR-6)

| Porte | Position | Bloque quoi | Implémenté dans |
|---|---|---|---|
| **HITL 1** | Après C (planification), avant D/E | Le démarrage du dev tant que PRD/archi non validés | `bmad_bridge.py` (flag `hitl1_approved`) |
| **HITL 2** | Après E (double gate vert), avant merge | La livraison/merge final | `supervisor.py` + branch protection |

Aucune automatisation au-delà de ces deux portes : c'est un invariant, pas une limitation technique.

---

## 8. Principes d'architecture (invariants)

1. **Minceur** : tout module qui dépasse le rôle d'adapter/orchestrateur viole la décision 01.
2. **Scaffold-first** : `scaffold.py` (B) s'exécute toujours avant `bmad_bridge.py` (C) — l'ordre est structurel, pas configurable (décision 02).
3. **Pipeline typé** : chaque étape consomme et produit un contrat pydantic versionné (§3).
4. **Substituabilité** : changer de cible = changer `targets/` + `copier.yml`, jamais `conductor/` (décision 08 / NFR-7).
5. **Stateless gates** : les gates ne portent pas d'état entre exécutions (mitigation design.md alpha, risque 7).

---

## 9. Questions ouvertes (techniques)

- ~~Format d'entrée BAD~~ — **RÉSOLU par S-1** ([`spike-S1-bad-format.md`](spike-S1-bad-format.md)).
- Format exact de `sprint-status.yaml` + arborescence attendue par `/bad` — mini-spike S-1b (lire `skills/bad/SKILL.md`, faible risque).
- Mécanisme d'invocation programmatique de `/bad` par `supervisor.py` (Claude Code headless ?) — à prototyper en Epic 3.
- Mécanisme exact d'injection du style (CLI vs copie locale) — §8.4.
- Modèle de multi-tenancy (RLS vs schéma/tenant) — §8.7, structurant pour `targets/bricks/multi-tenancy`.
- Frontière précise entre verdict local (`gates/*.py`) et autorité CI GitHub.

Voir aussi : [`PRD.md`](PRD.md) · [`plan-implementation.md`](plan-implementation.md).
