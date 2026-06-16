# Analyse critique — Dossier fondateur « Accélérateur SaaS Digit-AI »

> Source : `input/Digit-AI - SaaS Forge - Accelerateur SaaS - Dossier fondateur repo - 20260616d.html` (daté 16 juin 2026).
> Cette analyse ne paraphrase pas le dossier : elle en extrait les objectifs, valide les partis-pris, et surtout **expose les manques, ambiguïtés et risques non résolus** qui doivent être tranchés avant de coder.

---

## 1. Objectif du système (en une phrase)

Mener **une idée jusqu'à un produit SaaS de production** via une chaîne gouvernée, où une **couche d'orchestration mince** (« framework maître ») séquence et contraint des moteurs tiers existants — sans jamais les réécrire ni les forker.

Le dossier nomme le repo cible : **`digitai-saas-forge`** (nom paramétrable).

---

## 2. Les deux niveaux d'abstraction (clarification fondatrice)

Le dossier opère implicitement sur deux niveaux qu'il faut tenir séparés sous peine de confusion :

| Niveau | Quoi | Statut |
|---|---|---|
| **P1 — méta-produit** | Le repo `digitai-saas-forge` : le framework maître à coder. | **C'est l'objet de ce livrable.** |
| **P2 — produit final** | Un SaaS quelconque généré *par* la forge. | Out of scope direct ; sert de cas de validation. |

**BMAD-METHOD** et **BAD** sont des dépendances orchestrées dans **P2**. Ce livrable applique néanmoins la *méthode* BMAD en **dogfooding** pour planifier **P1** (cf. `PRD.md`).

---

## 3. Architecture cible — la chaîne en 5 étapes

Le framework maître enchaîne cinq étapes (bande 2 du dossier) :

| Étape | Nom | Entrée | Sortie | Garde-fou / réf. |
|---|---|---|---|---|
| **A** | Cadrage cible & style | Idée + contraintes (budget, délai, stack, scope SaaS, charte) | Configuration de mission | risque 5, ressource design 6 |
| **B** | Scaffold-first SaaS | Config de mission | Socle SaaS structuré (squelette + briques) **avant tout agent** | garde-fou n°1 ; risque 5 |
| **C** | Pont BMAD | Socle prêt | PRD, architecture, epics, stories priorisées | **HITL 1** (validation PRD/archi) |
| **D** | Compilateur de sprint | Stories BMAD | Graphe de dépendances + WSJF, format *BAD-ready* | « glue à construire » ; risque 3 |
| **E** | Superviseur BAD + double gate | Graphe | Stories développées, mergées sous double gate | **HITL 2** (revue & merge final) ; risques 3,4,8 |

**Deux principes structurants** :
- **`scaffold-first`** : le squelette de production existe **avant** que les agents codent. Premier garde-fou contre la divergence agent ↔ structure.
- **`double gate`** : aucune story n'est mergée si la **CI code** OU le **lint design** échoue. Symétrie code/design assumée.

---

## 4. Les briques mobilisées (toutes tierces, toutes orchestrées)

| # | Brique | Rôle dans la chaîne | Audit | Vigilance |
|---|---|---|---|---|
| 1 | **BMAD-METHOD** | Couche méthode : brief → PRD → archi → epics → stories | 4,9/5 | Entrée du pipeline |
| 2 | **bmad-autonomous-development (BAD)** | Couche orchestration : coordinateur + sous-agents isolés, 1 worktree git/story, pipeline 7 étapes, boucle epic par epic | 4,4/5 | **Mono-contributeur → vendoriser au tag (risque 3)** |
| 3 | **full-stack-fastapi-template** | Cible de production déterministe (FastAPI + React + PostgreSQL, JWT, pytest/Playwright, CI 14 workflows, Docker). Sa CI = **gate code** | 4,9/5 | Verrou mono-stack (risque 5) |
| 4 | **Toolkit SaaS (interne)** | 11 briques SaaS mappées au template, chacune avec décision *build-vs-buy* + commande de scaffolding | interne | — |
| 5 | **bergside/awesome-design-skills** | 68 styles design agent-natifs (SKILL.md + DESIGN.md, tokens, WCAG 2.2 AA). Contexte design injecté au dev de story (`npx typeui.sh pull <slug>`) | 3,9/5 | **Mono-auteur, aucune release → vendoriser les styles retenus (risque 6)** |
| 6 | **google-labs-code/design.md** | Format DESIGN.md + CLI de lint (contraste WCAG, refs, export tokens css-tailwind/dtcg). = **gate design** | 4,9/5 | **Alpha → adopter tel quel, épingler `@0.3.0` (risque 7)** |

**Principe non négociable** : *le framework maître ne contient aucune de ces logiques — il les séquence et les contraint.*

---

## 5. Les 8 décisions canoniques (contraintes dures, non rediscutables)

| # | Domaine | Décision |
|---|---|---|
| 01 | Orchestration | Maître **mince** au-dessus de BAD — ni fork ni réécriture de BMAD/BAD |
| 02 | Échafaudage | **Scaffold-first non négociable** — squelette FastAPI + briques avant tout agent |
| 03 | Qualité | **Double gate** code + design — aucun merge si l'un échoue |
| 04 | Contexte design | Style **injecté au dev de story** (pull SKILL.md) — l'UI naît *on-system* |
| 05 | Socle SaaS | **Multi-tenancy + RBAC + auth/SSO dès t0** (coûteux à rétro-ajouter) ; billing/jobs/analytics/flags = à la demande, build-vs-buy |
| 06 | Dépendances | **Épinglées & vendorisées** — BAD au tag, `design.md@0.3.0`, styles copiés ; test d'intégration cassant au breaking change upstream |
| 07 | Gouvernance | **Deux points HITL** — validation PRD/archi ; revue & merge final. L'automatisation s'arrête là, volontairement |
| 08 | Adaptabilité | **Cible & charte paramétrables** — FastAPI = une cible parmi d'autres ; charte en DESIGN.md lintable → tokens Tailwind |

---

## 6. Le repo à construire (arborescence cible du dossier)

```
digitai-saas-forge/
├─ README.md                    # vitrine + quickstart
├─ pyproject.toml               # uv · outillage
├─ conductor/                   # le framework maître (couche mince)
│  ├─ cadrage.py                # A · cible + scope SaaS + style
│  ├─ scaffold.py               # B · scaffold-first (template + Toolkit)
│  ├─ bmad_bridge.py            # C · lance la planification BMAD
│  ├─ sprint_compiler.py        # D · stories → graphe BAD-ready
│  ├─ supervisor.py             # E · lance BAD + double gate
│  └─ gates/
│     ├─ code_gate.py           # délègue à la CI du template
│     └─ design_gate.py         # délègue à design.md lint
├─ targets/fastapi-saas/        # cible paramétrable (template + briques)
│  ├─ copier.yml                # questions : tenant ? rbac ? sso ?
│  └─ bricks/                   # multi-tenancy · rbac · auth-sso · billing…
├─ design/
│  ├─ DESIGN.md                 # charte (client / Digit-AI), lintable
│  ├─ styles/                   # styles vendorisés (awesome-design-skills)
│  └─ design.md.lock            # design.md @0.3.0
├─ vendor/bad/                  # bmad-autonomous-development vendorisé (tag)
├─ backlog/seed.md              # epics/stories d'amorçage
├─ .github/workflows/double-gate.yml
└─ docs/                        # les 6 sources + le dossier fondateur
```

---

## 7. Critères de succès du repo (tirés du dossier)

1. `conductor run "<idée>"` → repo SaaS **PR-ready**
2. **Double gate vert** (code + design)
3. **Multi-tenant + RBAC + auth/SSO** présents
4. **2 points HITL** respectés
5. **Dépendances épinglées & vendorisées**

---

## 8. Delta & angles morts — ce que le dossier NE tranche PAS

> C'est ici que se situe la valeur ajoutée de l'analyse. Ces points doivent être arbitrés (cf. section « Questions ouvertes » de chaque livrable).

### 8.1 Contrats d'interface entre étapes A→E — non spécifiés
Le dossier nomme les modules (`cadrage.py`, `scaffold.py`…) mais **ne définit aucun schéma de données** échangé entre eux. *Quelle forme a la « configuration de mission » de A ? Quel format BAD-ready produit D ?* → spécifié dans `architecture.md`, à valider.

### 8.2 Le « compilateur de sprint » (étape D) — la vraie inconnue technique
Le dossier le qualifie lui-même de **« glue à construire »** et le rattache au risque 3. C'est le seul composant **sans upstream** : tout est à écrire. *Comment transformer des stories BMAD (markdown) en graphe de dépendances exécutable par BAD ? Le format d'entrée de BAD est-il documenté/stable ?* → **risque d'exécution majeur**, à dérisquer en priorité (spike).

### 8.3 Format d'entrée réel de BAD — non vérifié
Toute la chaîne D→E suppose que BAD consomme un « graphe de dépendances + WSJF ». **Le dossier ne cite aucune preuve** que c'est le format attendu par `bmad-autonomous-development`. À **vérifier dans le code vendorisé** avant de figer le compilateur.

### 8.4 Mécanisme d'injection du contexte design (« style pull ») — ✅ RÉSOLU (DE-2)
~~CLI vs copie ?~~ Tranché : **copie locale** des styles dans `design/styles/`, lecture en local par `supervisor.py`, **pas de CLI `typeui.sh`** en exécution. Voir [`decisions-execution.md`](decisions-execution.md) DE-2.

### 8.5 Les 11 briques SaaS — ✅ RÉSOLU (spike S-3)
~~Détail absent de cette page.~~ Les 6 sources étant embarquées en base64, la fiche Toolkit (BLOB #4) a été décodée. **Les 11 briques, leurs décisions build/buy et leurs commandes de scaffolding sont désormais connues** — voir [`spike-S2-S3.md`](spike-S2-S3.md) §S-3.2 et [`plan-implementation.md`](plan-implementation.md) Epic 1.

### 8.6 Boucle de feedback des gates — ✅ RÉSOLU (DE-3)
~~Non décrite.~~ Tranché : **3 retries** d'agent puis story `blocked` + escalade HITL. Voir [`decisions-execution.md`](decisions-execution.md) DE-3 (FR-E5).

### 8.7 Multi-tenancy — ✅ RÉSOLU (spike S-3)
~~Modèle non choisi.~~ Le Toolkit (BLOB #4) tranche **`tenant_id` row-level** : table `Organization`, FK `organization_id` sur les modèles, filtrage systématique par dépendance d'injection — **pas** RLS PostgreSQL ni schéma-par-tenant. À implémenter en t0 (décision 05). Voir [`spike-S2-S3.md`](spike-S2-S3.md) §S-3.3.

### 8.8 Définition de « PR-ready » — ✅ RÉSOLU (DE-4)
~~Non mesurable.~~ Tranché : **checklist binaire de 6 items** par story (PR non mergée, double gate vert, corps généré, issue liée, `mergeable` clean, assignée HITL 2). Automatisable via `gh pr view --json`. Voir [`decisions-execution.md`](decisions-execution.md) DE-4.

---

## 9. Risques référencés (bande 5 du dossier) + posture du plan

| Réf. | Risque | Mitigation imposée par le dossier | Traité dans le plan |
|---|---|---|---|
| 3 | Dépendance BAD mono-contributeur | Vendoriser au tag + plan B | Epic 0 (vendoring) + 8.2/8.3 (spike) |
| 4 | Divergence agent ↔ scaffold | Scaffold-first + gate | Epic 1 (ordre imposé) |
| 5 | Verrou mono-stack | Cible paramétrable (`copier.yml`) | Decision 08, Epic 0 |
| 6 | awesome-design-skills fragile | Vendoriser les styles, copie sans CLI | Epic 2 + arbitrage 8.4 |
| 7 | design.md alpha | Épingler `@0.3.0`, CLI stateless | Epic 2 (`design.md.lock`) |
| 8 | Dette cumulée d'upstreams (5-6 deps) | Vendoring de référence + test d'intégration du maître | Transverse, gate de non-régression |

---

## 10. Verdict

Le dossier fondateur est **mûr sur l'intention et l'architecture macro**, mais **immature sur trois points d'exécution** : (a) les contrats d'interface A→E, (b) le compilateur de sprint (étape D, « glue à construire », sans upstream), (c) le format d'entrée réel de BAD. Ces trois points concentrent le risque technique et doivent être **dérisqués par un spike avant l'Epic 1**. Le reste (scaffold, gates, vendoring) est de l'assemblage discipliné de briques connues.

Voir : [`PRD.md`](PRD.md) · [`architecture.md`](architecture.md) · [`plan-implementation.md`](plan-implementation.md).
