# Mode unattended gouverné — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Toujours afficher la sortie des vérifications.

**Goal:** Produire les 3 artefacts de process du « mode unattended gouverné » (procédure + 2 templates) qui permettent un run multi-EPIC « lance et reviens », sans aucun code conductor.

**Architecture:** Livrable 100 % documentaire sous `docs/superpowers/`. On écrit d'abord les deux templates (référencés par le playbook), puis le playbook (lifecycle + politiques + prompt orchestrateur + gabarit `RUN_LOG.md`), puis un contrôle de cohérence transversal. Pas de TDD : chaque tâche est vérifiée par présence des ancres requises (ripgrep) + relecture par rapport à la spec.

**Tech Stack:** Markdown uniquement. Vérifications via `rg` (ripgrep). Spec source : [docs/superpowers/specs/2026-06-18-unattended-run-mode-design.md](../specs/2026-06-18-unattended-run-mode-design.md).

**Note git :** la racine `c:\dev\Digit-AI - Saas Forge` n'est pas un dépôt git (le repo est sous `digitai-saas-forge/`). Les étapes « commit » sont donc **optionnelles** : ne committer que si ces fichiers sont suivis par git ; sinon, sauter l'étape commit (le fichier sur disque suffit).

---

## Task 1 : template `PLAN.md` (tracker maître des EPICs)

**Files:**
- Create: `docs/superpowers/templates/PLAN.md`

- [ ] **Step 1: créer le dossier templates si absent**

Run: `mkdir -p "docs/superpowers/templates"`
Expected: aucune sortie (dossier prêt).

- [ ] **Step 2: écrire `docs/superpowers/templates/PLAN.md`**

Contenu exact :
```markdown
<!-- TEMPLATE — copier en PLAN.md à la racine du run, remplacer <…>. Source de vérité + checkpoint de reprise. -->
# Run <slug> — Plan maître
> budget: <temps/coût max> · max_parallel: <n> · politique merge: <A|B|C> · branche: run/<slug>
> Statuts possibles : `todo` · `in-progress` · `done` · `blocked: <raison>`

| # | EPIC | dépend de | statut | gate | tests | durée | tag |
|---|------|-----------|--------|------|-------|-------|-----|
| 1 | <titre EPIC 1> | — | todo | — | — | — | — |
| 2 | <titre EPIC 2> | 1 | todo | — | — | — | — |
| 3 | <titre EPIC 3> | — | todo | — | — | — | — |

## Règles de mise à jour (l'orchestrateur les applique)
- Après chaque EPIC : mettre à jour `statut`, `gate` (✅/❌), `tests` (nb), `durée`, `tag`.
- `tag` = `run/<slug>/epic-<n>` posé UNIQUEMENT si double gate + non-régression verts.
- Une EPIC `blocked: <raison>` n'est ni mergée ni taguée ; elle est surfacée à la revue finale.
- Reprise : redémarrer à la 1ʳᵉ EPIC non `done` ; ne pas retaguer le `done`.
- Ce fichier est tenu à jour de façon ASYNCHRONE (jamais de message bloquant pour informer).
```

- [ ] **Step 3: vérifier les ancres requises**

Run: `rg -n "max_parallel|politique merge|blocked: <raison>|run/<slug>/epic-<n>|1ʳᵉ EPIC non .done" "docs/superpowers/templates/PLAN.md"`
Expected: au moins 5 lignes correspondantes (budget/max_parallel, politique merge, statut blocked, schéma de tag, règle de reprise).

- [ ] **Step 4: commit (optionnel — voir Note git)**

```
git add docs/superpowers/templates/PLAN.md
git commit -m "docs(unattended): template PLAN.md (tracker maître des EPICs)"
```

---

## Task 2 : template `DECISIONS.md` (registre de décisions)

**Files:**
- Create: `docs/superpowers/templates/DECISIONS.md`

- [ ] **Step 1: écrire `docs/superpowers/templates/DECISIONS.md`**

Contenu exact :
```markdown
<!-- TEMPLATE — copier en DECISIONS.md à la racine du run. Figé au GATE 1, enrichi en run. -->
# Décisions — Run <slug>

## Pré-vol (figé au GATE 1, avant la 1ʳᵉ EPIC)
> Toutes les décisions anticipables extraites du scan de TOUTES les EPICs, présentées en UN
> questionnaire groupé. Chaque ligne a un défaut recommandé ; l'utilisateur peut « tout accepter ».

| Choix | Options | Défaut recommandé | Réponse retenue |
|-------|---------|-------------------|-----------------|
| Politique de merge (GATE 2) | A / B / C | A (auto-intégration) | <…> |
| <choix fonctionnel/technique 2> | <…> | <…> | <…> |
| <choix fonctionnel/technique 3> | <…> | <…> | <…> |

## Défauts appliqués en run (décisions émergentes non bloquantes — horodatés)
> Politique défaut-sinon-stop : appliquer le défaut raisonnable, le consigner ici, continuer.
- [HH:MM] EPIC <n> — <décision> : défaut « <x> » appliqué — <justification>.

## Questions ouvertes / bloquantes (décisions irréversibles → arrêt)
> Irréversible / destructive / sécurité-conformité / hors-mandat / contournement de garde-fou.
- EPIC <n> — <question> → EPIC marquée `blocked`, en attente de la revue finale.
```

- [ ] **Step 2: vérifier les ancres requises**

Run: `rg -n "Pré-vol|tout accepter|Politique de merge|Défauts appliqués en run|Questions ouvertes|blocked" "docs/superpowers/templates/DECISIONS.md"`
Expected: au moins 6 lignes (les 3 sections + le défaut « tout accepter » + politique de merge + statut blocked).

- [ ] **Step 3: commit (optionnel — voir Note git)**

```
git add docs/superpowers/templates/DECISIONS.md
git commit -m "docs(unattended): template DECISIONS.md (pré-vol + défauts + questions ouvertes)"
```

---

## Task 3 : playbook `unattended-run-playbook.md`

**Files:**
- Create: `docs/superpowers/unattended-run-playbook.md`

- [ ] **Step 1: écrire `docs/superpowers/unattended-run-playbook.md`**

Contenu exact :
```markdown
# Unattended Run — Playbook gouverné (workflow EPIC)

> Procédure pour piloter un run multi-EPIC « lance et reviens » de la forge/des projets, via le
> workflow EPIC superpowers (brainstorm → spec → plan → exécution subagent-driven → revue → merge
> → récap). Objectif : **débit non supervisé maximal SANS affaiblir la gouvernance**.
> Templates associés : `templates/PLAN.md`, `templates/DECISIONS.md`.

## Principe directeur — frontière cérémonie / gouvernance
On supprime la cérémonie, on garde la gouvernance. Listes indépendantes (pas de correspondance
ligne à ligne).

| PRÉSERVÉ (jamais contourné) | SUPPRIMÉ / batché |
|---|---|
| Double gate (ruff/mypy/pytest + design WCAG) | Validation de design par EPIC |
| Non-régression | « Relis la spec » par EPIC |
| 2 HITL produit (uniquement si `conductor run`) | « Démarrer l'EPIC suivante ? » |
| Revue humaine avant merge vers `main`/cible partagée | Choix du mode d'exécution |
| `auto_pr_merge=false` | Messages d'avancement bloquants |

**Distinction de merge.** Merge LOCAL par EPIC (branche de run, gardé par double gate +
non-régression) = mécanisme d'enchaînement réversible → **autonome**. Merge FINAL vers `main`
(push/PR, irréversible) → **humain (revue finale)**. « Merge automatique » signifie TOUJOURS local.

## Cycle de vie — 2 gates humains

### Phase 0 — Plan & pré-vol  ⛔ GATE 1 (humain, unique)
1. Macro-brainstorm → liste des EPICs → instancier `PLAN.md` (tous `todo`, déps, ordre, budget,
   `max_parallel`, branche `run/<slug>`).
2. Scanner TOUTES les EPICs → extraire les décisions fonctionnelles/techniques anticipables.
3. Poser UN questionnaire groupé (chaque choix = recommandation par défaut + « tout accepter »),
   y compris le **choix de la politique de merge GATE 2** (ci-dessous). Consigner dans `DECISIONS.md`.
4. Estimer budget/temps ; si gros périmètre, proposer un **slice MVP d'abord** puis extension.
5. Obtenir le consentement unique « GO unattended ». Créer la branche `run/<slug>`.

### Phase 1 — Boucle autonome  (aucun arrêt humain hors politiques ci-dessous)
Pour chaque EPIC (ordre des déps ; EPICs indépendantes en parallèle dans la limite `max_parallel`) :
brainstorm → spec (auto-validée, consulte `DECISIONS.md`) → plan → exécution subagent-driven →
double gate + non-régression → merge LOCAL si vert (+ tag) → maj `PLAN.md` + `RUN_LOG.md` →
récap+KPIs (non bloquant) → démarrage automatique de l'EPIC suivante.

### Phase 2 — Revue finale  ⛔ GATE 2 (humain, unique)
Présenter un récap PAR EPIC adossé aux tags (titre, KPIs, décisions par défaut, diff résumé),
les EPICs `blocked`, les questions ouvertes, le coût/temps vs budget. Demander la validation
explicite pour merger la branche de run sur `main`. RIEN n'est mergé sur `main` avant ce feu vert.

## Politiques d'exécution autonome (Phase 1)

### Défaut-sinon-stop (décisions émergentes)
- **Anticipable** → déjà tranchée au pré-vol (zéro interruption).
- **Émergente non bloquante** → appliquer le défaut le plus raisonnable, le consigner dans
  `DECISIONS.md` (hypothèse + justification), continuer.
- **Irréversible / destructive / sécurité-conformité / hors-mandat / contournement d'un
  garde-fou** → NE PAS deviner. Marquer l'EPIC `blocked`, poursuivre les indépendantes, surfacer
  à la revue finale.

### Échec & résilience
- Double gate rouge → jusqu'à 3 retries → sinon EPIC `blocked` + poursuite des indépendantes.
- Reprise idempotente : `PLAN.md` (statuts) = checkpoint ; redémarrer à la 1ʳᵉ EPIC non `done`,
  sans refaire le `done` ni retaguer.
- Budget : plafond temps/coût + `max_parallel` (`PLAN.md`) ; arrêt propre au seuil, récap reprenable.
- Avancement asynchrone : jamais de message bloquant ; `PLAN.md` + `RUN_LOG.md` à jour ; UNE
  notification aux seuls jalons (GATE 1/2, `blocked`, fin de run).

## GATE 2 — politique de merge (choix posé au pré-vol)
Avant la 1ʳᵉ EPIC, poser UNE question (recommandation en tête) et expliquer l'impact CHIFFRÉ :

> « Veux-tu revoir chaque EPIC avant son intégration, ou laisser le run intégrer en autonomie
> et tout revoir à la fin ? »
> - **A. Auto-intégration (recommandé)** — chaque EPIC verte est mergée automatiquement sur la
>   branche de run, sans arrêt ; tu es seulement informé, la suivante démarre. ~0 arrêt → débit max.
> - **B. Revue avant chaque merge** — arrêt avant chaque intégration. N arrêts pour N EPICs →
>   contrôle max, run nettement plus long.
> - **C. Revue des EPICs risquées seulement** — auto par défaut, arrêt pour les EPICs marquées
>   « sensibles » au pré-vol (migrations, sécurité, irréversible).

**Invariants — quel que soit le choix (jamais contournés) :**
- Merges automatiques = LOCAUX, toujours sur la branche de run, JAMAIS vers `main` ni PR auto.
  `auto_pr_merge` reste `false`.
- Merge+tag d'une EPIC UNIQUEMENT si double gate + non-régression VERTS. EPIC `blocked` : ni
  mergée ni taguée, surfacée à la revue finale.
- Après intégration réussie : tag `run/<slug>/epic-<n>` (immutable ; pas de retag à la reprise)
  + entrée `RUN_LOG.md`.
- Revue (B/C) qui rejette une EPIC → la rouvrir avec feedback (retry borné à 3), sinon `blocked` ;
  le run poursuit les indépendantes.
- EPICs parallèles → worktrees réintégrés SÉQUENTIELLEMENT sur la branche de run, non-régression
  évaluée à chaque intégration.

## Gabarit `RUN_LOG.md` (à instancier par run, append-only)
```
# RUN_LOG — Run <slug>
[HH:MM] GATE 1 · GO unattended · politique merge=<A|B|C> · <n> EPICs · budget=<…>
[HH:MM] EPIC <n> · spec · auto-validée
[HH:MM] EPIC <n> · gate · code ✅ design ✅ régression ✅
[HH:MM] EPIC <n> · merge+tag · run/<slug>/epic-<n>
[HH:MM] EPIC <n> · décision · défaut « <x> » appliqué (voir DECISIONS.md)
[HH:MM] EPIC <n> · blocked · <raison> → revue finale
[HH:MM] notification · <jalon>
[HH:MM] GATE 2 · revue finale présentée · attente validation merge main
```

## Prompt orchestrateur (copier-coller pour lancer un run unattended)
```
Tu pilotes un RUN UNATTENDED GOUVERNÉ du workflow EPIC. Suis ce playbook à la lettre.

PHASE 0 (GATE 1) : macro-brainstorm → PLAN.md (EPICs, déps, budget, max_parallel, branche
run/<slug>). Scanne TOUTES les EPICs, extrais les décisions anticipables, pose-les en UN
questionnaire groupé (recommandation par défaut + « tout accepter »), DONT le choix de politique
de merge (A auto / B chaque / C risquées, défaut A) avec impact chiffré. Consigne dans
DECISIONS.md. Estime budget/temps ; gros périmètre → propose un slice MVP. Attends le « GO ».

PHASE 1 (autonome, AUCUN arrêt de cérémonie) : pour chaque EPIC, brainstorm → spec auto-validée
(consulte DECISIONS.md) → plan → exécution subagent-driven → double gate + non-régression →
merge LOCAL sur run/<slug> si vert + tag run/<slug>/epic-<n> → maj PLAN.md + RUN_LOG.md →
récap+KPIs non bloquant → EPIC suivante automatiquement. Décision émergente : défaut-sinon-stop
(non bloquant = défaut + log + continue ; irréversible = blocked + continue les indépendantes).
Gate rouge : 3 retries puis blocked. Informe en ASYNCHRONE (fichiers + notification aux jalons).

PHASE 2 (GATE 2) : récap PAR EPIC (tags), EPICs blocked, questions ouvertes, coût/temps. DEMANDE
la validation pour merger run/<slug> sur main. NE MERGE JAMAIS main sans ce feu vert.

INTERDITS : ne contourne aucun garde-fou ; merge automatique = LOCAL uniquement ; auto_pr_merge
reste false ; ne tague jamais une EPIC blocked ; ne devine pas en silence sur l'irréversible ;
ne supprime pas la traçabilité (PLAN.md + DECISIONS.md + RUN_LOG.md).
```
```

- [ ] **Step 2: vérifier les ancres de gouvernance (garde-fous présents)**

Run: `rg -n "auto_pr_merge.{0,6}false|JAMAIS vers .main|3 retries|défaut-sinon-stop|append-only|tout accepter" "docs/superpowers/unattended-run-playbook.md"`
Expected: au moins 6 lignes (les invariants clés + politique défaut-sinon-stop + log append-only + pré-vol « tout accepter »).

- [ ] **Step 3: vérifier les 3 phases et les 2 gates**

Run: `rg -n "GATE 1|GATE 2|Phase 0|Phase 1|Phase 2|Auto-intégration|Revue avant chaque merge|EPICs risquées" "docs/superpowers/unattended-run-playbook.md"`
Expected: au moins 8 lignes (3 phases + 2 gates + 3 options de merge A/B/C).

- [ ] **Step 4: commit (optionnel — voir Note git)**

```
git add docs/superpowers/unattended-run-playbook.md
git commit -m "docs(unattended): playbook du mode unattended gouverné (lifecycle + politiques + prompt)"
```

---

## Task 4 : contrôle de cohérence transversal

**Files:** (lecture seule — aucune modification, sauf correction si écart détecté)
- `docs/superpowers/unattended-run-playbook.md`
- `docs/superpowers/templates/PLAN.md`
- `docs/superpowers/templates/DECISIONS.md`

- [ ] **Step 1: cohérence du schéma de tag entre les 3 fichiers**

Run: `rg -n "run/<slug>/epic-<n>" docs/superpowers/unattended-run-playbook.md docs/superpowers/templates/PLAN.md`
Expected: le schéma `run/<slug>/epic-<n>` apparaît à l'identique dans le playbook ET dans `PLAN.md`. Si une variante diverge (ex. `epic_<n>`), la corriger pour aligner sur `run/<slug>/epic-<n>`.

- [ ] **Step 2: cohérence des statuts EPIC**

Run: `rg -n "todo|in-progress|done|blocked" docs/superpowers/templates/PLAN.md docs/superpowers/unattended-run-playbook.md`
Expected: les 4 statuts `todo` / `in-progress` / `done` / `blocked` sont utilisés de façon cohérente (pas de synonyme type `wip` ou `pending`). Corriger tout écart.

- [ ] **Step 3: cohérence de la politique de merge A/B/C entre playbook et DECISIONS.md**

Run: `rg -n "Politique de merge|politique merge|A / B / C|A|B|C" docs/superpowers/templates/DECISIONS.md docs/superpowers/unattended-run-playbook.md`
Expected: la ligne « Politique de merge » de `DECISIONS.md` référence bien les 3 options A/B/C définies dans le playbook, défaut A. Corriger si l'intitulé diverge.

- [ ] **Step 4: relecture finale par rapport à la spec**

Relire [la spec](../specs/2026-06-18-unattended-run-mode-design.md) §2–§7 et confirmer que chaque élément a une contrepartie dans les artefacts : frontière cérémonie/gouvernance (table), 2 gates, défaut-sinon-stop, async/reprise/budget, GATE 2 A/B/C + invariants, schéma des templates. Corriger inline tout manque. Aucune sortie de commande attendue — vérification manuelle.

---

## Définition de fin
- [ ] 3 artefacts créés : `unattended-run-playbook.md`, `templates/PLAN.md`, `templates/DECISIONS.md`.
- [ ] Garde-fous présents et non contournés (`auto_pr_merge=false`, merge auto = local, jamais `main` sans revue, EPIC blocked jamais taguée).
- [ ] 2 gates humains (GATE 1 pré-vol, GATE 2 revue finale) + politique de merge réglable A/B/C (défaut A).
- [ ] Politiques défaut-sinon-stop, reprise, budget, async, parallélisme présentes.
- [ ] Schéma de tag, statuts et politique de merge cohérents entre les 3 fichiers.

## Self-Review
**Couverture spec :** Task 1 → `PLAN.md` (§7) ; Task 2 → `DECISIONS.md` (§7) ; Task 3 → playbook (§2,§4,§5,§6 + prompt + gabarit RUN_LOG) ; Task 4 → cohérence transversale + relecture spec. **Placeholders :** `<slug>`/`<n>`/`<…>` sont des variables de gabarit intentionnelles, pas des trous de plan. **Cohérence des noms :** schéma de tag `run/<slug>/epic-<n>`, statuts `todo`/`in-progress`/`done`/`blocked`, options merge `A`/`B`/`C` — identiques dans toutes les tâches.
